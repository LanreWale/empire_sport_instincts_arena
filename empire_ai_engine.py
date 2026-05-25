"""
═══════════════════════════════════════════════════════════════════════════════
EMPIRE AI PREDICTION ENGINE
Claude-Powered Sports Intelligence | Multi-Factor Analysis | Value Detection
═══════════════════════════════════════════════════════════════════════════════
Architecture:
  Layer 1 — Match Context Builder   : assembles all available data per match
  Layer 2 — Claude Reasoning Engine : generates structured prediction JSON
  Layer 3 — Consensus Validator     : cross-checks with odds EV calculation
  Layer 4 — Prediction Cache        : TTL-based store, never hits API twice
═══════════════════════════════════════════════════════════════════════════════
"""

import os
import json
import time
import hashlib
import requests
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

logger = logging.getLogger("EMPIRE_AI")

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════════════════════════

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL      = "claude-sonnet-4-20250514"
CLAUDE_URL        = "https://api.anthropic.com/v1/messages"

TTL_PREDICTION  = 1800   # 30 min — predictions stay fresh
TTL_BATCH       = 300    # 5  min — batch scan refresh
MAX_TOKENS      = 1200
REQUEST_TIMEOUT = 25

# Confidence thresholds
HIGH_CONF   = 70   # ≥70 % → strong signal
MEDIUM_CONF = 55   # ≥55 % → moderate signal
VALUE_EDGE  = 5    # ≥5 % implied probability edge = value bet


# ═══════════════════════════════════════════════════════════════════════════════
# DATA MODELS
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class MatchPrediction:
    match_id:        str
    home_team:       str
    away_team:       str
    league:          str
    sport:           str
    # Probabilities (0-100)
    home_win_pct:    float
    draw_pct:        float        # 0 for sports without draws
    away_win_pct:    float
    # Recommendation
    recommended_bet: str          # e.g. "HOME WIN", "OVER 2.5", "BTTS YES"
    confidence:      int          # 0-100
    confidence_label:str          # "HIGH" / "MEDIUM" / "LOW"
    value_rating:    str          # "⭐⭐⭐" / "⭐⭐" / "⭐" / "—"
    expected_goals:  str          # "2.3 – 1.1" style or ""
    # Analysis
    key_factors:     List[str]    # bullet-point reasons
    risk_factors:    List[str]    # warnings
    ai_summary:      str          # 2-3 sentence narrative
    betting_angle:   str          # specific market recommendation
    # Meta
    generated_at:    str
    model_version:   str = CLAUDE_MODEL
    error:           str = ""


@dataclass
class BulkScanResult:
    total_matches:   int
    high_conf_picks: List[Dict]
    value_bets:      List[Dict]
    scan_time:       str
    sport:           str


# ═══════════════════════════════════════════════════════════════════════════════
# SYSTEM PROMPT  — the brain of the prediction engine
# ═══════════════════════════════════════════════════════════════════════════════

PREDICTION_SYSTEM_PROMPT = """You are EMPIRE INSTINCT — an elite AI sports prediction engine built for professional-grade match analysis.

Your role: analyse every match with the precision of a data scientist, the instinct of a professional scout, and the discipline of a quantitative trader.

ANALYSIS FRAMEWORK (apply to every match):
1. FORM & MOMENTUM   — recent results, winning/losing streaks, home/away form splits
2. HEAD-TO-HEAD      — historical matchup patterns, venue advantage, psychological edge
3. TACTICAL CONTEXT  — playing styles, defensive solidity vs attacking output
4. SQUAD & INJURIES  — key absences, fatigue from fixture congestion, rotation risk
5. MOTIVATION        — league position stakes, cup runs, relegation/title pressure
6. MARKET SIGNALS    — implied probability from odds vs your model probability = edge
7. ENVIRONMENTAL     — weather, pitch condition, crowd pressure, travel fatigue

CONFIDENCE CALIBRATION:
- HIGH (70-100%): Multiple factors align, strong historical pattern, clear market edge
- MEDIUM (55-69%): Moderate evidence, some uncertainty, situational value
- LOW (below 55%): Too much uncertainty, recommend PASS

VALUE BET RULE: Only flag a value bet when your probability estimate exceeds the implied market probability by ≥5 percentage points.

RESPONSE FORMAT — respond ONLY with this exact JSON structure, no preamble, no markdown:
{
  "home_win_pct": <number 0-100>,
  "draw_pct": <number 0-100>,
  "away_win_pct": <number 0-100>,
  "recommended_bet": "<specific bet recommendation>",
  "confidence": <integer 0-100>,
  "confidence_label": "<HIGH|MEDIUM|LOW>",
  "value_rating": "<⭐⭐⭐|⭐⭐|⭐|—>",
  "expected_goals": "<home xG> – <away xG>",
  "key_factors": ["<factor 1>", "<factor 2>", "<factor 3>"],
  "risk_factors": ["<risk 1>", "<risk 2>"],
  "ai_summary": "<2-3 sentence professional narrative>",
  "betting_angle": "<specific actionable market: e.g. Asian Handicap -0.5 Home, Over 2.5 Goals, BTTS Yes>"
}"""


