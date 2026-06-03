from __future__ import annotations

import asyncio
import base64
import ctypes
import ipaddress
import json
import os
import platform
import random
import re
import socket
import shutil
import subprocess
import time

import httpx

_CACHE_DURATION = 100

_cached_ip = None
_cached_time = 0


def _is_windows() -> bool:
    return platform.system().lower() == "windows"


def _is_linux() -> bool:
    return platform.system().lower() == "linux"


def get_platform_name() -> str:
    """Return a compact OS name used by the runner and diagnostics API."""
    if _is_windows():
        return "windows"
    if _is_linux():
        return "linux"
    return platform.system().lower() or "unknown"


def is_admin():
    """Check if the script is running with administrator/root privileges."""
    if _is_windows():
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except Exception:
            return False

    if hasattr(os, "geteuid"):
        return os.geteuid() == 0

    return False


def _ps_escape(value: str) -> str:
    return str(value).replace("'", "''")


def _run_checked(command, **kwargs):
    result = subprocess.run(command, text=True, capture_output=True, **kwargs)
    if result.returncode != 0:
        output = (result.stderr or result.stdout or "Unknown error").strip()
        raise RuntimeError(output)
    return result


def _run_powershell(command: str):
    _run_checked(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command]
    )


def _run_powershell_with_uac(command: str):
    encoded = base64.b64encode(command.encode("utf-16le")).decode("ascii")
    launcher_script = (
        f"$arg='-NoProfile -ExecutionPolicy Bypass -EncodedCommand {encoded}'; "
        "$p = Start-Process -FilePath 'powershell' -Verb RunAs -ArgumentList $arg -Wait -PassThru; "
        "exit $p.ExitCode"
    )
    try:
        _run_checked(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                launcher_script,
            ]
        )
    except RuntimeError as exc:
        output = str(exc)
        lowered = output.lower()
        if "canceled" in lowered or "cancelled" in lowered or "1223" in lowered:
            raise PermissionError("Administrator permission was canceled by user.")
        raise


def _run_with_optional_uac(command: str):
    if is_admin():
        _run_powershell(command)
    else:
        _run_powershell_with_uac(command)


def _require_ip_command():
    if not shutil.which("ip"):
        raise RuntimeError("Linux requires the 'ip' command from iproute2.")


def _run_ip_command(args):
    _require_ip_command()
    return _run_checked(["ip", *args])


async def ensure_admin_permission():
    if is_admin():
        return

    if _is_windows():
        command = "Write-Output 'admin-check' | Out-Null"
        try:
            await asyncio.to_thread(_run_powershell_with_uac, command)
        except PermissionError:
            raise RuntimeError("UAC was canceled. Please allow Administrator permission.")
        except RuntimeError as exc:
            raise RuntimeError(f"Administrator check failed: {exc}")
        return

    if _is_linux():
        raise RuntimeError("Root permission is required on Linux. Run the server with sudo/root.")

    raise RuntimeError("Administrator/root permission is required on this operating system.")


def _adapter_has_global_ipv6(interface_name: str) -> str | None:
    adapter = get_ipv6_by_card_name(interface_name)
    if not adapter:
        return None
    for item in adapter.get("ipv6", []):
        value = (item.get("value") or "").split("%")[0].split("(")[0].strip()
        try:
            ip_obj = ipaddress.IPv6Address(value)
        except ipaddress.AddressValueError:
            continue
        if ip_obj.is_global:
            return value
    return None


def generate_ipv6_addresses(count=1, interface_name: str | None = None):
    base_ipv6 = None
    if interface_name:
        base_ipv6 = _adapter_has_global_ipv6(interface_name)
    if not base_ipv6:
        base_ipv6 = get_ethernet_ipv6_addresses()
    if not base_ipv6:
        return []

    try:
        base_ip = ipaddress.IPv6Address(base_ipv6)
    except ipaddress.AddressValueError:
        return []

    network = ipaddress.IPv6Network(f"{base_ip}/64", strict=False)
    generated = set()
    while len(generated) < max(1, int(count)):
        host_id = random.getrandbits(64) or 1
        generated.add(str(ipaddress.IPv6Address(int(network.network_address) + host_id)))
    return list(generated)


