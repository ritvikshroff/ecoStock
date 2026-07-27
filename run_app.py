# ============================================================
# ecoStock 🥬 — App Launcher
# ============================================================
# Just double-click this file or run:
#   python run_app.py
#
# It will:
#   1. Create the database tables
#   2. Seed sample data (if not already seeded)
#   3. Start the server
#   4. Open your browser to the app
# ============================================================

import os
import sys
import webbrowser
import threading
import time
import subprocess

# Ensure we're in the right directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# ── Colors for terminal output ───────────────────────────
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RED = "\033[91m"
RESET = "\033[0m"
BOLD = "\033[1m"

def print_banner():
    """Print the ecoStock banner"""
    print(f"""
{BOLD}{GREEN}
╔═══════════════════════════════════════════════════════╗
║                                                       ║
║     🥬  ecoStock — Zero Waste Intelligence           ║
║     {RESET}Smart Inventory Management for Supermarkets{GREEN}      ║
║                                                       ║
╚═══════════════════════════════════════════════════════╝
{RESET}
    """)

def check_installed():
    """Check if required packages are installed"""
    try:
        import fastapi
        import sqlalchemy
        import uvicorn
        return True
    except ImportError:
        return False

def install_dependencies():
    """Install required packages"""
    print(f"{YELLOW}📦 Installing dependencies...{RESET}")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "Requirements.txt", "-q"])
    print(f"{GREEN}✅ Dependencies installed!{RESET}")

def seed_database():
    """Seed the database with sample data"""
    print(f"{CYAN}🌱 Seeding database with sample data...{RESET}")
    try:
        # Check if already seeded by trying to import and check
        from app.db.database import SessionLocal, engine, Base
        from app.models.models import Product

        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        count = db.query(Product).count()
        db.close()

        if count > 0:
            print(f"{GREEN}✅ Database already seeded ({count} products found){RESET}")
            return
    except Exception:
        pass

    # Run seed script
    try:
        exec(open("seed_data.py").read())
    except Exception as e:
        print(f"{YELLOW}⚠️  Seed skipped ({e}){RESET}")

def open_browser():
    """Open browser after a short delay"""
    time.sleep(3)
    webbrowser.open("http://localhost:8000")
    print(f"\n{GREEN}🌐 Browser opened to http://localhost:8000{RESET}")

def run_server():
    """Start the FastAPI server"""
    import uvicorn
    print(f"{GREEN}🚀 Starting ecoStock server...{RESET}")
    print(f"\n{CYAN}   📊 Dashboard:  http://localhost:8000{RESET}")
    print(f"{CYAN}   📋 API Docs:   http://localhost:8000/docs{RESET}")
    print(f"{CYAN}   🔑 Login:      manager@ecostock.com / password123{RESET}\n")
    print(f"{YELLOW}   Press CTRL+C to stop the server{RESET}\n")

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )

def main():
    """Main entry point"""
    print_banner()

    # Step 1: Check/install dependencies
    if not check_installed():
        print(f"{YELLOW}📦 First-time setup: installing dependencies...{RESET}")
        install_dependencies()
    else:
        print(f"{GREEN}✅ All dependencies found{RESET}")

    # Step 2: Seed database
    seed_database()

    # Step 3: Open browser in background
    browser_thread = threading.Thread(target=open_browser, daemon=True)
    browser_thread.start()

    # Step 4: Start server
    try:
        run_server()
    except KeyboardInterrupt:
        print(f"\n{YELLOW}👋 Shutting down...{RESET}")
        sys.exit(0)

if __name__ == "__main__":
    main()