BATCH_SCAN_PROMPT = """You are EMPIRE SCANNER — an automated AI that scans multiple upcoming matches and identifies the TOP VALUE PICKS.

For each match provided, rapidly assess and score it. Return ONLY the highest-confidence picks (confidence ≥ 65).

RESPOND ONLY with this exact JSON, no preamble:
{
  "top_picks": [
    {
      "match_id": "<id>",
      "home_team": "<name>",
      "away_team": "<name>",
      "league": "<league>",
      "recommended_bet": "<bet>",
      "confidence": <0-100>,
      "value_rating": "<⭐⭐⭐|⭐⭐|⭐|—>",
      "one_line_reason": "<single sharp sentence>"
    }
  ],
  "value_bets": [
    {
      "match_id": "<id>",
      "match": "<home vs away>",
      "bet": "<bet>",
      "edge": "<e.g. Model 68% vs Market 52%>",
      "rating": "<⭐⭐⭐|⭐⭐|⭐>"
    }
  ],
  "scanner_note": "<brief overall market assessment>"
}"""


# ═══════════════════════════════════════════════════════════════════════════════
# CACHE
# ═══════════════════════════════════════════════════════════════════════════════

class PredictionCache:
    def __init__(self):
        self._store: Dict[str, Dict] = {}

    def _key(self, *parts) -> str:
        return hashlib.md5("|".join(str(p) for p in parts).encode()).hexdigest()

    def get(self, *parts, ttl: int = TTL_PREDICTION) -> Optional[Any]:
        k = self._key(*parts)
        e = self._store.get(k)
        if e and time.time() - e["t"] < ttl:
            return e["v"]
        return None

    def set(self, value: Any, *parts):
        k = self._key(*parts)
        self._store[k] = {"v": value, "t": time.time()}

    def invalidate(self, *parts):
        k = self._key(*parts)
        self._store.pop(k, None)

    def clear(self):
        self._store.clear()

    def stats(self) -> Dict:
        now = time.time()
        active = sum(1 for e in self._store.values()
                     if now - e["t"] < TTL_PREDICTION)
        return {"total": len(self._store), "active": active}


# ═══════════════════════════════════════════════════════════════════════════════
# CONTEXT BUILDER  — assembles match data into a rich prompt
# ═══════════════════════════════════════════════════════════════════════════════

class MatchContextBuilder:
    """Turns a match row dict into a rich Claude prompt."""

    @staticmethod
    def build(match_row: Dict, odds: Dict = None,
              sport: str = "Soccer") -> str:
        home   = match_row.get("HOME_TEAM", "Home Team")
        away   = match_row.get("AWAY_TEAM", "Away Team")
        league = match_row.get("LEAGUE",    "Unknown League")
        status = match_row.get("STATUS",    "UPCOMING")
        score  = match_row.get("SCORE",     "vs")
        mtime  = match_row.get("TIME",      "TBD")

        lines = [
            f"SPORT: {sport}",
            f"LEAGUE: {league}",
            f"MATCH: {home} vs {away}",
            f"KICK-OFF: {mtime}",
            f"STATUS: {status}",
        ]

        if score and score != "vs":
            lines.append(f"CURRENT SCORE: {score}")

        # Odds section
        if odds:
            h_odd = odds.get("home", odds.get("1", ""))
            d_odd = odds.get("draw", odds.get("X", ""))
            a_odd = odds.get("away", odds.get("2", ""))
            if h_odd:
                lines.append(f"MARKET ODDS → Home: {h_odd} | Draw: {d_odd} | Away: {a_odd}")
                # Calculate implied probabilities
                try:
                    h_imp = round(1/float(h_odd)*100, 1) if h_odd else 0
                    a_imp = round(1/float(a_odd)*100, 1) if a_odd else 0
                    d_imp = round(1/float(d_odd)*100, 1) if d_odd else 0
                    lines.append(
                        f"IMPLIED PROBABILITIES → Home: {h_imp}% | "
                        f"Draw: {d_imp}% | Away: {a_imp}%"
                    )
                except Exception:
                    pass

        # Sport-specific context hints
        sport_hints = {
            "Soccer":    "Consider: xG trends, set-piece threat, pressing intensity, BTTS history.",
            "NBA":       "Consider: pace of play, 3PT%, home court advantage, back-to-back fatigue, ATS record.",
            "NFL":       "Consider: QB rating, O-line vs D-line matchup, turnover differential, weather.",
            "MLB":       "Consider: starting pitcher ERA, bullpen strength, run line, stadium factors.",
            "NHL":       "Consider: save %, power play efficiency, goaltender form, puck line.",
            "UFC":       "Consider: fighting style matchup, reach advantage, recent KO/submission trends.",
            "Formula 1": "Consider: qualifying position, pit strategy, tire compound, track characteristics.",
            "Tennis":    "Consider: surface preference, H2H record, recent tournament load, serve stats.",
            "Cricket":   "Consider: pitch report, weather/DLS risk, batting depth, powerplay specialists.",
            "Golf":      "Consider: course fit, recent form, strokes gained stats, cut line pressure.",
        }
        lines.append(f"\nCONTEXT HINTS: {sport_hints.get(sport, '')}")
        lines.append(
            "\nUsing your AI model, provide a comprehensive prediction. "
            "If data is limited, use sport knowledge and contextual inference. "
            "Always produce a structured assessment — never return empty fields."
        )

        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# CLAUDE API CLIENT
