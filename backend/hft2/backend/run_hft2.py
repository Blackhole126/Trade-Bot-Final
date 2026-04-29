#!/usr/bin/env python3
"""
Single entry point to run the full HFT2 stack:
- Fyers data service (port 8002) - with FYERS_ALLOW_MOCK=true if Fyers API unavailable
- MCP server (API on 8003, monitoring 8004)
- Web backend (port 5000) - the REAL bot API; all /api/start, /api/stop, predictions here
  Frontend hftApiService.ts talks to port 5000 by default.
- Monitors web_backend and auto-restarts if it crashes; Ctrl+C stops all

Usage:  cd backend/hft2/backend
        python run_hft2.py
"""
import os
import sys
import time
import signal
import subprocess
import atexit
import socket
from pathlib import Path

# Run from backend/hft2/backend
BACKEND_DIR = Path(__file__).resolve().parent
os.chdir(BACKEND_DIR)
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Load env from backend/hft2/env
ENV_FILE = BACKEND_DIR.parent / ".env"
if ENV_FILE.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(ENV_FILE)
    except ImportError:
        pass

# Child process handles; killed on exit
children = []


def is_port_in_use(port):
    """Check if a port is already in use - Windows compatible. Only checks LISTENING state."""
    import subprocess
    # Method 1: Try binding to the port (most reliable)
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('0.0.0.0', port))
                s.close()
                return False  # Port is free
            except OSError:
                return True  # Port is in use
    except Exception:
        pass
    
    # Method 2: Fallback - check via netstat on Windows (only LISTENING state)
    try:
        result = subprocess.run(
            ['netstat', '-ano'],
            capture_output=True,
            text=True,
            timeout=2
        )
        # Only check if port appears in LISTENING state (ignore TIME_WAIT, FIN_WAIT, etc.)
        for line in result.stdout.split('\n'):
            if f':{port}' in line and 'LISTENING' in line:
                return True
    except Exception:
        pass
    
    return False


def kill_children():
    for p in children:
        try:
            p.terminate()
            p.wait(timeout=5)
        except Exception:
            try:
                p.kill()
            except Exception:
                pass
    children.clear()


def start_subprocess(name, cmd, env_extra=None, wait_ready_sec=0, inherit_io=False):
    """Start a child process. If inherit_io=True, stdout/stderr go to terminal (no PIPE) so the
    child won't block on a full pipe; use for web_backend so it stays responsive and logs are visible."""
    env = os.environ.copy()
    if env_extra:
        env.update(env_extra)
    try:
        creationflags = 0
        if sys.platform == "win32":
            creationflags = subprocess.CREATE_NEW_PROCESS_GROUP
        if inherit_io:
            stdout_arg = None
            stderr_arg = None
        else:
            stdout_arg = subprocess.PIPE
            stderr_arg = subprocess.STDOUT
        p = subprocess.Popen(
            cmd,
            cwd=BACKEND_DIR,
            env=env,
            stdout=stdout_arg,
            stderr=stderr_arg,
            creationflags=creationflags,
        )
        children.append(p)
        if wait_ready_sec:
            time.sleep(wait_ready_sec)
        exit_code = p.poll()
        if exit_code is not None:
            if not inherit_io:
                msg = ""
                try:
                    stdout, _ = p.communicate(timeout=2)
                    msg = (stdout or b"").decode(errors="replace")[:800]
                    print(f"[run_hft2] {name} exited with code {exit_code}:\n{msg}")
                except subprocess.TimeoutExpired:
                    p.kill()
                    print(f"[run_hft2] {name} exited immediately (timeout reading output)")
                if msg and ("sqlalchemy" in msg.lower() or "No module named" in msg or "NameError" in msg):
                    print("[run_hft2] Missing dependencies! Install: pip install -r requirements-minimal.txt")
            else:
                print(f"[run_hft2] {name} exited with code {exit_code} (check output above)")
            children.remove(p)
            return None
        print(f"[run_hft2] Started {name} (PID {p.pid})")
        return p
    except Exception as e:
        print(f"[run_hft2] Failed to start {name}: {e}")
        return None


def wait_for_port(port, host="127.0.0.1", timeout_sec=15, step=0.5):
    """Return True when host:port is accepting connections."""
    start = time.time()
    while time.time() - start < timeout_sec:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                s.connect((host, port))
                return True
        except (OSError, socket.error):
            time.sleep(step)
    return False


