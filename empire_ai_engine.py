"""
═══════════════════════════════════════════════════════════════════════════════
EMPIRE AI PREDICTION ENGINE v4.1
Claude-Powered Sports Intelligence | Multi-Factor Analysis | Value Detection
═══════════════════════════════════════════════════════════════════════════════
"""

import os
import json
import time
import hashlib
import requests
import logging
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, field

logger = logging.getLogger("EMPIRE_AI")

# ─── CONFIG ───────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

CLAUDE_MODELS = [
    "claude-sonnet-4-5",
    "claude-3-5-sonnet-20241022",
    "claude-3-5-haiku-20241022",
    "claude-3-haiku-20240307",
]
CLAUDE_URL        = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"

TTL_PREDICTION = 1800
TTL_BATCH      = 300
MAX_TOKENS     = 1200
REQUEST_TIMEOUT = 30
HIGH_CONF   = 70
MEDIUM_CONF = 55
VALUE_EDGE  = 5

# ─── DATA MODELS ──────────────────────────────────────────────────────────────
@dataclass
class MatchPrediction:
    match_id:         str
    home_team:        str
    away_team:        str
    league:           str
    sport:            str
    home_win_pct:     float
    draw_pct:         float
    away_win_pct:     float
    recommended_bet:  str
    confidence:       int
    confidence_label: str
    value_rating:     str
    expected_goals:   str
    key_factors:      List[str]
    risk_factors:     List[str]
    ai_summary:       str
    betting_angle:    str
    generated_at:     str
    model_version:    str = ""
    error:            str = ""


@dataclass
class BulkScanResult:
    total_matches:   int
    high_conf_picks: List[Dict]
    value_bets:      List[Dict]
    scan_time:       str
    sport:           str


# ─── SYSTEM PROMPT ────────────────────────────────────────────────────────────
PREDICTION_SYSTEM_PROMPT = """You are EMPIRE INSTINCT — an elite AI sports prediction engine built for professional-grade match analysis.

ANALYSIS FRAMEWORK:
1. FORM & MOMENTUM   — recent results, streaks, home/away splits
2. HEAD-TO-HEAD      — historical patterns, venue advantage
3. TACTICAL CONTEXT  — playing styles, defensive solidity vs attacking output
4. SQUAD & INJURIES  — key absences, fatigue, rotation risk
5. MOTIVATION        — league position stakes, cup runs, relegation/title pressure
6. MARKET SIGNALS    — implied probability from odds vs model probability = edge
7. ENVIRONMENTAL     — weather, pitch, crowd, travel fatigue

CONFIDENCE CALIBRATION:
- HIGH (70-100%): Multiple factors align, strong historical pattern, clear market edge
- MEDIUM (55-69%): Moderate evidence, some uncertainty
- LOW (below 55%): Too much uncertainty

VALUE BET: Only flag when your probability exceeds implied market probability by ≥5pp.

RESPOND ONLY with this exact JSON (no markdown, no preamble):
{
  "home_win_pct": <number 0-100>,
  "draw_pct": <number 0-100>,
  "away_win_pct": <number 0-100>,
  "recommended_bet": "<specific bet>",
  "confidence": <integer 0-100>,
  "confidence_label": "<HIGH|MEDIUM|LOW>",
  "value_rating": "<⭐⭐⭐|⭐⭐|⭐|—>",
  "expected_goals": "<home_xg> – <away_xg> or empty string",
  "key_factors": ["<factor 1>", "<factor 2>", "<factor 3>"],
  "risk_factors": ["<risk 1>", "<risk 2>"],
  "ai_summary": "<2-3 sentence narrative>",
  "betting_angle": "<specific market and bet>"
}"""


# ─── PREDICTION CACHE ─────────────────────────────────────────────────────────
class PredictionCache:
    def __init__(self):
        self._store: Dict[str, Dict] = {}

    def _key(self, match_id: str, sport: str) -> str:
        return hashlib.md5(f"{sport}::{match_id}".encode()).hexdigest()

    def get(self, match_id: str, sport: str) -> Optional[MatchPrediction]:
        key   = self._key(match_id, sport)
        entry = self._store.get(key)
        if not entry:
            return None
        if time.time() - entry["ts"] > TTL_PREDICTION:
            del self._store[key]
            return None
        return entry["pred"]

    def set(self, match_id: str, sport: str, pred: MatchPrediction):
        self._store[self._key(match_id, sport)] = {"pred": pred, "ts": time.time()}

    def active_count(self) -> int:
        now = time.time()
        return sum(1 for e in self._store.values() if now - e["ts"] <= TTL_PREDICTION)

    def clear(self):
        self._store.clear()