# ═══════════════════════════════════════════════════════════════════════════════

class ClaudeClient:
    def __init__(self):
        self.api_key = ANTHROPIC_API_KEY
        self.headers = {
            "x-api-key":         self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type":      "application/json",
        } if self.api_key else {}

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def complete(self, system: str, user: str,
                 max_tokens: int = MAX_TOKENS) -> Optional[str]:
        if not self.available:
            return None
        payload = {
            "model":      CLAUDE_MODEL,
            "max_tokens": max_tokens,
            "system":     system,
            "messages":   [{"role": "user", "content": user}],
        }
        try:
            r = requests.post(
                CLAUDE_URL,
                headers=self.headers,
                json=payload,
                timeout=REQUEST_TIMEOUT,
            )
            if r.status_code == 200:
                data = r.json()
                blocks = data.get("content", [])
                return "".join(
                    b.get("text", "") for b in blocks if b.get("type") == "text"
                )
            logger.warning(f"Claude API {r.status_code}: {r.text[:200]}")
            return None
        except Exception as e:
            logger.error(f"Claude API error: {e}")
            return None

    @staticmethod
    def parse_json(text: str) -> Optional[Dict]:
        if not text:
            return None
        # Strip markdown fences if present
        clean = text.strip()
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        clean = clean.strip().rstrip("`").strip()
        try:
            return json.loads(clean)
        except json.JSONDecodeError:
            # Try to extract first {...} block
            start = clean.find("{")
            end   = clean.rfind("}") + 1
            if start != -1 and end > start:
                try:
                    return json.loads(clean[start:end])
                except Exception:
                    pass
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# EMPIRE AI ENGINE  — main interface
# ═══════════════════════════════════════════════════════════════════════════════

