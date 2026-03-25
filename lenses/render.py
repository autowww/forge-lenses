"""HTML rendering for dynamic lenses dashboard (stdlib only)."""

from __future__ import annotations

import html
import urllib.parse
from typing import Any


def esc(s: str) -> str:
    return html.escape(s, quote=True)


def nav_bar(
    active: str,
    handbook_url: str,
    forge_url: str,
) -> str:
    items = [
        ("overview", "/", "Overview"),
        ("projects", "/projects", "Projects"),
        ("toolset", "/toolset", "Toolset"),
        ("websites", "/websites", "Websites"),
        ("wbs", "/wbs", "WBS"),
    ]
    links = []
    for key, href, label in items:
        cls = " active" if active == key else ""
        links.append(
            f'<a class="lenses-nav-link{cls}" href="{esc(href)}">{esc(label)}</a>'
        )
    links.append(
        f'<a class="lenses-nav-link lenses-nav-docs" href="/docs/index.html">Docs</a>'
    )
    links.append(
        f'<a class="lenses-nav-link lenses-nav-external" href="{esc(handbook_url)}" target="_blank" rel="noopener">Handbook</a>'
    )
    links.append(
        f'<a class="lenses-nav-link lenses-nav-external" href="{esc(forge_url)}" target="_blank" rel="noopener">Forge</a>'
    )
    inner = "\n    ".join(links)
    return f"""<header class="lenses-topbar">
  <div class="lenses-brand"><a href="/">lenses</a></div>
  <nav class="lenses-nav" aria-label="Main">
    {inner}
  </nav>
</header>"""