def get_ethernet_ipv6_addresses() -> str:
    global _cached_ip, _cached_time

    now = time.time()
    if _cached_ip and (now - _cached_time) < _CACHE_DURATION:
        return _cached_ip

    try:
        with httpx.Client(timeout=5) as client:
            response = client.get("https://api64.ipify.org/?format=json")
            response.raise_for_status()
            ip = response.json().get("ip")
            if ip and ":" in ip:
                _cached_ip = ip
                _cached_time = time.time()
                return ip
    except Exception:
        pass

    return None


async def add_ipv6_to_ethernet(ipv6_address, interface_name="Ethernet"):
    if _is_windows():
        interface = _ps_escape(interface_name)
        ipv6 = _ps_escape(ipv6_address)

        command = (
            f"New-NetIPAddress -InterfaceAlias '{interface}' -IPAddress '{ipv6}' -PrefixLength 64 -AddressFamily IPv6 -ErrorAction Stop; "
            f"Set-DnsClientServerAddress -InterfaceAlias '{interface}' -ServerAddresses @('2001:4860:4860::8888','2001:4860:4860::8844') -ErrorAction Stop"
        )

        try:
            await asyncio.to_thread(_run_with_optional_uac, command)
        except PermissionError:
            raise RuntimeError("UAC was canceled. Please allow Administrator permission.")
        except RuntimeError as exc:
            raise RuntimeError(f"Add IPv6 failed: {exc}")
        return

    if _is_linux():
        if not is_admin():
            raise RuntimeError("Root permission is required on Linux to add IPv6 addresses.")
        try:
            await asyncio.to_thread(
                _run_ip_command,
                ["-6", "addr", "add", f"{ipv6_address}/64", "dev", interface_name],
            )
        except RuntimeError as exc:
            lowered = str(exc).lower()
            if "file exists" in lowered:
                return
            raise RuntimeError(f"Add IPv6 failed: {exc}")
        return

    raise RuntimeError(f"Unsupported operating system: {platform.system()}")


async def remove_ipv6_address(ipv6_address, interface_name="Ethernet"):
    if _is_windows():
        interface = _ps_escape(interface_name)
        ipv6 = _ps_escape(ipv6_address)

        command = (
            f"Remove-NetIPAddress -InterfaceAlias '{interface}' -IPAddress '{ipv6}' "
            "-AddressFamily IPv6 -Confirm:$false -ErrorAction Stop"
        )

        try:
            await asyncio.to_thread(_run_with_optional_uac, command)
        except PermissionError:
            raise RuntimeError("UAC was canceled. Please allow Administrator permission.")
        except RuntimeError as exc:
            lowered = str(exc).lower()
            if "no matching msft_netipaddress" in lowered:
                return
            raise RuntimeError(f"Remove IPv6 failed: {exc}")
        return

    if _is_linux():
        if not is_admin():
            raise RuntimeError("Root permission is required on Linux to remove IPv6 addresses.")
        try:
            await asyncio.to_thread(
                _run_ip_command,
                ["-6", "addr", "del", f"{ipv6_address}/64", "dev", interface_name],
            )
        except RuntimeError as exc:
            lowered = str(exc).lower()
            if "cannot assign requested address" in lowered or "not found" in lowered:
                return
            raise RuntimeError(f"Remove IPv6 failed: {exc}")
        return

    raise RuntimeError(f"Unsupported operating system: {platform.system()}")


def _get_windows_adapters_ipv4():
    result = subprocess.run(
        ["ipconfig"], capture_output=True, text=True, encoding="utf-8", errors="ignore"
    )
    lines = result.stdout.splitlines()

    adapters = []
    current_adapter = None
    adapter_info = {}

    for line in lines:
        adapter_match = re.match(r"^\s*([^\r\n:]+ adapter .+):", line)
        if adapter_match:
            if current_adapter and "ipv4" in adapter_info:
                adapters.append(adapter_info)

            current_adapter = adapter_match.group(1).split("adapter ")[-1].strip()
            adapter_info = {"card_name": current_adapter}

        ipv4_match = re.search(r"IPv4 Address[\s.]*: ([^\s]+)", line)
        if ipv4_match:
            adapter_info["ipv4"] = ipv4_match.group(1)

    if current_adapter and "ipv4" in adapter_info:
        adapters.append(adapter_info)

    return adapters


