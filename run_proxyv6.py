"""One-command runner for Proxy IPv6 Manager on Windows and Linux.

Usage examples:
  python run_proxyv6.py
  python run_proxyv6.py --count 3 --group group-main
  python run_proxyv6.py --no-auto-create
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
import time
import urllib.error
import urllib.request
import venv
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV_DIR = ROOT / "venv"
REQ_FILE = ROOT / "requirements.txt"
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 9002


def is_windows() -> bool:
    return platform.system().lower() == "windows"


def venv_python() -> Path:
    if is_windows():
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def ensure_venv() -> None:
    if not venv_python().exists():
        print("[1/5] Tao moi venv...")
        venv.EnvBuilder(with_pip=True, clear=False).create(VENV_DIR)


def run_command(command: list[str], **kwargs) -> None:
    print("$", " ".join(command))
    subprocess.check_call(command, cwd=ROOT, **kwargs)


def install_requirements() -> None:
    py = str(venv_python())
    print("[2/5] Cai/cap nhat pip va thu vien...")
    run_command([py, "-m", "ensurepip", "--upgrade"])
    run_command([py, "-m", "pip", "install", "--upgrade", "pip"])
    run_command([py, "-m", "pip", "install", "-r", str(REQ_FILE)])


def relaunch_inside_venv(args: list[str]) -> None:
    os.execv(
        str(venv_python()),
        [str(venv_python()), str(ROOT / "run_proxyv6.py"), "--skip-bootstrap", *args],
    )


def api_url(port: int, path: str) -> str:
    return f"http://127.0.0.1:{port}{path}"


def request_json(
    method: str,
    port: int,
    path: str,
    payload: dict | None = None,
    timeout: float = 10,
) -> dict | list:
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(
        api_url(port, path), data=data, headers=headers, method=method
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        body = response.read().decode("utf-8")
        return json.loads(body) if body else {}


def wait_for_server(port: int, timeout: int = 60) -> dict:
    deadline = time.time() + timeout
    last_error = ""
    while time.time() < deadline:
        try:
            data = request_json("GET", port, "/system/status", timeout=2)
            if isinstance(data, dict):
                return data
        except Exception as exc:  # server is still booting
            last_error = str(exc)
            time.sleep(1)
    raise RuntimeError(f"Server khong san sang sau {timeout}s: {last_error}")


def start_server(host: str, port: int) -> subprocess.Popen:
    env = os.environ.copy()
    env["PROXYV6_HOST"] = host
    env["PROXYV6_PORT"] = str(port)
    print(f"[3/5] Khoi dong server tren http://127.0.0.1:{port} ...")
    return subprocess.Popen([sys.executable, str(ROOT / "server.py")], cwd=ROOT, env=env)


def open_ui(port: int) -> None:
    url = f"http://127.0.0.1:{port}"
    print(f"[4/5] Mo giao dien: {url}")
    try:
        webbrowser.open(url, new=2)
    except Exception as exc:
        print(f"Khong tu mo duoc browser, hay mo thu cong {url}. Loi: {exc}")


def auto_create_proxies(port: int, group: str, count: int, interface: str | None) -> None:
    if count <= 0:
        print("[5/5] Bo qua auto tao proxy (--no-auto-create).")
        return

    status = wait_for_server(port)
    selected_interface = interface or status.get("default_adapter")
    if not selected_interface:
        print("[5/5] Khong tim thay card mang. Vao UI chon card roi tao proxy thu cong.")
        return

    print(f"[5/5] Tu dong tao {count} proxy tren card '{selected_interface}'...")
    try:
        result = request_json(
            "POST",
            port,
            "/proxy/create",
            {"group_name": group, "interface_name": selected_interface, "count": count},
            timeout=120,
        )
        created = result.get("created", []) if isinstance(result, dict) else []
        if isinstance(result, dict) and "port" in result:
            created = [result]
        ports = [str(item.get("port")) for item in created if item.get("port")]
        print(f"Da tao/chay proxy: {', '.join(ports) if ports else result}")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        print("Tao proxy tu dong bi loi. Thu chay bang Administrator/root va kiem tra IPv6 card mang.")
        print(detail)
    except Exception as exc:
        print(f"Tao proxy tu dong bi loi: {exc}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Proxy IPv6 Manager one-command runner")
    parser.add_argument("--host", default=os.getenv("PROXYV6_HOST", DEFAULT_HOST))
    parser.add_argument("--port", type=int, default=int(os.getenv("PROXYV6_PORT", DEFAULT_PORT)))
    parser.add_argument(
        "--count",
        type=int,
        default=int(os.getenv("PROXYV6_AUTO_COUNT", "3")),
        help="So proxy tu dong tao khi chay",
    )
    parser.add_argument("--group", default=os.getenv("PROXYV6_GROUP", "group-main"))
    parser.add_argument(
        "--interface",
        default=os.getenv("PROXYV6_INTERFACE", ""),
        help="Ten card mang; bo trong de tu nhan",
    )
    parser.add_argument("--no-auto-create", action="store_true", help="Chi mo UI, khong tu tao proxy")
    parser.add_argument("--skip-bootstrap", action="store_true", help=argparse.SUPPRESS)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.skip_bootstrap:
        ensure_venv()
        install_requirements()
        remaining = [arg for arg in sys.argv[1:] if arg != "--skip-bootstrap"]
        relaunch_inside_venv(remaining)
        return 0

    print(f"He dieu hanh: {platform.system()} | Python: {sys.version.split()[0]}")
    server = start_server(args.host, args.port)
    try:
        wait_for_server(args.port)
        open_ui(args.port)
        auto_count = 0 if args.no_auto_create else args.count
        auto_create_proxies(args.port, args.group, auto_count, args.interface.strip() or None)
        print("Server dang chay. Nhan Ctrl+C de dung.")
        return server.wait()
    except KeyboardInterrupt:
        print("Dang dung server...")
        return 0
    finally:
        if server.poll() is None:
            server.terminate()
            try:
                server.wait(timeout=8)
            except subprocess.TimeoutExpired:
                server.kill()


if __name__ == "__main__":
    raise SystemExit(main())
