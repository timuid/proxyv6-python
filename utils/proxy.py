import re
import socket
from urllib.parse import urlsplit
import subprocess
import threading
import traceback

# running proxy cache: port -> {"thread": t, "stop": bool, "server_socket": sock}
_running_proxies = {}
lock = threading.Lock()


def create_proxy(data):
    """Start a simple proxy on port=data['port'] and bind outgoing source to data['ip']."""
    listen_port = data["port"]
    source_address = (data["ip"], 0)

    max_conn = 10000
    buffer_size = 8192

    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind(("", listen_port))
        server_socket.listen(max_conn)
    except Exception:
        return

    with lock:
        _running_proxies[listen_port] = {
            "thread": threading.current_thread(),
            "stop": False,
            "server_socket": server_socket,
        }

    try:
        while True:
            if _running_proxies[listen_port]["stop"]:
                break
            try:
                server_socket.settimeout(1.0)
                conn, _ = server_socket.accept()
                data = conn.recv(buffer_size)
                if not data:
                    conn.close()
                    continue
                threading.Thread(
                    target=handle_client,
                    args=(conn, data, source_address, buffer_size),
                    daemon=True,
                ).start()
            except socket.timeout:
                continue
            except Exception:
                traceback.print_exc()
    finally:
        server_socket.close()
        with lock:
            if listen_port in _running_proxies:
                del _running_proxies[listen_port]


def handle_client(conn, data, source_address, buffer_size):
    try:
        first_line = data.decode("latin-1", errors="ignore").split("\n")[0]
        if first_line.upper().startswith("CONNECT "):
            target_host, target_port = parse_connect_target(first_line)
            if not target_host or not target_port:
                conn.sendall(b"HTTP/1.1 400 Bad Request\r\n\r\n")
                return
            try:
                with socket.create_connection(
                    (target_host, target_port), source_address=source_address
                ) as remote_socket:
                    conn.sendall(b"HTTP/1.1 200 Connection established\r\n\r\n")
                    threading.Thread(
                        target=forward,
                        args=(conn, remote_socket, buffer_size),
                        daemon=True,
                    ).start()
                    forward(remote_socket, conn, buffer_size)
            except socket.gaierror:
                conn.sendall(b"HTTP/1.1 502 Bad Gateway\r\n\r\n")
        else:
            remote_socket = open_http_upstream(first_line, data, source_address)
            if not remote_socket:
                conn.sendall(b"HTTP/1.1 400 Bad Request\r\n\r\n")
                return
            with remote_socket:
                threading.Thread(
                    target=forward,
                    args=(conn, remote_socket, buffer_size),
                    daemon=True,
                ).start()
                forward(remote_socket, conn, buffer_size)
    except Exception:
        traceback.print_exc()
    finally:
        conn.close()


def parse_connect_target(first_line):
    parts = first_line.split(" ")
    if len(parts) < 2:
        return None, None
    target = parts[1]
    if target.startswith("[") and "]:" in target:
        host, raw_port = target[1:].rsplit("]:", 1)
        return host, int(raw_port)
    if ":" not in target:
        return None, None
    host, raw_port = target.rsplit(":", 1)
    return host, int(raw_port)


def open_http_upstream(first_line, raw_data, source_address):
    """Open upstream socket for regular HTTP proxy requests and send normalized data."""
    parts = first_line.split(" ", 2)
    if len(parts) < 3:
        return None

    method, target, version = parts
    parsed = urlsplit(target)
    if parsed.scheme and parsed.hostname:
        host = parsed.hostname
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        path = parsed.path or "/"
        if parsed.query:
            path = f"{path}?{parsed.query}"
    else:
        headers = raw_data.decode("latin-1", errors="ignore").split("\r\n")
        host_header = ""
        for header in headers[1:]:
            if header.lower().startswith("host:"):
                host_header = header.split(":", 1)[1].strip()
                break
        if not host_header:
            return None
        if ":" in host_header and not host_header.startswith("["):
            host, raw_port = host_header.rsplit(":", 1)
            port = int(raw_port)
        else:
            host = host_header.strip("[]")
            port = 80
        path = target or "/"

    normalized = raw_data.replace(
        first_line.encode("latin-1", errors="ignore"),
        f"{method} {path} {version}".encode("latin-1"),
        1,
    )
    upstream = socket.create_connection((host, port), source_address=source_address, timeout=15)
    upstream.sendall(normalized)
    return upstream


def forward(source, destination, buffer_size):
    try:
        while True:
            data = source.recv(buffer_size)
            if not data:
                break
            destination.sendall(data)
    except Exception:
        pass
    finally:
        source.close()
        destination.close()


def get_ipv6_addresses():
    """Extract IPv6 list from ipconfig."""
    result = subprocess.run(
        ["ipconfig"], capture_output=True, text=True, encoding="utf-8", errors="ignore"
    )
    output = result.stdout
    lines = [line.strip() for line in output.splitlines() if "IPv6 Address" in line]
    ipv6_pattern = r"([a-fA-F0-9:]+:[a-fA-F0-9:]+)"
    ipv6_addresses = [
        re.search(ipv6_pattern, line).group(1)
        for line in lines
        if re.search(ipv6_pattern, line)
    ]
    return ipv6_addresses


def start_multi_proxy(list_run_thread):
    """Start multiple proxies."""
    for data in list_run_thread:
        t = threading.Thread(target=create_proxy, args=(data,), daemon=True)
        t.start()


def stop_proxy(port: int):
    """Stop one proxy by port."""
    with lock:
        if port in _running_proxies:
            _running_proxies[port]["stop"] = True
            return True
    return False


def list_running_proxies():
    """Return running proxy ports."""
    with lock:
        # Treat proxies marked for stop as not-running so UI can update
        # immediately after a stop command, without waiting for thread teardown.
        return [
            port
            for port, meta in _running_proxies.items()
            if not bool(meta.get("stop"))
        ]


def runProxy():
    with open("ip6.txt", "r") as file_obj:
        list_ip = file_obj.readlines()
    ipv6_list = [ip.strip() for ip in list_ip]
    filtered_ipv6_list = [ip for ip in ipv6_list if "::" not in ip]
    start_port = 10000
    list_run_thread = [
        {"port": start_port + i, "ip": ipv6}
        for i, ipv6 in enumerate(filtered_ipv6_list)
    ]
    start_multi_proxy(list_run_thread)
