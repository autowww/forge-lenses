"""LAN discovery helpers."""

from __future__ import annotations

import json
import subprocess

from lenses import fleet_lan_discover as fld


def test_probe_discovery_target_fleet(monkeypatch) -> None:
    def fake_probe(base: str, bearer: str, *, timeout_s: float = 0.45) -> dict:
        if not bearer:
            return {
                "http_status": 401,
                "is_fleet": False,
                "version": None,
                "auth_enforced": None,
                "ok_health": False,
            }
        return {
            "http_status": 200,
            "is_fleet": True,
            "version": {"package_semver": "1.2.3"},
            "auth_enforced": True,
            "ok_health": True,
        }

    monkeypatch.setattr(fld, "_probe_one_base", fake_probe)
    row = fld.probe_discovery_target("10.0.0.5", 18765, global_token="secret", timeout_s=0.1)
    assert row["is_fleet"] is True
    assert row["reachable"] is True
    assert row["version"] == {"package_semver": "1.2.3"}


def test_local_ipv4_link_networks_from_ip_json(monkeypatch) -> None:
    payload = [
        {
            "ifname": "eth0",
            "addr_info": [{"family": "inet", "local": "10.20.30.40", "prefixlen": 23}],
        }
    ]

    def fake_which(name: str) -> str | None:
        return "/fake/ip" if name == "ip" else None

    def fake_run(cmd: list[str], **_k: object) -> subprocess.CompletedProcess[str]:
        assert "-json" in cmd
        return subprocess.CompletedProcess(cmd, 0, json.dumps(payload), "")

    monkeypatch.setattr("lenses.fleet_lan_discover.shutil.which", fake_which)
    monkeypatch.setattr("lenses.fleet_lan_discover.subprocess.run", fake_run)
    nets = fld.local_ipv4_link_networks()
    assert len(nets) == 1
    assert nets[0]["network"] == "10.20.30.0/23"
    assert nets[0]["address"] == "10.20.30.40"
    assert nets[0]["prefixlen"] == 23


def test_default_scan_hosts_follows_interface_prefix(monkeypatch) -> None:
    monkeypatch.setattr(
        fld,
        "local_ipv4_link_networks",
        lambda: [
            {
                "interface": "eth0",
                "address": "10.0.0.5",
                "prefixlen": 24,
                "network": "10.0.0.0/24",
                "num_addresses": 256,
            },
        ],
    )
    hosts, meta = fld._default_scan_hosts("quick")
    assert meta[0]["network"] == "10.0.0.0/24"
    assert "10.0.0.5" in hosts
    assert "10.0.0.1" in hosts
    assert "127.0.0.1" in hosts


def test_run_discovery_filters_ports(monkeypatch) -> None:
    called: list[tuple[str, int]] = []

    def fake_probe(host: str, port: int, *, global_token: str = "", per_host_token: str = "", timeout_s: float = 0.45):
        called.append((host, port))
        return {
            "host": host,
            "port": port,
            "base_url": f"http://{host}:{port}",
            "reachable": False,
            "is_fleet": False,
            "auth_required": False,
            "version": None,
            "error": "skip",
        }

    monkeypatch.setattr(fld, "_default_scan_hosts", lambda mode: (["127.0.0.1"], []))
    monkeypatch.setattr(fld, "probe_discovery_target", fake_probe)
    out = fld.run_discovery(mode="quick", ports=[18765], extra_hosts=None, global_token="", timeout_s=0.05)
    assert out["ok"] is True
    assert out["ports"] == [18765]
    assert called == [("127.0.0.1", 18765)]
