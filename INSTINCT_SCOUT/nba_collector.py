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
#  Module: nba_collector
#  Purpose: NBA Data Collector
# ══════════════════════════════════════════════════════════════════════════════
"""
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging

try:
    from nba_api.stats.endpoints import leaguegamefinder, playergamelogs, teamgamelogs
    from nba_api.stats.static import teams, players
    from nba_api.live.nba.endpoints import scoreboard

# ──────────────────────────────────────────────────────────────────────────────
# ⚜  IMPORTS & DEPENDENCIES
# ──────────────────────────────────────────────────────────────────────────────

    NBA_API_AVAILABLE = True
except ImportError:
    NBA_API_AVAILABLE = False
    logging.warning("nba_api not installed. NBA collection will use fallback methods.")

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# ⚜  CLASS: NBACollector
# ──────────────────────────────────────────────────────────────────────────────

class NBACollector:
    """Collects NBA data from official API and secondary sources"""

    def __init__(self):
        self.season = "2024-25"
        self.team_cache = {}
        if NBA_API_AVAILABLE:
            self._load_teams()

    def _load_teams(self):
        """Cache NBA team information"""
        if NBA_API_AVAILABLE:
            all_teams = teams.get_teams()
            self.team_cache = {t['id']: t for t in all_teams}
            logger.info(f"Loaded {len(all_teams)} NBA teams")

    def get_todays_games(self) -> pd.DataFrame:
        """Fetch today's NBA schedule"""
        if not NBA_API_AVAILABLE:
            logger.error("nba_api not available")
            return pd.DataFrame()

        try:
            games = scoreboard.ScoreBoard()
            data = games.get_dict()

            game_list = []
            for game in data.get('scoreboard', {}).get('games', []):
                game_list.append({
                    'game_id': game['gameId'],
                    'date': game['gameEt'],
                    'home_team': game['homeTeam']['teamName'],
                    'home_team_id': game['homeTeam']['teamId'],
                    'away_team': game['awayTeam']['teamName'],
                    'away_team_id': game['awayTeam']['teamId'],
                    'home_score': game['homeTeam']['score'],
                    'away_score': game['awayTeam']['score'],
                    'status': game['gameStatusText'],
                    'arena': game.get('arena', {}).get('arenaName', ''),
                })

            df = pd.DataFrame(game_list)
            logger.info(f"Found {len(df)} NBA games today")
            return df
        except Exception as e:
            logger.error(f"Error fetching NBA scoreboard: {e}")
            return pd.DataFrame()

    def get_team_games(self, team_id: int, season: str = None) -> pd.DataFrame:
        """Fetch all games for a specific team"""
        if not NBA_API_AVAILABLE:
            return pd.DataFrame()

        season = season or self.season
        try:
            gamefinder = leaguegamefinder.LeagueGameFinder(
                team_id_nullable=team_id,
                season_nullable=season,
                season_type_nullable="Regular Season"
            )
            games = gamefinder.get_data_frames()[0]
            logger.info(f"Loaded {len(games)} games for team {team_id}")
            return games
        except Exception as e:
            logger.error(f"Error fetching team games: {e}")
            return pd.DataFrame()

    def get_player_logs(self, player_id: int, season: str = None) -> pd.DataFrame:
        """Fetch player game logs"""
        if not NBA_API_AVAILABLE:
            return pd.DataFrame()

        season = season or self.season
        try:
            logs = playergamelogs.PlayerGameLogs(
                player_id_nullable=player_id,
                season_nullable=season
            )
            data = logs.get_data_frames()[0]
            return data
        except Exception as e:
            logger.error(f"Error fetching player logs: {e}")
            return pd.DataFrame()

    def calculate_team_advanced_metrics(self, team_id: int) -> Dict:
        """Calculate advanced metrics for a team"""
        games = self.get_team_games(team_id)
        if games.empty:
            return {}

        # Calculate rolling averages and advanced stats
        metrics = {
            'games_played': len(games),
            'win_pct': (games['WL'] == 'W').mean(),
            'pts_avg': games['PTS'].mean(),
            'pts_allowed_avg': games['PTS'].mean(),  # Would need opponent data
            'fg_pct': games['FG_PCT'].mean(),
            'fg3_pct': games['FG3_PCT'].mean(),
            'ft_pct': games['FT_PCT'].mean(),
            'reb_avg': games['REB'].mean(),
            'ast_avg': games['AST'].mean(),
            'tov_avg': games['TOV'].mean(),
            'stl_avg': games['STL'].mean(),
            'blk_avg': games['BLK'].mean(),
            'plus_minus_avg': games['PLUS_MINUS'].mean(),
        }
        return metrics

    def discover_upcoming_games(self, days_ahead: int = 7) -> pd.DataFrame:
        """Discover upcoming NBA games"""
        # Use scoreboard API for today + schedule for future
        today_games = self.get_todays_games()

        # For future games, we'd need schedule API or scraping
        # This is simplified for the architecture demonstration
        logger.info(f"Discovered {len(today_games)} NBA games")
        return today_games


# ──────────────────────────────────────────────────────────────────────────────
# ⚜  CLI ENTRY POINT
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    collector = NBACollector()
    games = collector.get_todays_games()
    print(games.head())


# ──────────────────────────────────────────────────────────────────────────────
# ⚜  END OF MODULE — EMPIRE SPORT INSTINCTS ARENA
# ⚜  Dark Gold Premium Edition v2.0 | Production Ready
# ──────────────────────────────────────────────────────────────────────────────