"""IMBY Payroll Automation Suite - Standalone Application Runner.

Launches the dedicated FastAPI backend on port 8500 and opens the
high-performance desktop/web interface in the user's default browser.
"""

from __future__ import annotations

import os
import sys
import threading
import time
import webbrowser
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def open_browser(url: str, delay_seconds: float = 1.2) -> None:
    """Open the browser after the server has initialized."""
    time.sleep(delay_seconds)
    try:
        print(f"\n[Launcher] Launching application interface at: {url}")
        webbrowser.open(url)
    except Exception as exc:
        print(f"[Launcher] Could not automatically open browser: {exc}")


def main() -> None:
    """Run the standalone automation server."""
    port = int(os.environ.get("PAYROLL_APP_PORT", "8500"))
    host = os.environ.get("PAYROLL_APP_HOST", "127.0.0.1")
    url = f"http://{host}:{port}/"

    print("=" * 70)
    print("  IMBY ENTERPRISE PAYROLL DEDUCTION AUTOMATION SUITE")
    print("  Deterministic Engine · Policy Copilot · ERP Staging")
    print("=" * 70)
    print(f"  Server URL: {url}")
    print(f"  Project Root: {PROJECT_ROOT}")
    print("=" * 70)

    # Start browser opener in background thread
    launcher_thread = threading.Thread(
        target=open_browser, args=(url,), daemon=True
    )
    launcher_thread.start()

    try:
        import uvicorn
        from apps.payroll_automation.backend.main import app

        uvicorn.run(app, host=host, port=port, log_level="info")
    except ImportError:
        print("[Error] Uvicorn is required to run the server. Install via:")
        print("        pip install uvicorn")
        sys.exit(1)


if __name__ == "__main__":
    main()
