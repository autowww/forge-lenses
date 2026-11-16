"""Tests for multi-pipeline discovery."""

from __future__ import annotations

from pathlib import Path

from lenses.deploy_orchestrator import pipeline_spec


def test_discover_pipelines_includes_default_and_clean(tmp_path: Path):
    proj = tmp_path / "forge-market"
    (proj / "forge").mkdir(parents=True)
    (proj / "forge" / "delivery-pipeline.yaml").write_text(
        "schema_version: 1\napp: x\nartifact: {kind: docker_image, repository: r, tag_strategy: git_sha}\n"
        "environments: [{id: dev, rank: 1, gateway_slug: g, container_service_id: c, compose_root: d, host_port: 1}]\n"
        "gates: []\n",
        encoding="utf-8",
    )
    pipe_dir = proj / "forge" / "pipelines"
    pipe_dir.mkdir()
    (pipe_dir / "clean.yaml").write_text(
        "schema_version: 1\npipeline_id: clean\napp: x\nartifact: {kind: docker_image, repository: r, tag_strategy: git_sha}\n"
        "environments: [{id: clean, rank: 1, gateway_slug: g, container_service_id: c, compose_root: d, host_port: 2}]\n"
        "gates: []\n",
        encoding="utf-8",
    )
    grouped = pipeline_spec.discover_pipelines(tmp_path)
    assert "forge-market" in grouped
    assert "default" in grouped["forge-market"]
    assert "clean" in grouped["forge-market"]
