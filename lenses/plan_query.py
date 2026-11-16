"""Parse `/plan` URL query strings (mirrors client `qs` / `setUrl` contract)."""

from __future__ import annotations

from urllib.parse import parse_qs


def parse_plan_query(query_string: str) -> dict[str, str]:
    """
    Parse a query string like ``repo=x&wbs_p=y&id=z&tab=today``.

    Empty values are omitted. Repeated keys use the last value (browser behavior).
    """
    if not query_string:
        return {}
    s = query_string.strip()
    if s.startswith("?"):
        s = s[1:]
    if not s:
        return {}
    parsed = parse_qs(s, keep_blank_values=False)
    out: dict[str, str] = {}
    for k, vals in parsed.items():
        if vals:
            out[k] = vals[-1]
    return out
