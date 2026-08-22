"""Server-side LAN discovery for Forge Fleet (default ports 18765 / 18766 / 18767).

Browsers cannot scan the LAN; Studio calls ``POST /api/fleet/discover`` and the
Lenses workspace server probes candidate addresses.

Scan ranges are derived from **local IPv4 link addresses and prefix lengths**
(``ip -json addr`` when available), so targets match each interface's real subnet
instead of assuming an arbitrary /24.
"""

from __future__ import annotations

import ipaddress
import json
import shutil
import socket
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from lenses.sandbox import fleet_client as fleet_cli

# 18765/18766 — direct ``fleet_server`` installs; 18767 — common Caddy public HTTP front (see forge-fleet Caddy docs).
_DEFAULT_PORTS = (18765, 18766, 18767)
_QUICK_HOSTS_PER_SLICE = 32
_MAX_SUBNET_HOSTS = 8192
_SUBNET_WORKERS = 40
_PROBE_TIMEOUT_S = 0.45


def local_ipv4_link_networks() -> list[dict[str, Any]]:
    """
    IPv4 networks configured on this host (address + prefixlen), excluding loopback.

    Primary source: ``ip -json addr show up`` (same data as ``ip addr`` / kernel state).
    Fallback: single guessed ``/24`` from the outbound UDP trick when ``ip`` is unavailable.
    """
    out: list[dict[str, Any]] = []
    ip_bin = shutil.which("ip")
    if ip_bin:
        r: subprocess.CompletedProcess[str] | None = None
        for extra in (["up"], []):
            try:
                r = subprocess.run(
                    [ip_bin, "-json", "addr", "show", *extra],
                    capture_output=True,
                    text=True,
                    timeout=4.0,
                )
            except (OSError, subprocess.TimeoutExpired):
                r = subprocess.CompletedProcess(args=[], returncode=-1, stdout="", stderr="")
            if r.returncode == 0 and (r.stdout or "").strip():
                break
        if r and r.returncode == 0 and (r.stdout or "").strip():
            try:
                blocks = json.loads(r.stdout)
            except json.JSONDecodeError:
                blocks = []
            if isinstance(blocks, list):
                for blk in blocks:
                    if not isinstance(blk, dict):
                        continue
                    ifname = str(blk.get("ifname") or "").strip()
                    if not ifname or ifname == "lo":
                        continue
                    for ainfo in blk.get("addr_info") or []:
                        if not isinstance(ainfo, dict):
                            continue
                        if str(ainfo.get("family") or "") != "inet":
                            continue
                        loc = str(ainfo.get("local") or "").strip()
                        plen = ainfo.get("prefixlen")
                        if not loc or plen is None:
                            continue
                        try:
                            pl = int(plen)
                            iface = ipaddress.IPv4Interface(f"{loc}/{pl}")
                        except (ValueError, TypeError):
                            continue
                        net = iface.network
                        out.append(
                            {
                                "interface": ifname,
                                "address": loc,
                                "prefixlen": pl,
                                "network": str(net),
                                "num_addresses": net.num_addresses,
                            }
                        )
    if out:
        return _dedupe_network_entries(out)

    prim = _primary_local_via_udp()
    if prim:
        try:
            iface = ipaddress.IPv4Interface(f"{prim}/24")
            net = iface.network
            out.append(
                {
                    "interface": "fallback",
                    "address": prim,
                    "prefixlen": 24,
                    "network": str(net),
                    "num_addresses": net.num_addresses,
                    "source": "udp_guess_slash24",
                }
            )
        except ValueError:
            pass
    return _dedupe_network_entries(out)


def _dedupe_network_entries(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One row per (interface, network); keep first occurrence."""
    seen: set[tuple[str, str]] = set()
    rows: list[dict[str, Any]] = []
    for it in items:
        k = (str(it.get("interface") or ""), str(it.get("network") or ""))
        if not k[1] or k in seen:
            continue
        seen.add(k)
        rows.append(it)
    return rows


def _primary_local_via_udp() -> str | None:
    """Outbound interface IPv4 (no traffic sent)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.25)
        s.connect(("192.0.2.1", 1))
        ip = s.getsockname()[0]
        s.close()
        if ip and not ip.startswith("127."):
            return ip
    except OSError:
        pass
    return None


def _network_for_quick_scan(iface: ipaddress.IPv4Interface) -> ipaddress.IPv4Network:
    """
    In quick mode, scan at most one ``/24`` slice: the interface's own network if it is
    /24 or longer; otherwise the ``/24`` that contains this host (same third octet class).
    """
    net = iface.network
    if net.prefixlen >= 24:
        return net
    ip = iface.ip
    o = int(ip)
    base = o & 0xFFFFFF00
    return ipaddress.ip_network((base, 24), strict=False)


def _hosts_for_interface_network(iface: ipaddress.IPv4Interface, *, quick: bool) -> list[str]:
    """Host IPs to probe for one interface, respecting ``quick`` vs full subnet."""
    net = iface.network
    if quick:
        scan_net = _network_for_quick_scan(iface)
        hosts: list[str] = []
        # .1 .. .N within that network (skip network/broadcast for typical nets)
        if scan_net.prefixlen <= 30:
            upper = min(_QUICK_HOSTS_PER_SLICE, scan_net.num_addresses - 2)
            for i in range(1, max(upper, 1) + 1):
                try:
                    hosts.append(str(scan_net.network_address + i))
                except ValueError:
                    break
        else:
            hosts.append(str(iface.ip))
        hi = str(iface.ip)
        if hi not in hosts:
            hosts.insert(0, hi)
        return hosts

    # Full subnet mode — entire on-link prefix, capped for safety
    out: list[str] = []
    for h in net.hosts():
        out.append(str(h))
        if len(out) >= _MAX_SUBNET_HOSTS:
            break
    if str(iface.ip) not in out:
        out.insert(0, str(iface.ip))
    return out


