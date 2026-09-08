"""
Enterprise Automation Platform Server Launcher.
Launches the FastAPI backend and serves the interactive SPA dashboard.
"""

import sys
import webbrowser
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import uvicorn


def main():
    host = "127.0.0.1"
    port = 8000
    url = f"http://{host}:{port}/"

    print("=" * 76)
    print(" ⚡ ORBITAL AUTOMATION ENGINE — ENTERPRISE PLATFORM")
    print("=" * 76)
    print(f" [✓] Interactive Dashboard:  {url}")
    print(f" [✓] Interactive API Docs:   {url}docs")
    print(f" [✓] System Overview:        {url}api/overview")
    print(f" [✓] Process Mining DFG:     {url}api/mining/dfg")
    print(f" [✓] Hardware Telemetry:     {url}api/hardware")
    print(f" [✓] ERP CSV Export:         {url}api/export_erp_csv")
    print("=" * 76)
    print(" Starting Uvicorn ASGI Server... (Press CTRL+C to terminate)\n")

    try:
        webbrowser.open(url)
    except Exception:
        pass

    uvicorn.run(
        "src.automation.service.api:app",
        host=host,
        port=port,
        log_level="info",
        reload=False
    )


if __name__ == "__main__":
    main()