# ─── HTML HELPERS ─────────────────────────────────────────────────────────────
def confidence_color(conf: int) -> str:
    if conf >= HIGH_CONF:   return "#00ff88"
    if conf >= MEDIUM_CONF: return "#FFD700"
    return "#ff6b6b"


def confidence_bar_html(conf: int, width: int = 200) -> str:
    color  = confidence_color(conf)
    filled = int(width * conf / 100)
    return (
        f'<div style="display:inline-block;width:{width}px;height:8px;'
        f'background:rgba(255,255,255,.1);border-radius:4px;overflow:hidden;">'
        f'<div style="width:{filled}px;height:100%;background:{color};border-radius:4px;"></div></div>'
    )


def probability_donut_html(home_pct: float, draw_pct: float, away_pct: float,
                            home_label: str, away_label: str) -> str:
    segments = [
        (home_pct, "#00ff88", home_label[:12]),
        (draw_pct, "#D4AF37", "DRAW"),
        (away_pct, "#ff6b6b", away_label[:12]),
    ]
    total = sum(s[0] for s in segments) or 100
    bars  = ""
    for pct, color, label in segments:
        norm = round(pct / total * 100, 1)
        bars += (
            f'<div style="margin:4px 0;">'
            f'<div style="display:flex;justify-content:space-between;margin-bottom:2px;">'
            f'<span style="font-family:Rajdhani;font-size:.8rem;color:#888;">{label}</span>'
            f'<span style="font-family:Orbitron;font-size:.8rem;color:{color};">{norm}%</span></div>'
            f'<div style="background:rgba(255,255,255,.1);border-radius:4px;height:6px;">'
            f'<div style="width:{norm}%;background:{color};height:6px;border-radius:4px;"></div></div></div>'
        )
    return f'<div style="padding:8px 0;">{bars}</div>'


# ─── CLAUDE CLIENT ────────────────────────────────────────────────────────────
class ClaudeClient:
    """Minimal Claude API client with automatic model fallback."""

    def __init__(self):
        self.api_key   = ANTHROPIC_API_KEY
        self.model     = None
        self.available = bool(self.api_key)

    def _try_call(self, model: str, messages: List[Dict], system: str, max_tokens: int) -> Optional[Dict]:
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "content-type": "application/json",
        }
        payload = {"model": model, "max_tokens": max_tokens, "system": system, "messages": messages}
        try:
            resp = requests.post(CLAUDE_URL, headers=headers, json=payload, timeout=REQUEST_TIMEOUT)
            if resp.status_code == 200:
                return resp.json()
            if resp.status_code in (400, 404):
                logger.warning(f"Model {model} rejected: {resp.status_code}")
                return None
            logger.error(f"Claude {model} → {resp.status_code}: {resp.text[:200]}")
            return None
        except requests.exceptions.Timeout:
            logger.warning(f"Claude {model} timed out")
            return None
        except Exception as e:
            logger.error(f"Claude call error: {e}")
            return None

    def call(self, messages: List[Dict], system: str = "", max_tokens: int = MAX_TOKENS) -> Optional[str]:
        if not self.available:
            return None
        candidates = ([self.model] + [m for m in CLAUDE_MODELS if m != self.model]
                      if self.model else CLAUDE_MODELS)
        for model in candidates:
            resp = self._try_call(model, messages, system, max_tokens)
            if resp:
                try:
                    content    = resp["content"][0]["text"]
                    self.model = model
                    return content
                except (KeyError, IndexError) as e:
                    logger.error(f"Unexpected Claude response: {e}")
        logger.error("All Claude models failed.")
        return None