def layout_page(title: str, nav_active: str, body: str, handbook_url: str, forge_url: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{esc(title)} — lenses</title>
  <style>
    :root {{
      --bg: #0a0e17;
      --text: #e8ecf4;
      --muted: #94a3b8;
      --accent: #06b6d4;
      --border: #1e293b;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: system-ui, sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.5;
      min-height: 100vh;
    }}
    .lenses-topbar {{
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 0.75rem 1rem;
      padding: 0.65rem 1.25rem;
      border-bottom: 1px solid var(--border);
      background: #0d121c;
      position: sticky;
      top: 0;
      z-index: 100;
    }}
    .lenses-brand a {{
      font-weight: 700;
      color: var(--accent);
      text-decoration: none;
      letter-spacing: 0.02em;
    }}
    .lenses-nav {{
      display: flex;
      flex-wrap: wrap;
      gap: 0.35rem 0.75rem;
      align-items: center;
    }}
    .lenses-nav-link {{
      color: var(--muted);
      text-decoration: none;
      font-size: 0.9rem;
      padding: 0.2rem 0.35rem;
      border-radius: 4px;
    }}
    .lenses-nav-link:hover {{ color: var(--text); }}
    .lenses-nav-link.active {{ color: var(--accent); font-weight: 600; }}
    .lenses-nav-docs {{ color: #f59e0b; }}
    .lenses-nav-external {{ opacity: 0.9; }}
    main {{
      max-width: 56rem;
      margin: 0 auto;
      padding: 1.5rem 1.25rem 3rem;
    }}
    h1 {{ font-size: 1.5rem; margin-top: 0; }}
    h2 {{ font-size: 1.1rem; margin-top: 1.75rem; color: var(--accent); }}
    table {{ width: 100%; border-collapse: collapse; font-size: 0.88rem; }}
    th, td {{ text-align: left; padding: 0.45rem 0.6rem; border-bottom: 1px solid var(--border); }}
    th {{ color: var(--muted); font-weight: 600; }}
    code {{ font-size: 0.85em; background: #111827; padding: 0.1rem 0.35rem; border-radius: 3px; }}
    .meta {{ color: var(--muted); font-size: 0.85rem; margin-bottom: 1rem; }}
    .pill {{ display: inline-block; padding: 0.15rem 0.45rem; border-radius: 999px; font-size: 0.75rem; background: #1e293b; }}
    .pill.dirty {{ background: #422006; color: #fdba74; }}
    .pill.clean {{ color: #86efac; }}
  </style>
</head>
<body>
{nav_bar(nav_active, handbook_url, forge_url)}
<main>
{body}
</main>
</body>
</html>"""


def page_overview(
    state: dict[str, Any], handbook_url: str, forge_url: str
) -> str:
    n_children = len(state.get("children") or [])
    n_wbs = len(state.get("wbs") or [])
    n_sites = len(state.get("websites") or [])
    scripts = state.get("toolset") or {}
    n_scripts = len(scripts.get("root_scripts") or [])
    body = f"""<h1>Overview</h1>
<p class="meta">Workspace: <code>{esc(str(state.get("workspace_root", "")))}</code><br />
Resolved: <code>{esc(str(state.get("resolved_at", "")))}</code></p>
<ul>
  <li><strong>{n_children}</strong> top-level directories scanned</li>
  <li><strong>{n_sites}</strong> Firebase site repos detected</li>
  <li><strong>{n_wbs}</strong> WBS file(s) under <code>docs/requirements/</code></li>
  <li><strong>{n_scripts}</strong> shell script(s) at workspace root</li>
</ul>
<p class="meta">Reload any page to refresh discovery (no server-side cache).</p>"""
    return layout_page("Overview", "overview", body, handbook_url, forge_url)


def page_projects(state: dict[str, Any], handbook_url: str, forge_url: str) -> str:
    rows = []
    for c in state.get("children") or []:
        name = esc(str(c.get("name", "")))
        gi = c.get("git") or {}
        if c.get("is_git"):
            branch = esc(str(gi.get("branch", "")))
            dirty = gi.get("dirty")
            pill = '<span class="pill dirty">dirty</span>' if dirty else '<span class="pill clean">clean</span>'
            origin = esc(str(gi.get("origin_url", "")))
            top = esc(str(gi.get("top_level", "")))
            git_cell = f"{pill} <code>{branch}</code><br /><small>{origin}</small><br /><small>{top}</small>"
        else:
            git_cell = "—"
        rows.append(f"<tr><td><strong>{name}</strong></td><td>{git_cell}</td></tr>")
    table = (
        "<table><thead><tr><th>Directory</th><th>Git</th></tr></thead><tbody>"
        + ("\n".join(rows) if rows else "<tr><td colspan=\"2\">No directories found.</td></tr>")
        + "</tbody></table>"
    )
    body = f"<h1>Projects</h1>\n<p class=\"meta\">Top-level folders under the workspace root.</p>\n{table}"
    return layout_page("Projects", "projects", body, handbook_url, forge_url)


def page_toolset(state: dict[str, Any], handbook_url: str, forge_url: str) -> str:
    ts = state.get("toolset") or {}
    scripts = ts.get("root_scripts") or []
    sl = "\n".join(f"<li><code>{esc(s)}</code></li>" for s in scripts)
    cursor = ts.get("cursor_dir") or ""
    cur_html = f"<p><code>{esc(cursor)}</code></p>" if cursor else "<p class=\"meta\">No <code>.cursor</code> directory at workspace root.</p>"
    body = f"""<h1>Toolset</h1>
<p class="meta">Orchestration scripts and editor config at the workspace root (not nested repo websites).</p>
<h2>Root shell scripts</h2>
<ul>{sl or "<li class=\"meta\">None</li>"}</ul>
<h2>Cursor / IDE</h2>
{cur_html}"""
    return layout_page("Toolset", "toolset", body, handbook_url, forge_url)


def page_websites(state: dict[str, Any], registry: dict[str, Any], handbook_url: str, forge_url: str) -> str:
    labels = registry.get("website_labels") or {}
    rows = []
    for w in state.get("websites") or []:
        name = str(w.get("name", ""))
        label = labels.get(name, "")
        extra = f" — {esc(label)}" if label else ""
        rows.append(
            f"<tr><td><strong>{esc(name)}</strong>{extra}</td>"
            f"<td><code>{esc(str(w.get('firebase_json', '')))}</code></td></tr>"
        )
    note = "<p class=\"meta\">These are repos under your workspace that contain <code>firebase.json</code>. "
    note += "They are not served by lenses; use your normal build and Firebase workflow.</p>"
    table = (
        "<table><thead><tr><th>Repo</th><th>firebase.json</th></tr></thead><tbody>"
        + ("\n".join(rows) if rows else "<tr><td colspan=\"2\">None detected.</td></tr>")
        + "</tbody></table>"
    )
    body = f"<h1>Websites</h1>\n{note}\n{table}"
    return layout_page("Websites", "websites", body, handbook_url, forge_url)


def wbs_view_link(rel_path: str) -> str:
    q = urllib.parse.urlencode({"p": rel_path})
    return f"/wbs/view?{q}"


def page_wbs(state: dict[str, Any], handbook_url: str, forge_url: str) -> str:
    rows = []
    for w in state.get("wbs") or []:
        rp = str(w.get("rel_path", ""))
        kind = esc(str(w.get("kind", "")))
        hint = esc(str(w.get("repo_hint", "")))
        link = wbs_view_link(rp)
        rows.append(
            f"<tr><td><code>{esc(rp)}</code></td><td>{kind}</td><td>{hint}</td>"
            f'<td><a href="{esc(link)}">View</a></td></tr>'
        )
    table = (
        "<table><thead><tr><th>Path</th><th>Kind</th><th>Top folder</th><th></th></tr></thead><tbody>"
        + ("\n".join(rows) if rows else "<tr><td colspan=\"4\">No WBS.md / WBS.csv found.</td></tr>")
        + "</tbody></table>"
    )
    body = (
        f"<h1>WBS</h1>\n<p class=\"meta\">Blueprint-style work breakdown files under "
        f"<code>docs/requirements/</code>.</p>\n{table}"
    )
    return layout_page("WBS", "wbs", body, handbook_url, forge_url)


def page_wbs_view(
    rel_path: str,
    content: str,
    mime_hint: str,
    handbook_url: str,
    forge_url: str,
) -> str:
    if mime_hint == "csv":
        body_inner = f"<pre style=\"overflow:auto;font-size:0.82rem\">{esc(content)}</pre>"
    else:
        body_inner = f"<pre style=\"overflow:auto;white-space:pre-wrap;font-size:0.88rem\">{esc(content)}</pre>"
    body = f"""<h1>WBS file</h1>
<p class="meta"><code>{esc(rel_path)}</code></p>
<p><a href="/wbs">← Back to WBS list</a></p>
{body_inner}"""
    return layout_page("WBS view", "wbs", body, handbook_url, forge_url)