def _linux_addr_json(*args):
    _require_ip_command()
    result = _run_checked(["ip", "-j", *args])
    return json.loads(result.stdout or "[]")


def _get_linux_adapters_ipv4():
    if not shutil.which("ip"):
        return []

    adapters = []
    for item in _linux_addr_json("-4", "addr", "show"):
        if item.get("operstate") == "DOWN":
            continue
        if item.get("ifname") == "lo" or "LOOPBACK" in item.get("flags", []):
            continue
        info = {"card_name": item.get("ifname", "")}
        for addr in item.get("addr_info", []):
            if addr.get("family") == "inet" and addr.get("local"):
                info["ipv4"] = addr["local"]
                break
        if info.get("card_name") and info.get("ipv4"):
            adapters.append(info)
    return adapters


def get_adapters_ipv4():
    if _is_windows():
        return _get_windows_adapters_ipv4()
    if _is_linux():
        return _get_linux_adapters_ipv4()
    return []


def _get_windows_adapters_ipv6(debug: bool = False):
    result = subprocess.run(
        ["ipconfig"], capture_output=True, text=True, encoding="utf-8", errors="ignore"
    )
    lines = result.stdout.splitlines()

    adapters = []
    current_adapter = None
    adapter_info = {}
    ipv6_list = []

    for line in lines:
        if debug:
            print(f"[LINE] {line}")

        adapter_match = re.match(r"^\s*([^\r\n:]+ adapter .+):", line)
        if adapter_match:
            if current_adapter and ipv6_list:
                adapter_info["ipv6"] = ipv6_list
                adapters.append(adapter_info)

            current_adapter = adapter_match.group(1).split("adapter ")[-1].strip()
            adapter_info = {"card_name": current_adapter}
            ipv6_list = []
            if debug:
                print(f"--> Found adapter: {current_adapter}")
            continue

        if current_adapter:
            if not line.strip():
                continue

            if "IPv6 Address" in line or "Temporary IPv6 Address" in line:
                parts = line.split(":", 1)
                if len(parts) == 2:
                    addr = parts[1].strip().split("%")[0].split("(")[0].strip()
                    addr_type = (
                        "Temporary IPv6 Address"
                        if "Temporary" in line
                        else "IPv6 Address"
                    )
                    ipv6_list.append({"type": addr_type, "value": addr})

    if current_adapter and ipv6_list:
        adapter_info["ipv6"] = ipv6_list
        adapters.append(adapter_info)

    return adapters


def _get_linux_adapters_ipv6():
    if not shutil.which("ip"):
        return []

    adapters = []
    for item in _linux_addr_json("-6", "addr", "show"):
        ipv6_list = []
        for addr in item.get("addr_info", []):
            if addr.get("family") != "inet6" or not addr.get("local"):
                continue
            scope = addr.get("scope", "global")
            ipv6_list.append(
                {
                    "type": "IPv6 Address" if scope == "global" else f"IPv6 Address ({scope})",
                    "value": addr["local"].split("%")[0],
                }
            )
        if ipv6_list:
            adapters.append({"card_name": item.get("ifname", ""), "ipv6": ipv6_list})
    return adapters


def get_default_adapter_name() -> str:
    """Pick a sensible default adapter for one-click startup."""
    adapters = get_adapters_ipv4()
    if adapters:
        hostname = socket.gethostname().lower()
        preferred_words = ("ethernet", "wi-fi", "wifi", "wlan", "eth", "ens", "enp")
        for adapter in adapters:
            name = (adapter.get("card_name") or "").lower()
            ipv4 = adapter.get("ipv4") or ""
            if ipv4.startswith("127.") or name in {"lo", "loopback"}:
                continue
            if any(word in name for word in preferred_words) or hostname:
                return adapter.get("card_name") or ""
        return adapters[0].get("card_name") or ""

    if _is_windows():
        return "Ethernet"
    return "eth0"


def get_adapters_ipv6(debug: bool = False):
    if _is_windows():
        return _get_windows_adapters_ipv6(debug)
    if _is_linux():
        return _get_linux_adapters_ipv6()
    return []


def get_ipv6_by_card_name(card_name: str):
    """Return all IPv6 Address and Temporary IPv6 Address by card name."""
    adapters = get_adapters_ipv6()
    for adapter in adapters:
        if adapter["card_name"].lower() == card_name.lower():
            return adapter
    return None