def _default_scan_hosts(mode: str) -> tuple[list[str], list[dict[str, Any]]]:
    """
    Return ``(ordered_hosts, networks_meta)`` from local interface configuration.
    """
    seen: dict[str, None] = {}
    order: list[str] = []

    def add(h: str) -> None:
        h = (h or "").strip()
        if not h or h in seen:
            return
        try:
            ipaddress.IPv4Address(h)
        except ValueError:
            return
        seen[h] = None
        order.append(h)

    networks = local_ipv4_link_networks()
    quick = mode != "subnet"

    add("127.0.0.1")

    for meta in networks:
        addr = str(meta.get("address") or "").strip()
        pl = meta.get("prefixlen")
        if not addr or pl is None:
            continue
        try:
            iface = ipaddress.IPv4Interface(f"{addr}/{int(pl)}")
        except (ValueError, TypeError):
            continue
        for h in _hosts_for_interface_network(iface, quick=quick):
            add(h)

    return order, networks


def _probe_one_base(
    base_url: str,
    bearer: str,
    *,
    timeout_s: float = _PROBE_TIMEOUT_S,
) -> dict[str, Any]:
    code, body = fleet_cli._req(  # noqa: SLF001
        "GET",
        f"{base_url.rstrip('/')}/v1/health",
        bearer=bearer,
        timeout_s=timeout_s,
    )
    is_fleet = fleet_cli.is_fleet_health_body(body)
    ver = body.get("version") if isinstance(body.get("version"), dict) else {}
    return {
        "http_status": code,
        "is_fleet": is_fleet,
        "version": ver if is_fleet else None,
        "auth_enforced": body.get("auth_enforced") if isinstance(body, dict) else None,
        "ok_health": code < 400 and bool(body.get("ok", True)) and is_fleet,
    }


def probe_discovery_target(
    host: str,
    port: int,
    *,
    global_token: str = "",
    per_host_token: str = "",
    timeout_s: float = _PROBE_TIMEOUT_S,
) -> dict[str, Any]:
    """
    Try unauthenticated health, then ``global_token``, then ``per_host_token``.
    """
    base = f"http://{host}:{port}"
    out: dict[str, Any] = {
        "host": host,
        "port": port,
        "base_url": base,
        "reachable": False,
        "is_fleet": False,
        "auth_required": False,
        "version": None,
        "error": None,
    }
    tokens_try = ["", global_token.strip(), per_host_token.strip()]
    seen: set[str] = set()
    ordered_toks: list[str] = []
    for t in tokens_try:
        if t in seen:
            continue
        seen.add(t)
        ordered_toks.append(t)

    last_http = 0
    for tok in ordered_toks:
        r = _probe_one_base(base, tok, timeout_s=timeout_s)
        last_http = int(r.get("http_status") or 0)
        if r.get("ok_health"):
            out["reachable"] = True
            out["is_fleet"] = True
            out["version"] = r.get("version")
            out["auth_required"] = bool(r.get("auth_enforced")) and tok == ""
            return out
        if last_http == 401:
            out["reachable"] = True

    if last_http == 401:
        out["auth_required"] = True
        out["error"] = "unauthorized_try_token"
        return out
    if last_http == 0:
        out["error"] = "network_or_timeout"
    else:
        out["error"] = f"http_{last_http}"
    return out


def run_discovery(
    *,
    mode: str = "quick",
    ports: list[int] | None = None,
    extra_hosts: list[str] | None = None,
    global_token: str = "",
    timeout_s: float = _PROBE_TIMEOUT_S,
) -> dict[str, Any]:
    """
    ``mode``: ``quick`` (capped sweep per interface-derived range) or ``subnet``
    (all host addresses in each interface prefix, capped at ``_MAX_SUBNET_HOSTS`` per network).
    """
    port_list = [int(p) for p in (ports or list(_DEFAULT_PORTS)) if 0 < int(p) < 65536]
    if not port_list:
        port_list = list(_DEFAULT_PORTS)
    hosts, networks_meta = _default_scan_hosts(mode)
    if extra_hosts:
        for h in extra_hosts:
            h = str(h or "").strip()
            if not h:
                continue
            try:
                ipaddress.IPv4Address(h)
            except ValueError:
                continue
            if h not in hosts:
                hosts.append(h)

    targets: list[tuple[str, int]] = []
    for h in hosts:
        for prt in port_list:
            targets.append((h, prt))

    max_workers = _SUBNET_WORKERS if mode == "subnet" else min(24, max(4, len(targets)))
    rows: list[dict[str, Any]] = []
    lock = threading.Lock()

    def work(t: tuple[str, int]) -> None:
        host, prt = t
        row = probe_discovery_target(host, prt, global_token=global_token, timeout_s=timeout_s)
        with lock:
            rows.append(row)

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = [ex.submit(work, t) for t in targets]
        for f in as_completed(futs):
            try:
                f.result()
            except Exception as exn:  # noqa: BLE001
                with lock:
                    rows.append({"host": "", "port": 0, "base_url": "", "error": str(exn)[:500]})

    rows.sort(key=lambda r: (str(r.get("host") or ""), int(r.get("port") or 0)))
    found = [r for r in rows if r.get("is_fleet")]
    return {
        "ok": True,
        "mode": mode,
        "ports": port_list,
        "targets_scanned": len(targets),
        "fleet_found": len(found),
        "local_networks": networks_meta,
        "candidates": rows,
    }