def main():
    atexit.register(kill_children)

    def sig_handler(signum, frame):
        kill_children()
        sys.exit(0)

    signal.signal(signal.SIGINT, sig_handler)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, sig_handler)

    # 1) Fyers data service on 8002 (mock mode so it starts without fyers_apiv3)
    start_subprocess(
        "fyers_data_service (8002)",
        [sys.executable, "fyers_data_service.py", "--port", "8002"],
        env_extra={"FYERS_ALLOW_MOCK": "true"},
        wait_ready_sec=2,
    )

    # 2) MCP server (use 8004 for monitoring so 8002 stays for Fyers)
    start_subprocess(
        "start_mcp_server",
        [sys.executable, "start_mcp_server.py"],
        env_extra={"MCP_MONITORING_PORT": "8004", "MCP_API_PORT": "8003"},
        wait_ready_sec=3,
    )

    # 3) Web backend on 5000 (auth, MongoDB, trading-dashboard API) - inherit stdio so it doesn't block on PIPE
    print("[run_hft2] Starting web backend on port 5000 (auth + /docs)...")
    web_backend_proc = start_subprocess(
        "web_backend (5000)",
        [sys.executable, "web_backend.py", "--host", "0.0.0.0", "--port", "5000"],
        env_extra={"PYTHONUNBUFFERED": "1"},
        wait_ready_sec=10,
        inherit_io=True,
    )
    if web_backend_proc:
        if wait_for_port(5000, timeout_sec=60):
            print("[run_hft2] Web backend (5000) is ready. Dashboard auth: http://127.0.0.1:5000/docs")
        else:
            print("[run_hft2] WARNING: Port 5000 not responding. From repo root run: run_web_backend_only.bat to see web_backend errors.")
    else:
        print("[run_hft2] WARNING: web_backend (5000) did not start. From repo root run: run_web_backend_only.bat to see errors.")

    # 4) Note: api_server.py (port 8000) should be started separately for market scan
    #    Market scan endpoints: http://127.0.0.1:8000/tools/predict
    #    To start: cd backend && python api_server.py
    api_server_port = 8000
    if is_port_in_use(api_server_port):
        print(f"[run_hft2] Port {api_server_port} is in use - api_server.py appears to be running")
    else:
        print(f"[run_hft2] NOTE: Start api_server.py separately for market scan: cd backend && python api_server.py")

    # 5) Keep alive - web_backend (5000) IS the frontend's bot section.
    #    The frontend hftApiService.ts defaults to http://127.0.0.1:5000
    #    simple_app.py (port 5001) is NOT used; all real bot logic is in web_backend.
    print(f"[run_hft2] ============================================================")
    print(f"[run_hft2]  HFT2 stack is running. Press Ctrl+C to stop all.")
    print(f"[run_hft2]  Frontend BOT section -> http://127.0.0.1:5000/api/bot-data")
    print(f"[run_hft2]  Start bot           -> POST http://127.0.0.1:5000/api/start")
    print(f"[run_hft2]  API docs            -> http://127.0.0.1:5000/docs")
    if is_port_in_use(api_server_port):
        print(f"[run_hft2]  Market Scan        -> http://127.0.0.1:{api_server_port}/tools/predict")
    else:
        print(f"[run_hft2]  Market Scan: start api_server separately: cd backend && python api_server.py")
    print(f"[run_hft2] ============================================================")
    try:
        # Block here; Ctrl+C goes to sig_handler which kills children and exits
        while True:
            time.sleep(5)
            # Restart web_backend if it crashed
            if web_backend_proc and web_backend_proc.poll() is not None:
                print("[run_hft2] web_backend (5000) exited unexpectedly — restarting...")
                children.remove(web_backend_proc)
                new_proc = start_subprocess(
                    "web_backend (5000)",
                    [sys.executable, "web_backend.py", "--host", "0.0.0.0", "--port", "5000"],
                    env_extra={"PYTHONUNBUFFERED": "1"},
                    wait_ready_sec=5,
                    inherit_io=True,
                )
                if new_proc:
                    web_backend_proc = new_proc
    finally:
        kill_children()


if __name__ == "__main__":
    main()
