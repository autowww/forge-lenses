"""HTTP integration tests: Cursor Launch Pack staged download (GET after POST)."""

from __future__ import annotations

import json
import os
import threading
import time
import urllib.parse
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

from lenses.auth_session import SessionManager
from lenses.blueprints_wizard.artifact_generation_service import generate_artifacts
from lenses.serve import LensesHandler

from tests.test_cursor_launch_pack import _minimal_session


@pytest.fixture
def lenses_http_server(tmp_path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("LENSES_ARTIFACT_GENERATION_MOCK", "1")
    wr = tmp_path.resolve()
    LensesHandler.workspace_root = wr
    LensesHandler.registry = {}
    LensesHandler.expected_github_login = None
    LensesHandler.session_manager = SessionManager(wr)
    server = ThreadingHTTPServer(("127.0.0.1", 0), LensesHandler)
    port = server.server_address[1]
    th = threading.Thread(target=server.serve_forever, daemon=True)
    th.start()
    try:
        yield wr, port
    finally:
        server.shutdown()
        server.server_close()
        th.join(timeout=10)


def test_http_stream_export_then_get_zip_bytes(
    lenses_http_server: tuple[Path, int], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LENSES_EXPERIMENTAL_BLUEPRINTS_WIZARD", "1")
    wr, port = lenses_http_server
    sid = _minimal_session(wr)
    g = generate_artifacts(wr, sid, {"provider": "openai", "artifact": "roadmap"})
    assert g.get("ok") is True

    enc_sid = urllib.parse.quote(sid, safe="")
    body = json.dumps(
        {
            "artifact_keys": ["roadmap"],
            "closure_options": ["exact_only"],
            "destination": "download",
            "stream": True,
        }
    ).encode("utf-8")

    conn = HTTPConnection("127.0.0.1", port)
    conn.request(
        "POST",
        f"/api/blueprints/wizard/session/{enc_sid}/cursor-launch-pack/export",
        body=body,
        headers={"Content-Type": "application/json"},
    )
    post_resp = conn.getresponse()
    assert post_resp.status == 200
    payload = json.loads(post_resp.read().decode("utf-8"))
    conn.close()

    assert payload.get("ok") is True
    assert payload.get("download_mode") == "stream"
    dl_path = payload.get("download_path")
    assert isinstance(dl_path, str) and dl_path.startswith("/")

    conn = HTTPConnection("127.0.0.1", port)
    conn.request("GET", dl_path)
    get_resp = conn.getresponse()
    assert get_resp.status == 200
    raw = get_resp.read()
    conn.close()

    assert raw.startswith(b"PK")
    assert len(raw) == int(payload.get("byte_length") or 0)


def test_cleanup_expired_staged_zips_removes_old_files(tmp_path: Path) -> None:
    from lenses.blueprints_wizard.launch_pack_staging import cleanup_expired_staged_zips, staging_session_dir

    d = staging_session_dir(tmp_path, "sess-a")
    d.mkdir(parents=True)
    p = d / "oldtok.zip"
    p.write_bytes(b"old")
    old = time.time() - 50_000
    os.utime(p, (old, old))

    n = cleanup_expired_staged_zips(tmp_path, ttl_sec=3600, now=time.time())
    assert n == 1
    assert not p.exists()


def test_cleanup_expired_keeps_recent_files(tmp_path: Path) -> None:
    from lenses.blueprints_wizard.launch_pack_staging import cleanup_expired_staged_zips, write_staged_zip

    tok = write_staged_zip(tmp_path, "sess-b", b"fresh")
    from lenses.blueprints_wizard.launch_pack_staging import staged_zip_path

    p = staged_zip_path(tmp_path, "sess-b", tok)
    assert p is not None

    n = cleanup_expired_staged_zips(tmp_path, ttl_sec=3600, now=time.time())
    assert n == 0
    assert p.is_file()