# ─── CONTEXT BUILDER ──────────────────────────────────────────────────────────
class MatchContextBuilder:
    @staticmethod
    def build(match_row: Dict, sport: str) -> str:
        home   = match_row.get("HOME_TEAM", "Unknown")
        away   = match_row.get("AWAY_TEAM", "Unknown")
        league = match_row.get("LEAGUE", "Unknown")
        status = match_row.get("STATUS", "UPCOMING")
        score  = match_row.get("SCORE", "vs")
        mtime  = match_row.get("TIME", "TBD")
        venue  = match_row.get("VENUE", "")

        lines = [
            f"SPORT:    {sport.upper()}",
            f"LEAGUE:   {league}",
            f"MATCH:    {home} vs {away}",
            f"STATUS:   {status}  |  SCORE: {score}  |  TIME: {mtime}",
        ]
        if venue:
            lines.append(f"VENUE:    {venue}")

        for label, key in [("HOME", "HOME_ODDS"), ("DRAW", "DRAW_ODDS"), ("AWAY", "AWAY_ODDS")]:
            val = match_row.get(key)
            if val:
                try:
                    implied = round(100 / float(val), 1)
                    lines.append(f"ODDS {label}: {val} (implied {implied}%)")
                except Exception:
                    lines.append(f"ODDS {label}: {val}")

        for field_label, row_key in [
            ("HOME FORM (last 5)", "HOME_FORM"),
            ("AWAY FORM (last 5)", "AWAY_FORM"),
            ("HEAD-TO-HEAD", "H2H"),
            ("HOME INJURIES", "HOME_INJURIES"),
            ("AWAY INJURIES", "AWAY_INJURIES"),
            ("HOME xG avg", "HOME_XG"),
            ("AWAY xG avg", "AWAY_XG"),
            ("HOME goals/game", "HOME_GPG"),
            ("AWAY goals/game", "AWAY_GPG"),
            ("HOME conceded/game", "HOME_CPG"),
            ("AWAY conceded/game", "AWAY_CPG"),
        ]:
            val = match_row.get(row_key)
            if val:
                lines.append(f"{field_label}: {val}")

        return "\n".join(lines)


