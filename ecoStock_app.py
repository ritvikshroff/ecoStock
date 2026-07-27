# ============================================================
# ecoStock 🥬 — Desktop Application
# ============================================================
# This launches ecoStock in a NATIVE desktop window
# (NOT a browser tab — its own app window!)
#
# HOW TO USE:
#   Double-click this file (ecoStock_app.py)
#     OR
#   python ecoStock_app.py
#
# The app window will open automatically with the
# ecoStock dashboard inside it.
# ============================================================

import os
import sys
import threading
import time
from pathlib import Path

# Make sure we're in the right directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── Install dependencies if needed ────────────────────────
def ensure_dependencies():
    """Make sure pywebview and other packages are installed"""
    try:
        import webview
        return True
    except ImportError:
        print("📦 First-time setup: installing pywebview for desktop window...")
        import subprocess
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "pywebview", "-q"]
        )
        return True


# ── Seed database if empty ────────────────────────────────
def seed_if_needed():
    """Seed the database with sample data if it's empty"""
    try:
        from app.db.database import SessionLocal, engine, Base
        from app.models.models import Product

        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        count = db.query(Product).count()
        db.close()

        if count == 0:
            print("🌱 Seeding database with sample data...")
            exec(open("seed_data.py").read())
        else:
            print(f"✅ Database ready ({count} products)")
    except Exception as e:
        print(f"⚠️  Seed check: {e}")


# ── Start the FastAPI server in a background thread ───────
def start_server():
    """Start the FastAPI server on port 8000"""
    import uvicorn
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
        log_level="warning"
    )


# ── Wait for server to be ready ──────────────────────────
def wait_for_server():
    """Poll until the server is accepting connections"""
    import urllib.request
    for i in range(30):
        try:
            urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=1)
            return True
        except Exception:
            time.sleep(0.5)
    return False


# ============================================================
# MAIN — Launch the desktop app
# ============================================================
def main():
    print("""
╔═══════════════════════════════════════════════╗
║                                               ║
║     🥬  ecoStock Desktop App                 ║
║     Smart Inventory Management                ║
║                                               ║
╚═══════════════════════════════════════════════╝
    """)

    # Step 1: Ensure dependencies
    ensure_dependencies()
    import webview

    # Step 2: Seed database
    seed_if_needed()

    # Step 3: Start server in background
    print("🚀 Starting server...")
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()

    # Step 4: Wait for server
    print("⏳ Waiting for server...")
    if not wait_for_server():
        print("❌ Server failed to start!")
        input("Press Enter to exit...")
        return

    print("✅ Server ready!")
    print("📊 Opening ecoStock app window...\n")

    # Step 5: Create the desktop window
    window = webview.create_window(
        title="ecoStock 🥬 — Smart Inventory Management",
        url="http://127.0.0.1:8000",
        width=1280,
        height=800,
        min_size=(900, 600),
        resizable=True,
        fullscreen=False,
        text_select=True,
        confirm_close=True,
    )

    # Step 6: Run the app
    webview.start(
        debug=False,
        http_server=False,  # We use our own FastAPI server
        private_mode=False,
    )

    print("\n👋 ecoStock closed.")


if __name__ == "__main__":
    main()