class EmpireAIEngine:
    def __init__(self):
        self.claude  = ClaudeClient()
        self.cache   = PredictionCache()
        self.builder = MatchContextBuilder()
        self._call_count   = 0
        self._error_count  = 0
        self._predictions: List[Dict] = []   # rolling log

    @property
    def available(self) -> bool:
        return self.claude.available

    # ── Single match prediction ───────────────────────────────────────────────
    def predict_match(self, match_row: Dict, sport: str = "Soccer",
                      odds: Dict = None,
                      force: bool = False) -> MatchPrediction:
        match_id = match_row.get("MATCH_ID", "unknown")
        home     = match_row.get("HOME_TEAM", "Home")
        away     = match_row.get("AWAY_TEAM", "Away")
        league   = match_row.get("LEAGUE",    "")

        # Cache check
        if not force:
            cached = self.cache.get(match_id, sport, ttl=TTL_PREDICTION)
            if cached:
                return cached

        # Build context and call Claude
        context = self.builder.build(match_row, odds, sport)
        raw     = self.claude.complete(PREDICTION_SYSTEM_PROMPT, context)
        self._call_count += 1

        parsed = self.claude.parse_json(raw) if raw else None

        if not parsed:
            self._error_count += 1
            pred = self._fallback_prediction(match_id, home, away, league, sport)
        else:
            pred = self._build_prediction(parsed, match_id, home, away, league, sport)

        # Store in cache and rolling log
        self.cache.set(pred, match_id, sport)
        self._predictions.append({
            "time":       datetime.now().strftime("%H:%M:%S"),
            "match":      f"{home} vs {away}",
            "sport":      sport,
            "bet":        pred.recommended_bet,
            "confidence": pred.confidence,
            "rating":     pred.value_rating,
        })
        if len(self._predictions) > 200:
            self._predictions = self._predictions[-200:]

        return pred

    # ── Batch scanner — scans all matches, returns top picks ─────────────────
    def scan_matches(self, matches_df, sport: str) -> Optional[BulkScanResult]:
        if matches_df is None or matches_df.empty:
            return None

        # Cache check for batch result
        batch_key = f"batch_{sport}_{datetime.now().strftime('%Y%m%d%H%M')[:11]}"
        cached = self.cache.get(batch_key, ttl=TTL_BATCH)
        if cached:
            return cached

        # Build compact match list for Claude
        rows = []
        for i, (_, row) in enumerate(matches_df.head(20).iterrows()):
            home = row.get("HOME_TEAM", "Home")
            away = row.get("AWAY_TEAM", "Away")
            mid  = row.get("MATCH_ID",  str(i))
            lg   = row.get("LEAGUE",    "")
            st   = row.get("STATUS",    "")
            rows.append(
                f"[{mid}] {home} vs {away} | {lg} | {st}"
            )

        sport_hints = {
            "Soccer":    "European/Global football. Consider form, xG, home advantage.",
            "NBA":       "Basketball. Consider pace, ATS trends, rest days.",
            "NFL":       "American football. Consider QB matchup, weather, spread.",
            "MLB":       "Baseball. Consider SP ERA, bullpen, run line.",
            "NHL":       "Ice hockey. Consider goalie form, puck line.",
            "UFC":       "MMA. Consider style matchup, recent finishes.",
            "Formula 1": "Motorsport. Consider grid position, track history.",
            "Tennis":    "Tennis. Consider surface, H2H, recent load.",
            "Cricket":   "Cricket. Consider pitch, weather, batting lineup.",
            "Golf":      "Golf. Consider course fit, recent form.",
        }

        user_prompt = (
            f"SPORT: {sport}\n"
            f"CONTEXT: {sport_hints.get(sport, '')}\n\n"
            f"MATCHES TO SCAN ({len(rows)} total):\n"
            + "\n".join(rows)
            + "\n\nScan all matches. Return only picks with confidence ≥ 65."
        )

        raw    = self.claude.complete(BATCH_SCAN_PROMPT, user_prompt, max_tokens=2000)
        parsed = self.claude.parse_json(raw) if raw else None
        self._call_count += 1

        if not parsed:
            return None

        result = BulkScanResult(
            total_matches=len(matches_df),
            high_conf_picks=parsed.get("top_picks", []),
            value_bets=parsed.get("value_bets", []),
            scan_time=datetime.now().strftime("%H:%M:%S"),
            sport=sport,
        )
        self.cache.set(result, batch_key)
        return result

    # ── Analytics: rolling performance log ───────────────────────────────────
    def get_prediction_log(self) -> List[Dict]:
        return list(reversed(self._predictions))

    def get_stats(self) -> Dict:
        return {
            "api_calls":    self._call_count,
            "errors":       self._error_count,
            "cache_active": self.cache.stats()["active"],
            "predictions":  len(self._predictions),
            "model":        CLAUDE_MODEL,
            "available":    self.available,
        }

    # ── Internal helpers ─────────────────────────────────────────────────────
    @staticmethod
    def _build_prediction(p: Dict, match_id: str, home: str,
                          away: str, league: str, sport: str) -> MatchPrediction:
        conf  = int(p.get("confidence", 50))
        label = "HIGH" if conf >= HIGH_CONF else ("MEDIUM" if conf >= MEDIUM_CONF else "LOW")
        return MatchPrediction(
            match_id         = match_id,
            home_team        = home,
            away_team        = away,
            league           = league,
            sport            = sport,
            home_win_pct     = float(p.get("home_win_pct", 33)),
            draw_pct         = float(p.get("draw_pct", 34)),
            away_win_pct     = float(p.get("away_win_pct", 33)),
            recommended_bet  = p.get("recommended_bet", "PASS"),
            confidence       = conf,
            confidence_label = label,
            value_rating     = p.get("value_rating", "—"),
            expected_goals   = p.get("expected_goals", ""),
            key_factors      = p.get("key_factors", []),
            risk_factors     = p.get("risk_factors", []),
            ai_summary       = p.get("ai_summary", ""),
            betting_angle    = p.get("betting_angle", ""),
            generated_at     = datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )

    @staticmethod
    def _fallback_prediction(match_id: str, home: str, away: str,
                              league: str, sport: str) -> MatchPrediction:
        return MatchPrediction(
            match_id         = match_id,
            home_team        = home,
            away_team        = away,
            league           = league,
            sport            = sport,
            home_win_pct     = 40.0,
            draw_pct         = 25.0,
            away_win_pct     = 35.0,
            recommended_bet  = "PASS — Insufficient data",
            confidence       = 0,
            confidence_label = "LOW",
            value_rating     = "—",
            expected_goals   = "",
            key_factors      = ["AI engine unavailable or API key not set"],
            risk_factors     = ["Set ANTHROPIC_API_KEY in Render environment"],
            ai_summary       = "Prediction engine offline. Add ANTHROPIC_API_KEY to Render env vars.",
            betting_angle    = "—",
            generated_at     = datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            error            = "Claude API unavailable",
        )


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIDENCE COLOUR HELPER  (used by app.py renderer)
# ═══════════════════════════════════════════════════════════════════════════════

