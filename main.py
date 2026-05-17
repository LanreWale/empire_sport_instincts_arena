#!/usr/bin/env python3
"""
EMPIRE SPORT INSTINCTS ARENA — Main System Entry Point
Commands: scout | dashboard | test | help
"""
import sys
import os
import subprocess
import time
import socket
import requests
from pathlib import Path
from datetime import datetime

# Force .env load before anything else
from dotenv import load_dotenv
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path, override=True)
    print(f"[EMPIRE] Loaded .env from {env_path}")
else:
    print("[EMPIRE] ⚠️ .env file not found! APIs will fail.")

def print_banner():
    print("=" * 60)
    print("")
    print("    EMPIRE SPORT INSTINCTS ARENA")
    print("")
    print("    Advanced Research & Evaluation System")
    print("    Where Data Meets Instinct")
    print("")
    print("    Football    NBA    NFL    Tennis")
    print("")
    print("=" * 60)

def run_api_diagnostics():
    """Test all API keys and network before launching."""
    print("\n" + "═" * 60)
    print(" 📡 API CONNECTION DIAGNOSTICS")
    print("═" * 60)

    keys = [
        ("API-SPORTS", "API_SPORTS_KEY"),
        ("The Odds API", "ODDS_API_KEY"),
        ("Sportmonks", "SPORTMONKS_KEY"),
        ("TheSportsDB", "TheSportDB_API_key"),
        ("The Rundown", "RUNDOWN_KEY"),
    ]

    print("\n🔑 API KEYS:")
    for name, env_var in keys:
        val = os.getenv(env_var, "")
        if val and len(val) > 3:
            print(f" 🟢 {name:20s} : Present ({len(val)} chars)")
        else:
            print(f" 🔴 {name:20s} : MISSING")

    print("\n🌐 NETWORK:")
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        print(" 🟢 Internet: Connected")
    except Exception as e:
        print(f" 🔴 Internet: {e}")

    try:
        r = requests.get("https://api.github.com", timeout=5)
        print(f" 🟢 HTTPS: OK ({r.status_code})")
    except Exception as e:
        print(f" 🔴 HTTPS: {e}")

    print("\n📊 PROVIDER TEST:")
    try:
        from empire_data_layer import EmpireDataRouter
        router = EmpireDataRouter()

        # FIXED: router.connection_log now exists
        if router.active_provider:
            print(f" 🟢 ACTIVE: {router.active_provider.name}")
            print(" ✅ LIVE MODE — Real data streaming")
        else:
            print(" 🔴 NO ACTIVE PROVIDER")
            print(" ⚠️ DEMO MODE — Check .env keys")

        if router.connection_log:
            for entry in router.connection_log[-6:]:
                icon = "🟢" if entry["status"] == "SUCCESS" else (
                    "🟡" if entry["status"] == "EMPTY" else "🔴"
                )
                detail = entry.get("detail", "")[:45]
                print(f" {icon} {entry['provider']:15s} : {entry['status']} — {detail}")
        else:
            print(" ⚪ No connection log entries")

    except SyntaxError as e:
        print(f" 🔴 SYNTAX ERROR in empire_data_layer.py: {e}")
        print(f" File: {e.filename}, Line: {e.lineno}")
        print(" Fix the unterminated string literal and retry.")
    except Exception as e:
        print(f" 🔴 Data layer error: {e}")

    print("\n" + "═" * 60 + "\n")
    time.sleep(1)

def start_scheduler():
    try:
        from INSTINCT_SCOUT.scheduler import EmpireScheduler
        scheduler = EmpireScheduler()
        print("[INSTINCT SCOUT] Starting data collection...")
        scheduler.run()
    except ImportError as e:
        print(f"[INSTINCT SCOUT] ⚠️ Module not found: {e}")
    except Exception as e:
        print(f"[INSTINCT SCOUT] ❌ Error: {e}")

def find_app_py():
    """Find app.py in possible locations."""
    base = Path(__file__).parent
    locations = [
        base / "app.py",
        base / "ARENA_DASHBOARD" / "app.py",
        base / "arena_dashboard" / "app.py",
    ]
    for loc in locations:
        if loc.exists():
            return loc
    return None

def start_dashboard():
    """Launch Streamlit dashboard with diagnostics."""
    run_api_diagnostics()

    app_path = find_app_py()

    if not app_path:
        print("[ARENA DASHBOARD] ❌ app.py not found!")
        print(" Searched in:")
        print(" - EMPIRE_SPORT_INSTINCTS_ARENA/app.py")
        print(" - EMPIRE_SPORT_INSTINCTS_ARENA/ARENA_DASHBOARD/app.py")
        print("\n Please ensure app.py is in the root folder or ARENA_DASHBOARD/")
        return

    print(f"[ARENA DASHBOARD] Found app.py at: {app_path}")
    print(f"[ARENA DASHBOARD] Launching Streamlit...")

    try:
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", str(app_path),
            "--server.headless", "true",
            "--server.port", "8501",
            "--server.address", "localhost",
        ], check=True)
    except subprocess.CalledProcessError as e:
        print(f"[ARENA DASHBOARD] ❌ Streamlit exited with code {e.returncode}")
    except KeyboardInterrupt:
        print("\n[ARENA DASHBOARD] Stopped by user.")

def run_backtest():
    try:
        from EMPIRE_TESTING.walk_forward import WalkForwardTester
        print("[EMPIRE TESTING] Running walk-forward analysis...")
        tester = WalkForwardTester()
        print("Backtest engine ready")
    except SyntaxError as e:
        print(f"[EMPIRE TESTING] ❌ Syntax error in walk_forward.py: {e}")
        print(f" File: {e.filename}, Line: {e.lineno}")
        print(" Fix the unterminated string literal.")
    except ImportError as e:
        print(f"[EMPIRE TESTING] ⚠️ Module not found: {e}")
    except Exception as e:
        print(f"[EMPIRE TESTING] ❌ Error: {e}")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="EMPIRE SPORT INSTINCTS ARENA")
    parser.add_argument("command", choices=["scout", "dashboard", "test", "help"])
    args = parser.parse_args()

    print_banner()

    if args.command == "scout":
        start_scheduler()
    elif args.command == "dashboard":
        start_dashboard()
    elif args.command == "test":
        run_backtest()
    else:
        print("Commands: scout | dashboard | test")

if __name__ == "__main__":
    main()
