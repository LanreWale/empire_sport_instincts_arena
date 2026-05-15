"""
# ══════════════════════════════════════════════════════════════════════════════
#  EMPIRE SPORT INSTINCTS ARENA — INSTINCT SCOUT Module
#  Dark Gold Premium Edition v2.0 | Production Ready
# ══════════════════════════════════════════════════════════════════════════════
#
#  Brand Identity:
#    Primary Logo: Crowned Shield Monogram (Gold "E" on Black)
#    Secondary: Stadium Arena Wordmark (Metallic Gold + Silver)
#    Asset Path: BRAND_ASSET/empire_logo_primary.png
#               BRAND_ASSET/empire_logo_arena.png
#
#  Module: scheduler
#  Purpose: Master Scheduler
# ══════════════════════════════════════════════════════════════════════════════
"""
import schedule
import time
import threading
from datetime import datetime
import logging
from typing import Dict

from INSTINCT_SCOUT.football_collector import FootballCollector
from INSTINCT_SCOUT.nba_collector import NBACollector
from INSTINCT_SCOUT.nfl_collector import NFLCollector
from INSTINCT_SCOUT.tennis_collector import TennisCollector
from INSTINCT_SCOUT.odds_collector import OddsCollector

# ──────────────────────────────────────────────────────────────────────────────
# ⚜  IMPORTS & DEPENDENCIES
# ──────────────────────────────────────────────────────────────────────────────


logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# ⚜  CLASS: EmpireScheduler
# ──────────────────────────────────────────────────────────────────────────────

class EmpireScheduler:
    """Master scheduler for all data collection tasks"""

    def __init__(self):
        self.collectors = {
            'football': FootballCollector(),
            'nba': NBACollector(),
            'nfl': NFLCollector(),
            'tennis': TennisCollector(),
            'odds': OddsCollector()
        }
        self.running = False
        self.threads = []

    def schedule_all(self):
        """Schedule all collection tasks"""
        # Football: Every hour during season
        schedule.every(1).hours.do(self._collect_football)

        # NBA: Every 30 minutes during season
        schedule.every(30).minutes.do(self._collect_nba)

        # NFL: Every hour during season
        schedule.every(1).hours.do(self._collect_nfl)

        # Tennis: Every 2 hours
        schedule.every(2).hours.do(self._collect_tennis)

        # Odds: Every 5 minutes (most frequent)
        schedule.every(5).minutes.do(self._collect_odds)

        # Daily summary
        schedule.every().day.at("00:00").do(self._daily_summary)

        logger.info("All collection tasks scheduled")

    def _collect_football(self):
        logger.info("[FOOTBALL] Starting collection cycle")
        try:
            fixtures = self.collectors['football'].discover_upcoming_fixtures()
            logger.info(f"[FOOTBALL] Discovered {len(fixtures)} fixtures")
        except Exception as e:
            logger.error(f"[FOOTBALL] Collection error: {e}")

    def _collect_nba(self):
        logger.info("[NBA] Starting collection cycle")
        try:
            games = self.collectors['nba'].discover_upcoming_games()
            logger.info(f"[NBA] Discovered {len(games)} games")
        except Exception as e:
            logger.error(f"[NBA] Collection error: {e}")

    def _collect_nfl(self):
        logger.info("[NFL] Starting collection cycle")
        try:
            games = self.collectors['nfl'].discover_upcoming_games()
            logger.info(f"[NFL] Discovered {len(games)} games")
        except Exception as e:
            logger.error(f"[NFL] Collection error: {e}")

    def _collect_tennis(self):
        logger.info("[TENNIS] Starting collection cycle")
        try:
            tournaments = self.collectors['tennis'].discover_upcoming_tournaments()
            logger.info(f"[TENNIS] Discovered tournaments")
        except Exception as e:
            logger.error(f"[TENNIS] Collection error: {e}")

    def _collect_odds(self):
        logger.info("[ODDS] Starting collection cycle")
        try:
            # Collect odds for all sports
            for sport in ['soccer', 'basketball_nba', 'americanfootball_nfl']:
                odds = self.collectors['odds'].get_the_odds_events(sport)
                logger.info(f"[ODDS] {sport}: {len(odds)} entries")
        except Exception as e:
            logger.error(f"[ODDS] Collection error: {e}")

    def _daily_summary(self):
        logger.info("=" * 50)
        logger.info("DAILY SUMMARY — Empire Sport Instincts Arena")
        logger.info(f"Date: {datetime.now().strftime('%Y-%m-%d')}")
        logger.info("=" * 50)

    def run(self):
        """Run the scheduler loop"""
        self.running = True
        self.schedule_all()
        logger.info("EMPIRE SCHEDULER RUNNING — Instinct Scout Active")

        while self.running:
            schedule.run_pending()
            time.sleep(1)

    def stop(self):
        """Stop the scheduler"""
        self.running = False
        logger.info("Scheduler stopped")


# ──────────────────────────────────────────────────────────────────────────────
# ⚜  CLI ENTRY POINT
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    scheduler = EmpireScheduler()
    try:
        scheduler.run()
    except KeyboardInterrupt:
        scheduler.stop()


# ──────────────────────────────────────────────────────────────────────────────
# ⚜  END OF MODULE — EMPIRE SPORT INSTINCTS ARENA
# ⚜  Dark Gold Premium Edition v2.0 | Production Ready
# ──────────────────────────────────────────────────────────────────────────────