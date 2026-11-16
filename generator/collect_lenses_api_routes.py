#!/usr/bin/env python3
"""Extract HTTP API surfaces from ``lenses/serve.py`` for handbook coverage checks.

Parses ``do_GET``, ``do_POST``, and ``do_PUT`` only (not auxiliary ``def`` methods).
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SERVE_DEFAULT = REPO_ROOT / "lenses" / "serve.py"

_METHOD_DEF = re.compile(r"^\s+def\s+do_(GET|POST|PUT)\(", re.MULTILINE)

_REQ_EQ = re.compile(r'\b(?P<var>path|post_path|put_path)\s*==\s*["\'](?P<api>/api[^"\']+)["\']')

_REQ_RSTRICT_EQ = re.compile(
    r'\b(?P<var>path|post_path|put_path)\s*\.\s*rstrip\([^)]*\)\s*==\s*["\'](?P<api>/api[^"\']+)["\']'
)

_REQ_STARTSWITH = re.compile(
    r'\b(?P<var>path|post_path|put_path)\s*\.\s*startswith\s*\(\s*["\'](?P<pre>/api[^"\']+)["\']\s*\)'
)

# POST bodies behind ``post_path.startswith("/api/blueprints/wizard/session/")``, ``endswith("…")`` — keep explicit.
_BLUEPRINT_WIZ_SESSION_POST_TAIL = frozenset(
    {
        "refine",
        "interpret",
        "clarify-suggest",
        "generate-artifacts",
        "artifact-review",
        "artifact-export",
        "artifact-recheck",
        "create-repo",
        "cursor-launch-pack/preview",
        "cursor-launch-pack/export",
    }
)


def _wizard_session_post_specs() -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = [("POST", "/api/blueprints/wizard/session"), ("POST", "/api/blueprints/wizard/telemetry")]
    for tail in sorted(_BLUEPRINT_WIZ_SESSION_POST_TAIL):
        out.append(("POST", f"/api/blueprints/wizard/session/<id>/{tail}"))
    return out


def _partition_do_methods(py: str) -> list[tuple[str, str]]:
    matches = [(m.start(), m.end(), m.group(1)) for m in _METHOD_DEF.finditer(py)]
    out: list[tuple[str, str]] = []
    for i, (start, _, name) in enumerate(matches):
        end = matches[i + 1][0] if i + 1 < len(matches) else len(py)
        out.append((name, py[start:end]))
    return out


def _var_for_method(method: str) -> str:
    return {"GET": "path", "POST": "post_path", "PUT": "put_path"}[method]


def collect_api_route_signatures(serve_py: Path | None = None) -> list["ApiRouteSig"]:
    text = (serve_py or SERVE_DEFAULT).read_text(encoding="utf-8")
    flat: dict[tuple[str, str], None] = {}

    def add(method: str, sig: str) -> None:
        flat[(method.upper(), sig)] = None

    for verb, chunk in _partition_do_methods(text):
        var = _var_for_method(verb)
        for m in _REQ_EQ.finditer(chunk):
            if m.group("var") != var:
                continue
            add(verb, m.group("api"))
        for m in _REQ_RSTRICT_EQ.finditer(chunk):
            if m.group("var") != var:
                continue
            add(verb, m.group("api"))
        seen_pf: set[str] = set()
        for m in _REQ_STARTSWITH.finditer(chunk):
            if m.group("var") != var:
                continue
            pre = m.group("pre").rstrip("/")
            if pre in seen_pf:
                continue
            seen_pf.add(pre)
            add(verb, f"PREFIX:{pre}")

    for method, sig in _wizard_session_post_specs():
        add(method, sig)

    specs = sorted(
        (ApiRouteSig(m, s) for (m, s) in flat),
        key=lambda x: (x.method, x.signature),
    )
    return specs


@dataclass(frozen=True)
class ApiRouteSig:
    method: str
    signature: str

    def sort_key(self) -> tuple[str, str]:
        return (self.method, self.signature)


def documented_in_md(sig: ApiRouteSig, md_text: str) -> bool:
    """Match paths and ``PREFIX:/api/foo`` umbrellas heuristically (handbook formatting varies)."""
    compact = "".join(md_text.replace("\\", "/").split())
    lowered = compact.casefold()
    if sig.signature.startswith("PREFIX:"):
        stem = sig.signature[len("PREFIX:") :].rstrip("/")
        checks = (
            "`" + stem + "`",
            stem + "`",
            "`" + stem,
            stem,
            stem + "*",
        )
        return any(c.casefold() in lowered for c in checks)
    path_clean = "".join(sig.signature.split())
    if "`" + path_clean + "`" in compact:
        return True
    if "`" + path_clean + "`".casefold() in lowered:
        return True
    return path_clean.casefold() in lowered


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional JSON path (writes method + signature list)",
    )
    args = parser.parse_args()
    rows = [{"method": s.method, "signature": s.signature} for s in collect_api_route_signatures()]
    text = json.dumps(rows, indent=2)
    if args.output:
        args.output.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
