"""Fleet Test Fleet batch helper when no Fleet nodes are configured."""

from __future__ import annotations

from pathlib import Path

from lenses.sandbox.fleet_client import run_test_fleet_batch


def test_run_test_fleet_batch_not_configured(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("LENSES_FLEET_URL", "")
    monkeypatch.delenv("LENSES_FLEET_TOKEN", raising=False)
    d = tmp_path / ".lenses-local"
    d.mkdir(parents=True)
    (d / "fleet-settings.json").write_text('{"version":2,"nodes":[]}', encoding="utf-8")
    out = run_test_fleet_batch(tmp_path, count=5)
    assert out.get("ok") is False
    assert out.get("error") == "fleet_not_configured_or_no_eligible_node"
    assert "hint" in out and "Save" in str(out.get("hint"))