def confidence_color(conf: int) -> str:
    if conf >= HIGH_CONF:
        return "#00ff88"
    if conf >= MEDIUM_CONF:
        return "#FFD700"
    return "#ff6b6b"


def confidence_bar_html(conf: int, width: int = 200) -> str:
    color  = confidence_color(conf)
    filled = int(width * conf / 100)
    return (
        f'<div style="background:#1a1a2e;border-radius:4px;height:8px;width:{width}px;'
        f'display:inline-block;overflow:hidden;">'
        f'<div style="background:{color};width:{filled}px;height:8px;'
        f'border-radius:4px;transition:width .5s ease;"></div></div>'
    )


def probability_donut_html(home: float, draw: float, away: float,
                            home_name: str, away_name: str) -> str:
    """Returns an SVG donut chart for win probabilities."""
    total = home + draw + away or 100
    h = round(home / total * 100)
    d = round(draw / total * 100)
    a = 100 - h - d

    def arc_path(pct_start: float, pct_end: float, r: int = 40) -> str:
        import math
        cx, cy = 50, 50
        def pt(pct):
            angle = math.radians(pct * 360 - 90)
            return cx + r * math.cos(angle), cy + r * math.sin(angle)
        x1, y1 = pt(pct_start)
        x2, y2 = pt(pct_end)
        large  = 1 if (pct_end - pct_start) > 0.5 else 0
        return f"M {cx} {cy} L {x1:.2f} {y1:.2f} A {r} {r} 0 {large} 1 {x2:.2f} {y2:.2f} Z"

    h_frac = h / 100
    d_frac = d / 100

    h_path = arc_path(0,              h_frac)
    d_path = arc_path(h_frac,         h_frac + d_frac)
    a_path = arc_path(h_frac + d_frac, 1.0)

    return f"""
<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg" width="140" height="140">
  <circle cx="50" cy="50" r="40" fill="#1a1a2e"/>
  <path d="{h_path}" fill="#00ff88" opacity=".9"/>
  <path d="{d_path}" fill="#FFD700" opacity=".9"/>
  <path d="{a_path}" fill="#ff6b6b" opacity=".9"/>
  <circle cx="50" cy="50" r="26" fill="#0a0a0f"/>
  <text x="50" y="46" font-family="Orbitron,sans-serif" font-size="7"
        fill="#888" text-anchor="middle">WIN %</text>
  <text x="50" y="57" font-family="Orbitron,sans-serif" font-size="9"
        fill="#FFD700" text-anchor="middle" font-weight="700">{h}|{d}|{a}</text>
</svg>
<div style="display:flex;gap:12px;justify-content:center;margin-top:4px;font-family:Rajdhani;font-size:.75rem;">
  <span style="color:#00ff88;">■ {home_name[:10]} {h}%</span>
  <span style="color:#FFD700;">■ Draw {d}%</span>
  <span style="color:#ff6b6b;">■ {away_name[:10]} {a}%</span>
</div>"""


__all__ = [
    "EmpireAIEngine",
    "MatchPrediction",
    "BulkScanResult",
    "confidence_color",
    "confidence_bar_html",
    "probability_donut_html",
    "HIGH_CONF",
    "MEDIUM_CONF",
]
