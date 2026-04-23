"""Fleet Studio status helpers."""

from __future__ import annotations

from lenses.sandbox import fleet_client as fc


def test_is_fleet_health_body() -> None:
    assert fc.is_fleet_health_body({"service": "forge-fleet", "ok": True}) is True
    assert fc.is_fleet_health_body({"service": "other", "ok": True}) is False
    assert fc.is_fleet_health_body({}) is False


def test_studio_fleet_status_connected() -> None:
    h = {"ok": True, "fleet": {"service": "forge-fleet", "ok": True}}
    assert fc.studio_fleet_status(stored_health=h, anon_health={"ok": False, "fleet": {}}) == "connected"


def test_studio_fleet_status_online() -> None:
    stored = {"ok": False, "http_status": 401, "fleet": {"error": "unauthorized"}}
    anon = {"ok": True, "http_status": 200, "fleet": {"service": "forge-fleet", "ok": True}}
    assert fc.studio_fleet_status(stored_health=stored, anon_health=anon) == "online"


def test_studio_fleet_status_needs_token() -> None:
    stored = {"ok": False, "http_status": 401, "fleet": {"ok": False, "error": "unauthorized"}}
    anon = {"ok": False, "http_status": 401, "fleet": {"ok": False, "error": "unauthorized"}}
    assert fc.studio_fleet_status(stored_health=stored, anon_health=anon) == "needs_token"


def test_studio_fleet_status_offline() -> None:
    stored = {"ok": False, "http_status": 0, "fleet": {}}
    anon = {"ok": False, "http_status": 0, "fleet": {}}
    assert fc.studio_fleet_status(stored_health=stored, anon_health=anon) == "offline"
