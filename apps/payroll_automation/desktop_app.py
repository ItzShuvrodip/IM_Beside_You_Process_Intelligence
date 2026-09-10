"""
IMBY Enterprise Payroll Deduction Automation Suite - Standalone Desktop Application
Launches an independent native Windows desktop window with an embedded ASGI engine.
Requires no external web browser, runs completely self-contained.
"""

import sys
import os
import time
import socket
import threading
import logging
import webbrowser
from pathlib import Path

# Ensure project root is available in sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import uvicorn
from apps.payroll_automation.backend.main import app

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("DesktopApp")


def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0


def find_available_port(start_port: int = 8500, host: str = "127.0.0.1") -> int:
    port = start_port
    while port < start_port + 50:
        if not is_port_in_use(port, host):
            return port
        port += 1
    return start_port


class ServerThread(threading.Thread):
    def __init__(self, host: str, port: int):
        super().__init__(daemon=True)
        self.host = host
        self.port = port
        self.server = None

    def run(self):
        config = uvicorn.Config(
            app=app,
            host=self.host,
            port=self.port,
            log_level="warning",
            access_log=False
        )
        self.server = uvicorn.Server(config)
        self.server.run()

    def stop(self):
        if self.server:
            self.server.should_exit = True


def wait_for_server(host: str, port: int, timeout: float = 10.0) -> bool:
    start = time.time()
    while time.time() - start < timeout:
        if is_port_in_use(port, host):
            return True
        time.sleep(0.1)
    return False


def main():
    host = "127.0.0.1"
    port = 8500

    # If 8500 is already in use by a previously launched instance, find next free port
    if is_port_in_use(port, host):
        logger.info(f"Port {port} is in use; checking if engine is already running...")
        # Check if it responds to /api/status
        try:
            import urllib.request
            req = urllib.request.urlopen(f"http://{host}:{port}/api/status", timeout=1.0)
            if req.status == 200:
                logger.info(f"Existing engine instance detected on port {port}.")
                server_thread = None
            else:
                port = find_available_port(8501, host)
                server_thread = ServerThread(host, port)
                server_thread.start()
        except Exception:
            port = find_available_port(8501, host)
            server_thread = ServerThread(host, port)
            server_thread.start()
    else:
        server_thread = ServerThread(host, port)
        server_thread.start()

    url = f"http://{host}:{port}/"
    logger.info(f"Enterprise Payroll Engine ready at: {url}")
    wait_for_server(host, port, timeout=8.0)

    # Launch Native Windows Desktop Window
    use_webview = True
    if "--browser" in sys.argv:
        use_webview = False

    if use_webview:
        try:
            import webview
            logger.info("Initializing native Windows WebView container...")
            window = webview.create_window(
                title="IMBY Enterprise Payroll Deduction Automation Suite",
                url=url,
                width=1440,
                height=900,
                min_size=(1024, 700),
                confirm_close=False
            )
            webview.start(gui="edgechromium")
            logger.info("Desktop window closed by user. Terminating process.")
            if server_thread:
                server_thread.stop()
            sys.exit(0)
        except Exception as e:
            logger.warning(f"Native desktop container encountered error: {e}. Falling back to default browser...")

    # Fallback to browser
    webbrowser.open(url)
    print("=" * 76)
    print(" IMBY ENTERPRISE PAYROLL DEDUCTION SUITE - RUNNING")
    print("=" * 76)
    print(f" Workplace Web & Desktop UI: {url}")
    print(" Press CTRL+C to terminate application.")
    print("=" * 76)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        if server_thread:
            server_thread.stop()
        print("\n[OK] Application terminated.")


if __name__ == "__main__":
    main()