# ─── EMPIRE AI ENGINE ─────────────────────────────────────────────────────────
class EmpireAIEngine:
    def __init__(self):
        self.client           = ClaudeClient()
        self.cache            = PredictionCache()
        self._call_count      = 0
        self._error_count     = 0
        self._prediction_log: List[Dict] = []

    @property
    def available(self) -> bool:
        return self.client.available

    def get_stats(self) -> Dict:
        return {
            "api_calls":    self._call_count,
            "cache_active": self.cache.active_count(),
            "predictions":  len(self._prediction_log),
            "errors":       self._error_count,
            "model":        self.client.model or "Not yet resolved",
        }

    def get_prediction_log(self) -> List[Dict]:
        return list(reversed(self._prediction_log[-50:]))

    def predict_match(self, match_row: Dict, sport: str, force: bool = False) -> MatchPrediction:
        match_id = str(match_row.get("MATCH_ID", ""))
        home     = str(match_row.get("HOME_TEAM", "Home"))
        away     = str(match_row.get("AWAY_TEAM", "Away"))
        league   = str(match_row.get("LEAGUE", ""))

        if not force:
            cached = self.cache.get(match_id, sport)
            if cached:
                return cached

        if not self.available:
            return self._fallback(match_id, home, away, league, sport, "ANTHROPIC_API_KEY not set")

        context = MatchContextBuilder.build(match_row, sport)
        self._call_count += 1
        raw = self.client.call(
            messages=[{"role": "user", "content": f"Analyse this match and return JSON only:\n\n{context}"}],
            system=PREDICTION_SYSTEM_PROMPT,
        )
        if not raw:
            self._error_count += 1
            return self._fallback(match_id, home, away, league, sport, "Claude API call failed")

        pred = self._parse(raw, match_id, home, away, league, sport)
        self.cache.set(match_id, sport, pred)
        self._log(pred)
        return pred

    def scan_matches(self, df, sport: str, min_confidence: int = 65, max_matches: int = 20) -> BulkScanResult:
        if df is None or df.empty:
            return BulkScanResult(0, [], [], datetime.now().strftime("%H:%M"), sport)

        high_conf_picks: List[Dict] = []
        value_bets:      List[Dict] = []
        total = 0

        for _, row in df.head(max_matches).iterrows():
            try:
                pred  = self.predict_match(row.to_dict(), sport)
                total += 1
                if pred.error or pred.confidence < min_confidence:
                    continue
                high_conf_picks.append({
                    "match_id":         pred.match_id,
                    "home_team":        pred.home_team,
                    "away_team":        pred.away_team,
                    "league":           pred.league,
                    "recommended_bet":  pred.recommended_bet,
                    "confidence":       pred.confidence,
                    "confidence_label": pred.confidence_label,
                    "value_rating":     pred.value_rating,
                    "one_line_reason":  pred.ai_summary[:100],
                })
                if pred.value_rating in ("⭐⭐⭐", "⭐⭐"):
                    value_bets.append({
                        "match":  f"{pred.home_team} vs {pred.away_team}",
                        "bet":    pred.recommended_bet,
                        "edge":   f"+{pred.confidence - 50}%",
                        "rating": pred.value_rating,
                    })
            except Exception as e:
                logger.error(f"scan error: {e}")
                self._error_count += 1

        high_conf_picks.sort(key=lambda x: x["confidence"], reverse=True)
        return BulkScanResult(
            total_matches=total,
            high_conf_picks=high_conf_picks[:10],
            value_bets=value_bets[:10],
            scan_time=datetime.now().strftime("%H:%M:%S"),
            sport=sport,
        )

    # ── internals ──────────────────────────────────────────────────────────────
    def _parse(self, raw: str, match_id: str, home: str, away: str,
               league: str, sport: str) -> MatchPrediction:
        try:
            text = raw.strip()
            if text.startswith("```"):
                text = "\n".join(l for l in text.split("\n") if not l.startswith("```"))
            start = text.find("{"); end = text.rfind("}") + 1
            if start == -1 or end == 0:
                raise ValueError("No JSON found")
            data = json.loads(text[start:end])
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"JSON parse error: {e}")
            return self._fallback(match_id, home, away, league, sport, f"JSON parse error: {e}")

        conf  = int(data.get("confidence", 50))
        label = "HIGH" if conf >= HIGH_CONF else ("MEDIUM" if conf >= MEDIUM_CONF else "LOW")
        return MatchPrediction(
            match_id=match_id, home_team=home, away_team=away,
            league=league, sport=sport,
            home_win_pct=float(data.get("home_win_pct", 33.3)),
            draw_pct=float(data.get("draw_pct", 33.3)),
            away_win_pct=float(data.get("away_win_pct", 33.4)),
            recommended_bet=str(data.get("recommended_bet", "—")),
            confidence=conf, confidence_label=label,
            value_rating=str(data.get("value_rating", "—")),
            expected_goals=str(data.get("expected_goals", "")),
            key_factors=[str(f) for f in data.get("key_factors", [])[:5]],
            risk_factors=[str(r) for r in data.get("risk_factors", [])[:3]],
            ai_summary=str(data.get("ai_summary", "")),
            betting_angle=str(data.get("betting_angle", "—")),
            generated_at=datetime.now().isoformat(),
            model_version=self.client.model or "claude",
        )

    def _fallback(self, match_id, home, away, league, sport, error) -> MatchPrediction:
        return MatchPrediction(
            match_id=match_id, home_team=home, away_team=away,
            league=league, sport=sport,
            home_win_pct=33.3, draw_pct=33.3, away_win_pct=33.4,
            recommended_bet="—", confidence=0, confidence_label="—",
            value_rating="—", expected_goals="",
            key_factors=[], risk_factors=[],
            ai_summary="", betting_angle="—",
            generated_at=datetime.now().isoformat(),
            model_version="—", error=error,
        )

    def _log(self, pred: MatchPrediction):
        if pred.error or pred.confidence == 0:
            return
        self._prediction_log.append({
            "time":       datetime.now().strftime("%H:%M:%S"),
            "match":      f"{pred.home_team} vs {pred.away_team}",
            "sport":      pred.sport,
            "bet":        pred.recommended_bet,
            "confidence": pred.confidence,
            "rating":     pred.value_rating,
        })
        if len(self._prediction_log) > 200:
            self._prediction_log = self._prediction_log[-200:]
