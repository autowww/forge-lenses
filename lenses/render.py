"""HTML rendering for dynamic lenses dashboard (KS showcase when submodule present)."""

from __future__ import annotations

import html
import json
import re
import urllib.parse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lenses.git_urls import commit_url_for_remote, remote_to_https_repo_url
from lenses.scan import shell_script_comment_detail
from lenses.sticker_board import board_count_for_project
from lenses.tutorial_index import (
    HandbookRef,
    list_child_handbooks,
    repo_tutorials_link_label_from_pages,
    tutorial_link_label_from_pages,
)
from lenses.toolset_actions import resolve_toolset_script
from lenses.feature_showcase_classic import feature_showcase_body_html
from lenses.ks_layout import board_thumb_capture_extra_css, lenses_showcase_page
from lenses.overview_forge import build_overview_forge_rollup
from lenses.plan_workflow_ui import FORGE_PLAN_SCRIPT
from lenses.safe_forge_paths import roadmap_timeline_view_link, workspace_md_view_link
from lenses.timeline_workflow_ui import FORGE_TIMELINE_SCRIPT
from lenses.wbs_management import (
    build_wbs_project_rows,
    resolve_wbs_project_base,
    wbs_md_exists,
)
from lenses.repo_strategy import (
    DEFAULT_MAINTENANCE_BULLETS,
    git_submodule_status_text,
    load_optional_strategy_markdown,
    markdown_to_html_fragment,
    parse_gitmodules,
    remote_default_branch,
    sibling_workspace_hint,
    strategy_registry_entry,
    svg_submodule_layout_svg,
    workspace_child_names,
)
from lenses.roadmap_charts import (
    KS_ROADMAP_TEMPLATE,
    horizon_badges_html,
    ks_diagram_img,
    roadmap_date_shift_html,
    roadmap_gantt_html,
    roadmap_summary_html,
    svg_epic_progress_bars,
)
from lenses.roadmap_outline import (
    extract_chart_metrics,
    extract_date_shift_model,
    extract_gantt_model,
    find_section,
    parse_roadmap_markdown,
    section_to_html,
)
from lenses.standards_compliance import svg_compliance_score_bars
from lenses.project_stats import (
    approx_tracked_lines,
    collect_project_stats,
    commits_by_day_dict,
    extension_heatmap_html,
    git_numstat_since,
    git_recent_commits,
    overview_repo_row_metrics,
    svg_commit_bar_chart,
    svg_commit_daily_bar_chart,
    svg_loc_added_horizontal_bars,
    svg_loc_share_donut,
    svg_repo_total_loc_bars,
    workspace_commits_daily_series,
)


def esc(s: str) -> str:
    return html.escape(s, quote=True)


def _repo_hints_wbs_then_roadmaps(
    wbs_rows: list[dict[str, Any]],
    rms: list[dict[str, Any]],
) -> list[str]:
    """Distinct repo_hint values: preserve WBS iteration order, then add roadmap-only repos."""
    seen: set[str] = set()
    out: list[str] = []
    for row in wbs_rows:
        h = str(row.get("repo_hint", "")).strip()
        if h and h not in seen:
            seen.add(h)
            out.append(h)
    for row in rms:
        h = str(row.get("repo_hint", "")).strip()
        if h and h not in seen:
            seen.add(h)
            out.append(h)
    return out


def _project_standards_compliance_html(
    sid: str,
    sc_data: dict[str, Any],
    handbook_url: str,
) -> str:
    """Single project dashboard section for heuristic agentic / standards compliance."""
    score = int(sc_data.get("score") or 0)
    tier = str(sc_data.get("tier") or "minimal")
    summary = str(sc_data.get("summary") or "")
    checks = sc_data.get("checks") or []
    if not isinstance(checks, list):
        checks = []
    tier_badge = (
        "text-bg-success"
        if tier == "good"
        else ("text-bg-warning" if tier == "partial" else "text-bg-secondary")
    )
    hb = handbook_url.rstrip("/")
    bp_link = f'{hb}/sdlc--methodologies-agentic-coding-standards.html'
    rows: list[str] = []
    modals: list[str] = []
    for c in checks:
        if not isinstance(c, dict):
            continue
        cid = str(c.get("id", "")).strip() or "check"
        lbl = str(c.get("label", ""))
        st = str(c.get("status", ""))
        icon = "✓" if st == "pass" else ("◌" if st in ("na", "skipped") else "!")
        row_cls = ""
        if st == "warn":
            row_cls = ' class="table-warning"'
        elif st in ("na", "skipped"):
            row_cls = ' class="table-secondary"'
        modal_id = f"lenses-std-modal-{sid}-{cid}"
        modal_title_id = f"lenses-std-modal-title-{sid}-{cid}"
        pre_id = f"lenses-std-pre-{sid}-{cid}"
        rationale = str(c.get("rationale", "") or "")
        fix_prompt = str(c.get("cursor_fix_prompt", "") or "")
        detail = str(c.get("detail", "") or "")
        st_badge = (
            "text-bg-success"
            if st == "pass"
            else ("text-bg-secondary" if st in ("na", "skipped") else "text-bg-warning")
        )
        prompt_block = (
            f'<pre class="lenses-std-guidance-pre mb-2" id="{esc(pre_id)}"><code>{esc(fix_prompt)}</code></pre>'
            f'<button type="button" class="btn btn-sm btn-outline-secondary lenses-std-copy-btn" '
            f'data-lenses-copy="#{pre_id}">Copy prompt</button>'
            if fix_prompt.strip()
            else '<p class="small text-secondary mb-0">No copy-paste prompt for this status — use the scan detail and blueprint link above.</p>'
        )
        modals.append(
            f'<div class="modal fade" id="{esc(modal_id)}" tabindex="-1" '
            f'aria-labelledby="{esc(modal_title_id)}" aria-hidden="true">'
            '<div class="modal-dialog modal-lg modal-dialog-scrollable">'
            '<div class="modal-content" style="background:var(--forge-bg,#0f172a);color:var(--bs-body-color,#e2e8f0);border-color:var(--forge-border,#1e293b)">'
            '<div class="modal-header border-secondary">'
            f'<h5 class="modal-title" id="{esc(modal_title_id)}">'
            f"{esc(lbl)} "
            f'<span class="badge {st_badge}">{esc(st)}</span></h5>'
            '<button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" '
            'aria-label="Close"></button>'
            "</div>"
            '<div class="modal-body">'
            f'<p class="small text-secondary mb-2"><strong>Scan</strong>: {esc(detail)}</p>'
            f'<p class="small mb-3">{esc(rationale)}</p>'
            '<h6 class="h6 text-cyan mb-2">Try in Cursor</h6>'
            f"{prompt_block}"
            "</div></div></div></div>"
        )
        rows.append(
            f"<tr{row_cls}>"
            f"<td>{esc(icon)}</td>"
            f"<td>{esc(lbl)}</td>"
            f'<td class="small">{esc(detail)}</td>'
            f'<td class="text-nowrap">'
            f'<button type="button" class="btn btn-sm btn-outline-info" '
            f'data-bs-toggle="modal" data-bs-target="#{esc(modal_id)}" '
            f'aria-label="Why this check matters and Cursor prompt for {esc(lbl)}">'
            "Why &amp; fix</button>"
            f"</td>"
            f"</tr>"
        )
    tbl = (
        '<table class="table table-sm table-bordered mb-2">'
        '<thead><tr><th scope="col"></th><th scope="col">Check</th><th scope="col">Detail</th>'
        '<th scope="col">Guide</th></tr></thead>'
        f"<tbody>{''.join(rows)}</tbody></table>"
        if rows
        else '<p class="forge-support small mb-2">No checks available.</p>'
    )
    sugg = sc_data.get("suggestions") or []
    sugg_html = ""
    if isinstance(sugg, list) and sugg:
        items = "".join(f"<li>{esc(str(x))}</li>" for x in sugg if str(x).strip())
        sugg_html = (
            f'<p class="small fw-semibold mb-1">Suggestions</p><ul class="small mb-0">{items}</ul>'
        )
    copy_script = f"""<script>
(function() {{
  var root = document.getElementById('lenses-proj-std-wrap-{esc(sid)}');
  if (!root) return;
  root.querySelectorAll('.lenses-std-copy-btn').forEach(function(btn) {{
    btn.addEventListener('click', function() {{
      var sel = btn.getAttribute('data-lenses-copy');
      var el = sel ? document.querySelector(sel) : null;
      var text = el ? (el.textContent || '') : '';
      function done() {{
        var t = btn.textContent;
        btn.textContent = 'Copied';
        setTimeout(function() {{ btn.textContent = t; }}, 1600);
      }}
      if (navigator.clipboard && navigator.clipboard.writeText) {{
        navigator.clipboard.writeText(text).then(done).catch(function() {{
          var ta = document.createElement('textarea');
          ta.value = text;
          document.body.appendChild(ta);
          ta.select();
          try {{ document.execCommand('copy'); }} catch (e) {{}}
          document.body.removeChild(ta);
          done();
        }});
      }} else {{
        var ta = document.createElement('textarea');
        ta.value = text;
        document.body.appendChild(ta);
        ta.select();
        try {{ document.execCommand('copy'); }} catch (e) {{}}
        document.body.removeChild(ta);
        done();
      }}
    }});
  }});
}})();
</script>"""
    std_style = (
        "<style>"
        ".lenses-std-guidance-pre { max-height: 14rem; overflow: auto; font-size: 0.8rem; "
        "white-space: pre-wrap; word-break: break-word; "
        "background: var(--bs-body-bg, #0f172a); border: 1px solid var(--forge-border, #1e293b); "
        "border-radius: 6px; padding: 0.75rem; }"
        "</style>"
    )
    return (
        f'<section class="lenses-site-hero-section forge-card" '
        f'id="lenses-proj-std-wrap-{esc(sid)}" '
        f'aria-labelledby="lenses-proj-std-{esc(sid)}">'
        f"{std_style}"
        f'<h3 class="h6 text-cyan mb-2" id="lenses-proj-std-{esc(sid)}">'
        f"Standards and agentic hygiene</h3>"
        f'<p class="forge-support small mb-2">'
        f'<span class="badge rounded-pill {tier_badge} me-2">{esc(tier)} · {score}/100</span>'
        f"{esc(summary)} "
        f'<a href="{esc(bp_link)}" target="_blank" rel="noopener">Blueprint: agentic coding standards</a>.'
        f"</p>"
        f"{tbl}"
        f"{''.join(modals)}"
        f"{copy_script}"
        f"{sugg_html}"
        f"</section>"
    )


# Same path as kitchensink ``LANDING_FORGE_SPECTRAL_SVG`` — static sites resolve it
# under site root; Lenses only serves that file under ``/__ks/``.
_LENSES_HERO_SPECTRAL_REL = (
    "assets/svg/backgrounds/sinusoids/bg-fourier-forge-spectral-animated-01.svg"
)


def _rewrite_lenses_hero_spectral_img_src(html: str) -> str:
    """Rewrite hero ``img`` src so it loads from ``/__ks/`` on the Lenses server."""
    rel = _LENSES_HERO_SPECTRAL_REL.replace("\\", "/")
    needle = f'src="{rel}"'
    if needle not in html:
        return html
    return html.replace(needle, f'src="/__ks/{rel}"', 1)


def _lenses_vertical_hero_styles() -> str:
    """Shared CSS for websites stacked heroes and project dashboard panels."""
    return """<style>
.lenses-sites-stack { display: flex; flex-direction: column; gap: 0; }
.lenses-site-hero-section {
  border-left: 3px solid rgba(6, 182, 212, 0.35);
  background: linear-gradient(105deg, rgba(6, 182, 212, 0.03) 0%, transparent 50%);
  border-radius: 10px;
  padding: 1.25rem 1.35rem;
  margin-bottom: 1.5rem;
  transition: border-color 0.18s ease, background 0.18s ease, box-shadow 0.18s ease;
}
.lenses-site-card.lenses-site-hero-section {
  border-left-width: 3px;
  border-left-color: rgba(6, 182, 212, 0.32);
  background: linear-gradient(105deg, rgba(6, 182, 212, 0.025) 0%, transparent 58%);
}
.lenses-site-card.lenses-site-hero-section:hover,
.lenses-site-card.lenses-site-hero-section:focus-within {
  border-left-color: var(--bs-cyan, #06b6d4);
  background: linear-gradient(105deg, rgba(6, 182, 212, 0.07) 0%, transparent 52%);
  box-shadow: 0 0 0 1px rgba(6, 182, 212, 0.12);
}
.lenses-site-hero-section .lenses-hero-kicker {
  font-size: 0.72rem;
  letter-spacing: 0.07em;
  text-transform: uppercase;
  color: var(--forge-text-4, #64748b);
  font-weight: 600;
}
.lenses-site-hero-section h2 { font-size: 1.35rem; margin: 0.35rem 0 0.25rem; }
.lenses-site-card .lenses-site-title {
  font-size: clamp(1.5rem, 2.8vw, 2rem);
  font-weight: 700;
  letter-spacing: -0.03em;
  margin: 0.35rem 0 0.4rem;
  line-height: 1.15;
}
.lenses-site-status-chips .badge { font-weight: 500; max-width: 100%; }
.lenses-site-branch-chip {
  max-width: min(100%, 18rem);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.lenses-site-summary {
  font-size: 0.88rem;
  color: var(--forge-text-4, #94a3b8);
  margin: 0 0 0.25rem;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.lenses-site-cta-col .btn-forge { font-weight: 600; }
.lenses-site-meta-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 0.65rem 1rem;
  margin-top: 1.05rem;
  padding-top: 1rem;
  border-top: 1px solid rgba(148, 163, 184, 0.18);
}
@media (min-width: 576px) {
  .lenses-site-meta-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (min-width: 992px) {
  .lenses-site-meta-grid { grid-template-columns: repeat(4, minmax(0, 1fr)); }
}
.lenses-site-meta-k {
  font-size: 0.65rem;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--forge-text-4, #64748b);
  font-weight: 600;
  margin-bottom: 0.2rem;
}
.lenses-site-meta-v {
  font-size: 0.82rem;
  color: var(--bs-body-color, var(--forge-text, #e2e8f0));
  word-break: break-word;
  min-width: 0;
}
.lenses-site-meta-v code { font-size: 0.78rem; }
.lenses-site-meta-muted { color: var(--forge-text-4, #64748b); font-size: 0.8rem; }
.lenses-site-meta-truncate {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.lenses-index-health { display: flex; flex-direction: column; gap: 0.25rem; }
.lenses-index-progress { height: 4px; background: rgba(148, 163, 184, 0.2); }
.lenses-index-progress .progress-bar { min-width: 0; }
.lenses-index-health-label { line-height: 1.2; }
.lenses-site-stat-strip { display: flex; flex-wrap: wrap; gap: 0.45rem; margin: 0.85rem 0 0.25rem; align-items: center; }
.lenses-site-stat-strip .badge { font-weight: 500; }
.lenses-site-card .lenses-site-details { margin-top: 0.65rem; }
.lenses-site-card .lenses-site-details summary {
  cursor: pointer;
  color: var(--bs-cyan, #06b6d4);
  font-weight: 500;
}
.lenses-site-card .lenses-site-details summary:focus-visible {
  outline: 2px solid var(--bs-cyan, #06b6d4);
  outline-offset: 2px;
  border-radius: 2px;
}
.lenses-site-pages-block { margin-top: 1rem; }
.lenses-site-pages-block > .lenses-pages-heading {
  font-size: 0.7rem;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--forge-text-4, #64748b);
  font-weight: 600;
  margin-bottom: 0.35rem;
}
.lenses-key-pages-preview {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(10.5rem, 1fr));
  gap: 0.5rem 0.85rem;
  margin-top: 0.2rem;
}
.lenses-key-pages-preview .lenses-key-page-link {
  font-size: 0.82rem;
  font-weight: 500;
  line-height: 1.3;
}
.lenses-key-pages-preview .lenses-key-page-path {
  font-size: 0.68rem;
  opacity: 0.9;
}
.lenses-key-pages-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(14rem, 1fr));
  gap: 0.65rem 1.15rem;
  margin: 0.5rem 0 0;
}
.lenses-key-pages-grid .lenses-key-page-link {
  font-size: 0.9rem;
  text-decoration: none;
  color: var(--bs-body-color, var(--forge-text, #e2e8f0));
}
.lenses-key-pages-grid .lenses-key-page-link:hover {
  color: var(--bs-cyan, #06b6d4);
  text-decoration: none;
}
.lenses-key-page-path { font-size: 0.72rem; }
.lenses-site-hero-section.lenses-project-portal-section {
  min-height: 12rem;
  padding-top: 1.5rem;
  padding-bottom: 1.65rem;
}
.lenses-project-whats-here-grid {
  display: grid;
  gap: 0.75rem 1.25rem;
  grid-template-columns: 1fr;
}
@media (min-width: 576px) {
  .lenses-project-whats-here-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
.lenses-project-whats-here-k {
  font-weight: 600;
  letter-spacing: 0.04em;
}
.lenses-project-cta-groups {
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
}
.lenses-project-cta-group {
  padding-left: 0.65rem;
  border-left: 3px solid rgba(148, 163, 184, 0.35);
}
.lenses-project-cta-group-label {
  display: block;
  font-size: 0.65rem;
  letter-spacing: 0.06em;
  color: var(--forge-text-4, #64748b);
  font-weight: 600;
  margin-bottom: 0.35rem;
}
.lenses-portal-preview-wrap {
  display: inline-block;
  margin-top: 0.15rem;
}
a.lenses-portal-preview-trigger.fs-topic-preview-card {
  display: inline-flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.15rem;
  margin-top: 0;
  padding: 0.4rem 0.85rem;
  border: 1px solid rgba(148, 163, 184, 0.45);
  border-radius: 0.375rem;
  background: transparent;
  text-decoration: none;
  max-width: min(100%, 22rem);
}
a.lenses-portal-preview-trigger.fs-topic-preview-card:hover {
  border-color: var(--bs-cyan, #06b6d4);
}
a.lenses-portal-preview-trigger .fs-topic-preview-card__eyebrow {
  display: none;
}
a.lenses-portal-preview-trigger .fs-topic-preview-card__title {
  font-size: 0.95rem;
  font-weight: 600;
  line-height: 1.25;
}
a.lenses-portal-preview-trigger .fs-topic-preview-card__desc {
  display: none;
}
a.lenses-portal-preview-trigger .fs-topic-preview-card__hint {
  font-size: 0.72rem;
  opacity: 0.85;
}
</style>"""


def _child_by_name(state: dict[str, Any], name: str) -> dict[str, Any] | None:
    for c in state.get("children") or []:
        if str(c.get("name", "")) == name:
            return c if isinstance(c, dict) else None
    return None


def _website_by_name(state: dict[str, Any], name: str) -> dict[str, Any] | None:
    for w in state.get("websites") or []:
        if str(w.get("name", "")) == name:
            return w if isinstance(w, dict) else None
    return None


def local_site_href(site: str, rel_path: str) -> str:
    rel_path = (rel_path or "").strip().replace("\\", "/").lstrip("/")
    segs = [urllib.parse.quote(s, safe="") for s in rel_path.split("/") if s]
    tail = "/".join(segs) if segs else urllib.parse.quote("index.html", safe="")
    return f"/local-site/{urllib.parse.quote(site, safe='')}/{tail}"


def view_lenses_docs_href(rel_path: str = "") -> str:
    """Dashboard URL that keeps Lenses chrome while showing ``/docs/…`` in an iframe."""
    rel = (rel_path or "").strip().replace("\\", "/").lstrip("/")
    if not rel:
        return "/view/docs"
    segs = [urllib.parse.quote(s, safe="") for s in rel.split("/") if s]
    return "/view/docs/" + "/".join(segs)


def view_local_site_href(site: str, rel_path: str) -> str:
    """Dashboard URL that keeps Lenses chrome while showing ``/local-site/…`` in an iframe."""
    return "/view" + local_site_href(site, rel_path)


def embed_in_app_doc_url(url: str) -> str:
    """Rewrite same-origin ``/docs`` and ``/local-site`` paths to ``/view/…`` shell routes."""
    u = (url or "").strip()
    if not u:
        return u
    parsed = urllib.parse.urlparse(u)
    path = parsed.path
    new_path: str | None = None
    if path == "/docs" or path.startswith("/docs/"):
        tail = path[len("/docs") :].lstrip("/")
        new_path = "/view/docs" + ("/" + tail if tail else "")
    elif path.startswith("/local-site/"):
        new_path = "/view" + path
    if new_path is None:
        return u
    return urllib.parse.urlunparse(
        (parsed.scheme, parsed.netloc, new_path, parsed.params, parsed.query, parsed.fragment)
    )


def page_view_embed(
    state: dict[str, Any],
    *,
    iframe_src: str,
    raw_open_href: str,
    page_title: str,
    breadcrumb_parts: list[tuple[str, str]],
    lenses_repo_root: Path,
    handbook_url: str,
    forge_url: str,
    missing_message: str | None = None,
) -> str:
    """Full dashboard page with iframe to static handbook, or in-shell message when missing."""
    if missing_message:
        body_inner = (
            f'<div class="alert alert-warning border-secondary" role="status">'
            f"<p class=\"mb-2\">{esc(missing_message)}</p>"
            '<p class="mb-0 forge-support small">'
            '<a href="/">Overview</a> · '
            f'<a href="{esc(view_lenses_docs_href())}">Lenses reference</a> · '
            '<a href="/tutorials">Tutorials</a>'
            "</p></div>"
        )
    else:
        _embed_sandbox = (
            "allow-scripts allow-same-origin allow-forms "
            "allow-popups allow-popups-to-escape-sandbox allow-modals allow-downloads"
        )
        initial_src_js = json.dumps(iframe_src)
        body_inner = f"""
<style>
.lenses-view-embed-root {{ display: flex; flex-direction: column; min-height: calc(100vh - 10rem); }}
.lenses-view-embed-toolbar {{
  flex: 0 0 auto; display: flex; flex-wrap: wrap; gap: 0.5rem; align-items: center;
  margin-bottom: 0.75rem;
}}
.lenses-view-embed-frame-wrap {{
  flex: 1 1 auto; min-width: 0; min-height: 480px; border: 1px solid var(--forge-border, #1e293b);
  border-radius: 8px; overflow: hidden; background: #020617;
}}
.lenses-view-embed-frame-wrap iframe {{
  width: 100%; height: 100%; min-height: 480px; border: 0; display: block;
}}
</style>
<div class="lenses-view-embed-root">
  <div class="lenses-view-embed-toolbar forge-support">
    <button type="button" class="btn btn-sm btn-outline-secondary" id="lenses-embed-iframe-back"
      title="Go back one step inside the embedded page" aria-label="Back inside embedded preview">← In preview</button>
    <button type="button" class="btn btn-sm btn-outline-secondary" id="lenses-embed-iframe-reset"
      title="Reload the starting URL for this view" aria-label="Reset embedded preview">Reset preview</button>
    <button type="button" class="btn btn-sm btn-outline-secondary" id="lenses-embed-iframe-reload"
      title="Reload the current embedded page" aria-label="Reload embedded preview">Reload</button>
    <a href="/" class="btn btn-sm btn-outline-secondary">Overview</a>
    <a href="{esc(view_lenses_docs_href())}" class="btn btn-sm btn-outline-secondary">Lenses reference</a>
    <a href="{esc(raw_open_href)}" target="_blank" rel="noopener" class="btn btn-sm btn-outline-info">Open without shell</a>
  </div>
  <div class="lenses-view-embed-frame-wrap">
    <iframe id="lenses-view-embed-frame" title="{esc(page_title)}" src="{esc(iframe_src)}"
      sandbox="{esc(_embed_sandbox)}"></iframe>
  </div>
</div>
<script>
(function () {{
  var frame = document.getElementById("lenses-view-embed-frame");
  var initialSrc = {initial_src_js};
  if (!frame) return;
  function back() {{
    try {{ frame.contentWindow.history.back(); }} catch (e) {{}}
  }}
  function reset() {{ frame.src = initialSrc; }}
  function reload() {{
    try {{ frame.contentWindow.location.reload(); }} catch (e) {{ frame.src = frame.src; }}
  }}
  var b1 = document.getElementById("lenses-embed-iframe-back");
  var b2 = document.getElementById("lenses-embed-iframe-reset");
  var b3 = document.getElementById("lenses-embed-iframe-reload");
  if (b1) b1.addEventListener("click", back);
  if (b2) b2.addEventListener("click", reset);
  if (b3) b3.addEventListener("click", reload);
}})();
</script>
"""
    bc = lenses_breadcrumb_html(*breadcrumb_parts)
    return _wrap_dashboard(
        lenses_repo_root,
        browser_title=f"{page_title} — lenses",
        nav_active="overview",
        page_title=page_title,
        breadcrumb_html=bc,
        body_inner=body_inner,
        handbook_url=handbook_url,
        forge_url=forge_url,
        workspace_projects=workspace_project_names_sorted(state),
        current_project=None,
    )


def _handbook_display_label(book: HandbookRef, pages: Any, is_site: bool) -> str:
    if not is_site:
        return book.label_default
    if book.kind == "tutorial":
        return tutorial_link_label_from_pages(pages)
    return repo_tutorials_link_label_from_pages(pages)


def _fmt_mtime(ts: object) -> str:
    if ts is None:
        return "—"
    try:
        t = float(ts)
    except (TypeError, ValueError):
        return "—"
    return datetime.fromtimestamp(t).strftime("%Y-%m-%d %H:%M")


def _parse_git_iso_datetime(s: str) -> datetime | None:
    raw = (s or "").strip()
    if not raw:
        return None
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _relative_time_short(dt: datetime) -> str:
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    secs = int((now - dt).total_seconds())
    if secs < 0:
        return "just now"
    if secs < 60:
        return f"{secs}s ago"
    mins = secs // 60
    if mins < 60:
        return f"{mins}m ago"
    hrs = mins // 60
    if hrs < 48:
        return f"{hrs}h ago"
    days = hrs // 24
    if days < 14:
        return f"{days}d ago"
    return dt.strftime("%Y-%m-%d")


def _portal_last_update_label(gi: dict[str, Any]) -> str:
    cu = gi.get("commit_unix")
    if isinstance(cu, int) and cu > 0:
        dt = datetime.fromtimestamp(cu, tz=timezone.utc)
        return _relative_time_short(dt)
    dt = _parse_git_iso_datetime(str(gi.get("commit_date", "")))
    if dt is not None:
        return _relative_time_short(dt)
    return "—"


def _portal_first_sentence(text: str, max_len: int = 140) -> str:
    t = " ".join((text or "").split())
    if not t:
        return ""
    for sep in ".!?":
        i = t.find(sep)
        if 12 < i < max_len + 40:
            return t[: i + 1]
    return _truncate_plain(t, max_len)


def _prefetch_portal_repo_metrics(
    rows: list[dict[str, Any]],
) -> dict[str, tuple[int | None, tuple[int, int]]]:
    """Per-repo approx LoC and 7d numstat for the projects portal (parallel)."""
    out: dict[str, tuple[int | None, tuple[int, int]]] = {}

    def job(c: dict[str, Any]) -> tuple[str, int | None, tuple[int, int]]:
        name = str(c.get("name", ""))
        path = Path(str(c.get("path", "")))
        if not c.get("is_git"):
            return name, None, (0, 0)
        loc = approx_tracked_lines(path)
        add_d, del_d = git_numstat_since(path, 7)
        return name, loc, (add_d, del_d)

    if not rows:
        return out
    max_workers = min(12, max(1, len(rows)))
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        for name, loc, nd in pool.map(job, rows):
            out[name] = (loc, nd)
    return out


def _project_portal_panel_html(
    *,
    name: str,
    path: Path,
    c: dict[str, Any],
    website_names: set[str],
    website_labels: dict[str, Any],
    project_urls: dict[str, Any],
    project_summaries: dict[str, Any],
    wbs_count: int,
    card_href: str,
    loc: int | None,
    numstat: tuple[int, int],
    ks_preview: bool,
) -> str:
    gi = c.get("git") or {}
    is_git = bool(c.get("is_git"))
    origin = str(gi.get("origin_url", ""))
    head_full = str(gi.get("head_full", ""))
    commit_url = commit_url_for_remote(origin, head_full) if head_full else ""
    sid = re.sub(r"[^a-z0-9_-]+", "-", name.lower()).strip("-") or "proj"

    if name in website_names:
        wl = str(website_labels.get(name, "") or "").strip()
        kicker = wl if wl else "Firebase hosting site"
    else:
        kicker = "Project"

    reg_sum = (
        str(project_summaries.get(name, "")).strip()
        if isinstance(project_summaries, dict)
        else ""
    )
    if reg_sum:
        blurb = reg_sum
    else:
        blurb = _readme_excerpt(path, max_len=360) if path.is_dir() else ""
    blurb_html = (
        f'<p class="forge-support small mb-0 mt-2">{esc(blurb)}</p>' if blurb else ""
    )

    role_bits: list[str] = []
    if name in website_names:
        role_bits.append(
            '<span class="badge rounded-pill text-bg-info">Firebase site</span>'
        )
    pub = str(project_urls.get(name, "")).strip()
    if pub:
        role_bits.append(
            f'<a class="badge rounded-pill text-bg-warning text-decoration-none" '
            f'href="{esc(pub)}" target="_blank" rel="noopener">Published site</a>'
        )
    if wbs_count > 0:
        role_bits.append(
            f'<a class="badge rounded-pill text-bg-dark border border-secondary text-decoration-none" '
            f'href="/wbs">WBS · {wbs_count} file{"s" if wbs_count != 1 else ""}</a>'
        )
    role_row = (
        f'<div class="d-flex flex-wrap gap-1 mb-1">{"".join(role_bits)}</div>'
        if role_bits
        else ""
    )

    stat_bits: list[str] = []
    if is_git and loc is not None:
        stat_bits.append(
            f'<span class="badge rounded-pill text-bg-dark border border-secondary">'
            f"~{loc:,} lines (approx.)</span>"
        )
    if is_git:
        stat_bits.append(
            f'<span class="badge rounded-pill text-bg-dark border border-secondary">'
            f"updated {_portal_last_update_label(gi)}</span>"
        )
    add_d, del_d = numstat
    if is_git and (add_d or del_d):
        stat_bits.append(
            f'<span class="badge rounded-pill text-bg-dark border border-secondary">'
            f"+{add_d:,} / −{del_d:,} lines (7d)</span>"
        )
    stat_strip = (
        f'<div class="lenses-site-stat-strip">{"".join(stat_bits)}</div>'
        if stat_bits
        else ""
    )

    dirty_note = ""
    if is_git and gi.get("dirty"):
        dirty_note = (
            '<p class="forge-support small mb-0 mt-2 text-warning-emphasis">'
            "Uncommitted changes in the working tree.</p>"
        )

    subj = str(gi.get("commit_subject", "")).strip()
    if len(subj) > 160:
        subj = subj[:157].rstrip() + "…"
    commit_link = ""
    if commit_url:
        commit_link = (
            f' <a href="{esc(commit_url)}" target="_blank" rel="noopener">Open commit</a>'
        )
    last_line = ""
    if is_git and subj:
        last_line = (
            f'<p class="forge-support small mb-0 mt-2"><strong>Last change</strong> '
            f"{esc(subj)}{commit_link}</p>"
        )
    elif is_git:
        last_line = (
            f'<p class="forge-support small mb-0 mt-2">{commit_link.strip()}</p>'
            if commit_link
            else ""
        )

    preview_desc = _portal_first_sentence(blurb) or f"Open {name} dashboard"
    preview_block = ""
    if ks_preview:
        try:
            from components import render_topic_preview_trigger  # noqa: WPS433

            raw_prev = render_topic_preview_trigger(
                href=card_href,
                title=name,
                description=preview_desc,
                eyebrow="Project",
            )
            preview_block = raw_prev.replace(
                'class="fs-topic-preview-card"',
                'class="fs-topic-preview-card lenses-portal-preview-trigger"',
                1,
            )
            preview_block = (
                f'<div class="lenses-portal-preview-wrap">{preview_block}</div>'
            )
        except ImportError:
            preview_block = ""

    strategy_href = f"/projects/{urllib.parse.quote(name, safe='')}/strategy"
    actions = (
        f'<div class="d-flex flex-wrap gap-2 align-items-start mt-3">'
        f'<a class="btn btn-sm btn-forge" href="{esc(card_href)}">Open dashboard</a>'
        f'<a class="btn btn-sm btn-outline-secondary" href="{esc(strategy_href)}">'
        f"Repo &amp; strategy</a>"
        f"{preview_block}"
        f"</div>"
    )

    return (
        f'<section class="lenses-site-hero-section lenses-project-portal-section forge-card" '
        f'id="lenses-portal-{esc(sid)}" aria-labelledby="lenses-portal-title-{esc(sid)}">'
        f"{role_row}"
        f'<p class="lenses-hero-kicker mb-0">{esc(kicker)}</p>'
        f'<h2 class="text-cyan" id="lenses-portal-title-{esc(sid)}">{esc(name)}</h2>'
        f"{blurb_html}"
        f"{stat_strip}"
        f"{dirty_note}"
        f"{last_line}"
        f"{actions}"
        f"</section>"
    )


def _readme_excerpt(dir_path: Path, max_len: int = 200) -> str:
    for fn in ("README.md", "README.MD", "readme.md"):
        p = dir_path / fn
        if p.is_file():
            text = p.read_text(encoding="utf-8", errors="replace")
            one = " ".join(text.split())
            one = re.sub(r"[#*_`]+", " ", one)
            one = re.sub(r"\s+", " ", one).strip()
            if len(one) > max_len:
                return one[: max_len - 1].rstrip() + "…"
            return one
    return ""


def _load_overview_metrics(lenses_repo_root: Path) -> dict[str, Any]:
    p = lenses_repo_root / "lenses-docs" / "overview-metrics.json"
    if not p.is_file():
        return {}
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return raw if isinstance(raw, dict) else {}


def _truncate_plain(text: str, max_len: int) -> str:
    t = " ".join((text or "").split())
    if len(t) > max_len:
        return t[: max_len - 1].rstrip() + "…"
    return t


def _overview_child_sort_key(ch: dict[str, Any]) -> tuple[bool, int, str]:
    is_git = bool(ch.get("is_git"))
    gi = ch.get("git") or {}
    cu = gi.get("commit_unix")
    ts = int(cu) if isinstance(cu, int) else 0
    if not is_git:
        ts = 0
    return (not is_git, -ts, str(ch.get("name", "")).lower())


def _gather_overview_repo_row(
    c: dict[str, Any],
) -> tuple[
    str,
    Path,
    dict[str, Any],
    list[dict[str, str]],
    tuple[int, int] | None,
    int | None,
    dict[str, int],
    tuple[list[tuple[str, int]], int],
]:
    return overview_repo_row_metrics(c, ext_limit=120)


def _gitmodules_submodule_count(repo_path: Path) -> int:
    p = repo_path / ".gitmodules"
    if not p.is_file():
        return 0
    try:
        text = p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return 0
    return sum(1 for line in text.splitlines() if line.strip().startswith("[submodule"))


def _looks_like_ascii_tree(text: str) -> bool:
    if not text:
        return False
    if "├──" in text or "└──" in text:
        return True
    if "|--" in text or "`--" in text:
        return True
    return False


def _overview_readme_raw(dir_path: Path) -> str:
    for fn in ("README.md", "README.MD", "readme.md"):
        p = dir_path / fn
        if p.is_file():
            return p.read_text(encoding="utf-8", errors="replace")
    return ""


def _overview_repo_description_block(repo_path: Path, reg_sum: str) -> str:
    raw = reg_sum.strip() if reg_sum.strip() else _overview_readme_raw(repo_path)
    stripped = raw.strip()
    if not stripped:
        return '<p class="forge-support small mb-2">No README summary yet.</p>'
    lines = raw.splitlines()
    n_nonempty = sum(1 for ln in lines if ln.strip())
    n_chars = len(stripped)
    tree = _looks_like_ascii_tree(raw)
    needs_details = n_chars > 400 or n_nonempty > 4 or tree
    if not needs_details:
        return (
            f'<p class="mb-2 lenses-overview-repo-lede">{esc(_truncate_plain(raw, 720))}</p>'
        )
    first_line = ""
    for ln in lines:
        t = ln.strip()
        if t:
            first_line = t
            break
    if not first_line:
        lede = _truncate_plain(" ".join(raw.split()), 220)
    else:
        lede = _truncate_plain(first_line, 220)
    summary_label = "Architecture & full notes" if tree else "Full description"
    return (
        f'<p class="mb-2 lenses-overview-repo-lede">{esc(lede)}</p>'
        f'<details class="lenses-overview-repo-details mb-2">'
        f'<summary class="forge-support small">{esc(summary_label)}</summary>'
        f'<div class="lenses-overview-repo-desc-full forge-support small mt-2 mb-0">{esc(raw)}</div>'
        "</details>"
    )


def _overview_repo_section_html(
    *,
    name: str,
    repo_path: Path,
    phref: str,
    is_git: bool,
    gi: dict[str, Any],
    badges: list[str],
    reg_sum: str,
    add_del: tuple[int, int] | None,
    loc: int | None,
    day_dict: dict[str, int],
    ext_rows: list[tuple[str, int]],
    ext_total: int,
    project_urls: dict[str, Any],
    website_names: set[str],
    handbook_quick_links: list[tuple[str, str]] | None = None,
) -> str:
    sm_count = _gitmodules_submodule_count(repo_path)
    if sm_count > 0:
        badges = badges + [
            f'<span class="badge rounded-pill text-bg-dark border border-secondary" '
            f'title="Entries in .gitmodules at repo root">{esc(f"Submodules: {sm_count}")}</span>'
        ]

    meta_items: list[str] = []
    if is_git:
        hf = str(gi.get("head_full", "") or "").strip()
        hs = str(gi.get("head_short", "") or "").strip()
        ou = str(gi.get("origin_url", "") or "").strip()
        c_url = commit_url_for_remote(ou, hf) if hf else ""
        disp = hs or (hf[:12] if len(hf) >= 12 else hf) or "—"
        if c_url and disp != "—":
            head_html = (
                f'<a href="{esc(c_url)}" target="_blank" rel="noopener"><code>{esc(disp)}</code></a>'
            )
        else:
            head_html = f"<code>{esc(disp)}</code>"
        meta_items.append(f"<span>HEAD {head_html}</span>")
        meta_items.append(f"<span>Updated {_portal_last_update_label(gi)}</span>")
        subj = str(gi.get("commit_subject", "") or "").strip()
        if subj:
            meta_items.append(f"<span>Latest: {esc(_truncate_plain(subj, 120))}</span>")
        n_commits = sum(day_dict.values())
        meta_items.append(f"<span>{n_commits} commit{'s' if n_commits != 1 else ''} (7d)</span>")
        if add_del is not None:
            a, d = add_del
            meta_items.append(
                f"<span><strong>+{a}</strong> / <strong>-{d}</strong> lines (7d)</span>"
            )
        if loc is not None:
            meta_items.append(f"<span>~{loc:,} lines (approx.)</span>")
    elif add_del is not None or loc is not None:
        if add_del is not None:
            a, d = add_del
            meta_items.append(
                f"<span><strong>+{a}</strong> / <strong>-{d}</strong> lines (7d)</span>"
            )
        if loc is not None:
            meta_items.append(f"<span>~{loc:,} lines (approx.)</span>")

    meta_html = ""
    if meta_items:
        meta_html = (
            f'<div class="lenses-overview-repo-meta forge-support small mb-2" '
            f'role="group" aria-label="Repository facts">{" · ".join(meta_items)}</div>'
        )

    link_parts: list[str] = [
        f'<a href="{esc(phref)}">Project</a>',
    ]
    pub = str(project_urls.get(name, "") or "").strip()
    if pub:
        link_parts.append(
            f'<a href="{esc(pub)}" target="_blank" rel="noopener">Live</a>'
        )
    if name in website_names:
        link_parts.append(
            f'<a href="{esc(view_local_site_href(name, ""))}">Preview</a>'
        )
    if handbook_quick_links:
        for hb_label, hb_rel in handbook_quick_links:
            link_parts.append(
                f'<a href="{esc(view_local_site_href(name, hb_rel))}">{esc(hb_label)}</a>'
            )
    links_html = (
        f'<p class="lenses-overview-quick-links forge-support small mb-2">'
        f'{" · ".join(link_parts)}</p>'
    )

    ext_html = ""
    if ext_total > 0 and ext_rows:
        pills: list[str] = []
        for ext, cnt in ext_rows[:5]:
            pct = 100.0 * float(cnt) / float(ext_total)
            label = ext if ext else "(no ext)"
            title = f"{cnt} tracked files ({pct:.0f}% of {ext_total})"
            pills.append(
                f'<span class="badge rounded-pill text-bg-dark border border-secondary '
                f'lenses-overview-ext-pill" title="{esc(title)}">{esc(label)} {pct:.0f}%</span>'
            )
        ext_html = (
            '<div class="lenses-overview-ext-row d-flex flex-wrap align-items-center gap-1 mb-2">'
            '<span class="forge-support small me-1">File mix:</span>'
            f'{"".join(pills)}'
            "</div>"
        )

    desc_block = _overview_repo_description_block(repo_path, reg_sum)

    return (
        f'<section class="lenses-overview-repo-card mb-4 p-3 lenses-overview-aside-block">'
        f'<div class="d-flex flex-wrap align-items-center gap-2 mb-2 lenses-pill-row">{"".join(badges)}</div>'
        f'<h3 class="h5 mb-2"><a href="{esc(phref)}">{esc(name)}</a></h3>'
        f"{meta_html}{links_html}{ext_html}{desc_block}"
        "</section>"
    )


def _overview_manual_bar_rows(manual: dict[str, Any]) -> list[tuple[str, float, str]]:
    """(label, value, css_class_suffix) for hour comparison bars."""
    rows: list[tuple[str, float, str]] = []
    keymap = [
        ("Human hours (week)", "human_hours_week", "cyan"),
        ("Without GenAI (estimate)", "estimated_hours_without_genai", "warning"),
        ("GenAI potential (estimate)", "estimated_hours_genai_potential", "success"),
    ]
    for label, key, cls in keymap:
        v = manual.get(key)
        if v is None:
            continue
        try:
            fv = float(v)
        except (TypeError, ValueError):
            continue
        if fv < 0:
            continue
        rows.append((label, fv, cls))
    if not any(r[0] == "Without GenAI (estimate)" for r in rows):
        alt = manual.get("hours_without_genai")
        if alt is not None:
            try:
                fv = float(alt)
                if fv >= 0:
                    rows.append(("Without GenAI (estimate)", fv, "warning"))
            except (TypeError, ValueError):
                pass
    if not any(r[0] == "GenAI potential (estimate)" for r in rows):
        alt2 = manual.get("hours_genai_potential")
        if alt2 is not None:
            try:
                fv = float(alt2)
                if fv >= 0:
                    rows.append(("GenAI potential (estimate)", fv, "success"))
            except (TypeError, ValueError):
                pass
    return rows


def _overview_metrics_strip_html(metrics: dict[str, Any]) -> str:
    parts: list[str] = [
        '<section class="lenses-overview-metrics-strip lenses-overview-aside-block p-3 mb-4">',
        '<h2 class="h5 text-cyan mb-3">Workspace metrics</h2>',
    ]
    if metrics.get("skipped"):
        parts.append(
            f'<p class="forge-support small mb-2">{esc(str(metrics.get("skip_reason", "skipped")))}</p>'
        )
    if metrics.get("errors"):
        parts.append(
            '<p class="small text-warning mb-2">'
            + esc("; ".join(str(e) for e in metrics.get("errors") or []))
            + "</p>"
        )
    ca = metrics.get("cursor_agents_7d") or {}
    if isinstance(ca, dict) and ca.get("session_files_7d") is not None:
        note = str(ca.get("note", ""))
        parts.append(
            "<p class=\"small mb-2\"><strong>Cursor agent sessions (7d)</strong>: "
            f"{int(ca.get('session_files_7d', 0))} transcript file(s) touched; "
            f"{int(ca.get('total_bytes_7d', 0)):,} bytes. "
            f"{esc(note)}</p>"
        )
        if ca.get("transcript_files_capped"):
            parts.append(
                '<p class="forge-support small mb-2">Transcript scan stopped early (file cap).</p>'
            )
    cw = metrics.get("cursor_workspace") or {}
    if isinstance(cw, dict) and cw.get("present"):
        parts.append(
            "<p class=\"small mb-2\"><strong>.cursor</strong>: "
            f"{int(cw.get('rules_count', 0))} rule(s), "
            f"{int(cw.get('skills_count', 0))} skill file(s)"
            f"{'; MCP configured' if cw.get('mcp_present') else ''}.</p>"
        )
    manual = metrics.get("manual") or {}
    if isinstance(manual, dict) and manual:
        bar_rows = _overview_manual_bar_rows(manual)
        if bar_rows:
            vmax = max(v for _, v, _ in bar_rows) or 1.0
            parts.append('<h3 class="h6 text-cyan mb-2">Time comparison (manual)</h3>')
            parts.append(
                '<p class="forge-support small mb-2">Values come from '
                "<code>overview_metrics_manual</code> in lenses-workspace-registry.json "
                "(not measured by git or Cursor).</p>"
            )
            for label, val, cls in bar_rows:
                pct = min(100.0, 100.0 * val / vmax)
                parts.append(
                    f'<div class="mb-2 lenses-overview-metric-bar">'
                    f'<div class="d-flex justify-content-between small mb-1">'
                    f"<span>{esc(label)}</span><span>{val:g} h</span></div>"
                    f'<div class="lenses-overview-hbar-track">'
                    f'<div class="lenses-overview-hbar-fill lenses-overview-hbar-fill--{cls}" '
                    f'style="width:{pct:.1f}%"></div></div></div>'
                )
        note = str(manual.get("methodology_note", "") or "").strip()
        if note:
            parts.append(f'<p class="forge-support small mb-0 mt-2">{esc(note)}</p>')
    if len(parts) <= 2:
        parts.append(
            '<p class="forge-support small mb-0">Run <code>python3 generator/collect-lenses-overview-data.py</code> '
            "after building docs, or start via <code>scripts/run-lenses.sh</code>, to populate Cursor metrics. "
            "Optional manual hours: set <code>overview_metrics_manual</code> in the workspace registry.</p>"
        )
    parts.append(
        f'<p class="forge-support small mt-2 mb-0">Generated: <code>{esc(str(metrics.get("generated_at", "—")))}</code></p>'
    )
    parts.append("</section>")
    return "\n".join(parts)


def lenses_sidebar_html(
    nav_active: str,
    handbook_url: str,
    forge_url: str,
    workspace_projects: list[str],
    switcher_selected: str,
    *,
    roadmap_scope_repo: str | None = None,
    search_scope_repo: str | None = None,
) -> str:
    """Left rail: collapsible tiers (kitchensink ``.nav-tier-*``), one section open at a time."""
    switcher = project_switcher_html(workspace_projects, switcher_selected, bootstrap=True)
    workspace_items = [
        ("overview", "/", "Overview"),
        ("projects", "/projects", "Projects"),
        ("tutorials", "/tutorials", "Tutorials"),
        ("feature_showcase", "/feature-showcase", "Showcase"),
        ("toolset", "/toolset", "Automation"),
        ("websites", "/websites", "Sites"),
        ("search", "/search", "Search"),
        ("board", "/board", "Sticker board"),
    ]
    _rm_q = (
        f"?{urllib.parse.urlencode({'repo': roadmap_scope_repo})}"
        if roadmap_scope_repo
        else ""
    )
    roadmap_items = [
        ("wbs", "/wbs", "Work Breakdown"),
        ("plan", f"/plan{_rm_q}", "Plan"),
        ("timeline", f"/timeline{_rm_q}", "Timeline"),
    ]
    ws_keys = frozenset(
        {
            "overview",
            "projects",
            "tutorials",
            "feature_showcase",
            "toolset",
            "websites",
            "search",
            "board",
        }
    )
    rm_keys = frozenset({"wbs", "plan", "timeline"})

    def _tier_open(keys: frozenset[str]) -> str:
        return ' open' if nav_active in keys else ""

    search_form_cls = "lenses-sidebar-search"
    if nav_active == "search":
        search_form_cls += " lenses-sidebar-search--active"
    _search_icon = (
        '<svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">'
        '<path d="M11.742 10.344a6.5 6.5 0 1 0-1.397 1.398h-.001l3.85 3.85a1 1 0 0 0 1.415-1.414l-3.85-3.85zm-5.242.656a5 5 0 1 1 0-10 5 5 0 0 1 0 10z"/>'
        "</svg>"
    )
    _scope = (search_scope_repo if search_scope_repo is not None else roadmap_scope_repo)
    _scope = str(_scope).strip() if _scope else ""
    _hidden_repo = (
        f'<input type="hidden" name="repo" value="{esc(_scope)}" />'
        if _scope
        else ""
    )
    search_block = (
        f'<form class="{search_form_cls}" method="get" action="/search" role="search" aria-label="Search workspace">'
        f"{_hidden_repo}"
        '<label class="visually-hidden" for="lenses-sidebar-search-q">Search workspace</label>'
        '<input type="search" id="lenses-sidebar-search-q" name="q" class="form-control form-control-sm" '
        'placeholder="Search workspace…" autocomplete="off" />'
        f'<button type="submit" class="lenses-sidebar-search-submit" title="Search">{_search_icon}</button>'
        "</form>"
    )

    # Search is the prominent field above; omit duplicate "Search" nav link (see /search for full UI).
    workspace_items_no_dup = [x for x in workspace_items if x[0] != "search"]

    lines = [search_block, switcher, '<div class="nav-tier-accordion">']

    lines.append(
        f'<details class="nav-tier-wrap"{_tier_open(ws_keys)} name="lenses-sidebar-tier">'
    )
    lines.append('<summary class="nav-tier-summary">Workspace</summary>')
    lines.append('<div class="nav-rail nav-rail--tier">')
    for key, href, label in workspace_items_no_dup:
        cls = " active" if nav_active == key else ""
        lines.append(
            f'<a class="doc-sidebar-link{cls}" href="{esc(href)}">{esc(label)}</a>'
        )
    lines.append("</div></details>")

    lines.append(
        f'<details class="nav-tier-wrap"{_tier_open(rm_keys)} name="lenses-sidebar-tier">'
    )
    lines.append('<summary class="nav-tier-summary">Roadmap management</summary>')
    lines.append('<div class="nav-rail nav-rail--tier">')
    for key, href, label in roadmap_items:
        cls = " active" if nav_active == key else ""
        lines.append(
            f'<a class="doc-sidebar-link{cls}" href="{esc(href)}">{esc(label)}</a>'
        )
    lines.append("</div></details>")

    lines.append('<details class="nav-tier-wrap" name="lenses-sidebar-tier">')
    lines.append('<summary class="nav-tier-summary">Reference</summary>')
    lines.append('<div class="nav-rail nav-rail--tier">')
    lines.append(
        f'<a class="doc-sidebar-link" href="{esc(view_lenses_docs_href("index.html"))}">Lenses docs</a>'
    )
    lines.append("</div></details>")

    lines.append('<details class="nav-tier-wrap" name="lenses-sidebar-tier">')
    lines.append('<summary class="nav-tier-summary">Published</summary>')
    lines.append('<div class="nav-rail nav-rail--tier">')
    lines.append(
        f'<a class="doc-sidebar-link" href="{esc(handbook_url)}" target="_blank" rel="noopener">Handbook</a>'
    )
    lines.append(
        f'<a class="doc-sidebar-link" href="{esc(forge_url)}" target="_blank" rel="noopener">Forge</a>'
    )
    lines.append("</div></details>")

    lines.append("</div>")
    return "\n".join(lines)


def lenses_breadcrumb_html(*parts: tuple[str, str]) -> str:
    """Each part is (href, label); last part may be ("", current_label) for plain text."""
    bits: list[str] = []
    for href, label in parts:
        if href:
            bits.append(f'<a href="{esc(href)}">{esc(label)}</a>')
        else:
            bits.append(f"<span>{esc(label)}</span>")
    return '<p class="forge-support mb-2">' + " · ".join(bits) + "</p>"


def lenses_footer_html() -> str:
    return (
        '<hr class="forge-divider">'
        '<footer class="text-center pb-4">'
        '<p class="forge-support mb-0">lenses · local workspace</p>'
        "</footer>"
    )


LENSES_PROJECT_SWITCHER_CSS = """<style>
.lenses-project-switcher-wrap { margin-bottom: 0.75rem; }
.lenses-project-switcher-wrap--topbar { margin-bottom: 0; align-self: center; }
.lenses-project-switcher-label {
  display: block; font-size: 0.65rem; text-transform: uppercase; letter-spacing: 0.06em;
  color: var(--forge-text-4, #94a3b8); margin-bottom: 0.25rem;
}
.lenses-project-switcher {
  width: 100%; max-width: 100%; font-size: 0.8rem;
}
.lenses-topbar .lenses-project-switcher-wrap--topbar {
  flex: 1 1 12rem; min-width: 10rem; max-width: 20rem;
}
</style>"""


def workspace_project_names_sorted(state: dict[str, Any] | None) -> list[str]:
    """Sorted top-level workspace child names (same set as repo_strategy.workspace_child_names)."""
    if not state:
        return []
    return sorted(workspace_child_names(state))


def switcher_selected_href(current_project: str | None, nav_active: str) -> str:
    """Which `<select>` option is selected: `/`, `/projects`, a project path, or neutral (\"\")."""
    if current_project:
        return f"/projects/{urllib.parse.quote(current_project, safe='')}"
    if nav_active == "overview":
        return "/"
    if nav_active == "projects":
        return "/projects"
    return ""


def workspace_project_for_repo(
    repo: str, workspace_projects: list[str]
) -> str | None:
    """If ``repo`` is a top-level workspace project name, return it for switcher and sidebar scope."""
    r = (repo or "").strip()
    if not r:
        return None
    return r if r in workspace_projects else None


def project_switcher_html(
    workspace_projects: list[str],
    selected_href: str,
    *,
    compact_topbar: bool = False,
    bootstrap: bool = True,
) -> str:
    """Accessible `<select>` to jump to Overview, All projects, or a repository dashboard."""
    wrap_cls = (
        "lenses-project-switcher-wrap lenses-project-switcher-wrap--topbar"
        if compact_topbar
        else "lenses-project-switcher-wrap"
    )
    sel_cls = (
        "form-select form-select-sm lenses-project-switcher"
        if bootstrap
        else "lenses-project-switcher"
    )

    def opt(val: str, label: str) -> str:
        sel = " selected" if selected_href == val else ""
        return f'<option value="{esc(val)}"{sel}>{esc(label)}</option>'

    lines: list[str] = [
        opt("", "— Workspace —"),
        opt("/", "Overview"),
        opt("/projects", "All projects"),
    ]
    if workspace_projects:
        lines.append('<optgroup label="Repositories">')
        for name in workspace_projects:
            href = f"/projects/{urllib.parse.quote(name, safe='')}"
            sel = " selected" if selected_href == href else ""
            lines.append(f'<option value="{esc(href)}"{sel}>{esc(name)}</option>')
        lines.append("</optgroup>")

    inner = "\n".join(lines)
    return (
        f'<div class="{wrap_cls}">'
        '<label for="lenses-project-switcher" class="lenses-project-switcher-label">Workspace</label>'
        f'<select id="lenses-project-switcher" class="{sel_cls}" '
        'aria-label="Workspace or project" '
        'onchange="if(this.value) window.location.href=this.value">'
        f"{inner}"
        "</select></div>"
    )


def nav_bar(
    active: str,
    handbook_url: str,
    forge_url: str,
    workspace_projects: list[str],
    switcher_selected: str,
    *,
    bootstrap: bool = False,
    roadmap_scope_repo: str | None = None,
) -> str:
    workspace_items = [
        ("overview", "/", "Overview"),
        ("projects", "/projects", "Projects"),
        ("tutorials", "/tutorials", "Tutorials"),
        ("feature_showcase", "/feature-showcase", "Showcase"),
        ("toolset", "/toolset", "Automation"),
        ("websites", "/websites", "Sites"),
        ("search", "/search", "Search"),
        ("board", "/board", "Sticker board"),
    ]
    _rm_q = (
        f"?{urllib.parse.urlencode({'repo': roadmap_scope_repo})}"
        if roadmap_scope_repo
        else ""
    )
    roadmap_items = [
        ("wbs", "/wbs", "Work Breakdown"),
        ("plan", f"/plan{_rm_q}", "Plan"),
        ("timeline", f"/timeline{_rm_q}", "Timeline"),
    ]
    links = []
    for key, href, label in workspace_items:
        cls = " active" if active == key else ""
        links.append(
            f'<a class="lenses-nav-link{cls}" href="{esc(href)}">{esc(label)}</a>'
        )
    roadmap_parts = [
        '<span class="lenses-nav-roadmap-label">Roadmap</span>',
    ]
    for key, href, label in roadmap_items:
        cls = " active" if active == key else ""
        roadmap_parts.append(
            f'<a class="lenses-nav-link{cls}" href="{esc(href)}">{esc(label)}</a>'
        )
    links.append(
        '<div class="lenses-nav-roadmap-group" role="group" aria-label="Roadmap management">'
        + "\n    ".join(roadmap_parts)
        + "</div>"
    )
    links.append(
        f'<a class="lenses-nav-link lenses-nav-docs" href="{esc(view_lenses_docs_href("index.html"))}">Lenses docs</a>'
    )
    links.append(
        f'<a class="lenses-nav-link lenses-nav-external" href="{esc(handbook_url)}" target="_blank" rel="noopener">Handbook</a>'
    )
    links.append(
        f'<a class="lenses-nav-link lenses-nav-external" href="{esc(forge_url)}" target="_blank" rel="noopener">Forge</a>'
    )
    inner = "\n    ".join(links)
    switcher = project_switcher_html(
        workspace_projects, switcher_selected, compact_topbar=True, bootstrap=bootstrap
    )
    return f"""<header class="lenses-topbar">
  <div class="lenses-brand">
    <a class="lenses-brand-lockup" href="/" title="Home" aria-label="Home">
      <span class="lenses-brand-icon" aria-hidden="true">F</span>
      <span class="lenses-brand-text">lenses</span>
    </a>
  </div>
  {switcher}
  <nav class="lenses-nav" aria-label="Main">
    {inner}
  </nav>
</header>"""


def layout_page(
    title: str,
    nav_active: str,
    body: str,
    handbook_url: str,
    forge_url: str,
    workspace_projects: list[str] | None = None,
    switcher_selected: str = "",
    *,
    roadmap_scope_repo: str | None = None,
) -> str:
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
    .lenses-brand {{
      flex: 0 0 auto;
      align-self: center;
    }}
    .lenses-brand-lockup {{
      display: inline-flex;
      align-items: center;
      gap: 0.45rem;
      font-weight: 700;
      color: var(--accent);
      text-decoration: none;
      letter-spacing: 0.02em;
    }}
    .lenses-brand-lockup:hover {{
      color: #22d3ee;
    }}
    .lenses-brand-icon {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 1.65rem;
      height: 1.65rem;
      border-radius: 7px;
      background: linear-gradient(135deg, #f59e0b, rgba(245, 158, 11, 0.65));
      color: #0a0e17;
      font-size: 0.82rem;
      font-weight: 900;
      flex-shrink: 0;
    }}
    .lenses-brand-text {{
      font-weight: 700;
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
    .lenses-nav-roadmap-group {{
      display: inline-flex;
      flex-wrap: wrap;
      gap: 0.35rem 0.5rem;
      align-items: center;
      padding-left: 0.55rem;
      margin-left: 0.15rem;
      border-left: 1px solid var(--border);
    }}
    .lenses-nav-roadmap-label {{
      font-size: 0.68rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--muted);
      white-space: nowrap;
    }}
    main {{
      width: 100%;
      margin: 0;
      padding: 1.5rem clamp(1rem, 4vw, 2.75rem) 3rem;
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
    .lenses-overview-lede {{ font-size: 1.05rem; line-height: 1.55; }}
    .lenses-overview-kpi-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(min(100%, 11rem), 1fr));
      gap: 0.75rem;
    }}
    .lenses-overview-kpi {{
      display: flex; flex-direction: column; flex: 1 1 auto; width: 100%; min-width: 0;
      border: 1px solid var(--border); border-radius: 8px;
      padding: 0.85rem; text-decoration: none; color: inherit; box-sizing: border-box;
    }}
    .lenses-overview-kpi:hover {{ border-color: var(--accent); }}
    .lenses-overview-kpi p {{ overflow-wrap: break-word; word-wrap: break-word; }}
    .lenses-overview-kpi .h3 {{ word-break: break-word; line-height: 1.2; }}
    .lenses-overview-kpi .small:last-child {{ margin-top: auto; }}
    .lenses-overview-main {{ display: flex; flex-wrap: wrap; gap: 1.5rem; }}
    .lenses-overview-main > div:first-child {{ flex: 2 1 20rem; min-width: 0; }}
    .lenses-overview-main > div:last-child {{ flex: 1 1 14rem; min-width: 0; }}
    .lenses-overview-feed {{ display: flex; flex-direction: column; gap: 1rem; }}
    .lenses-overview-article {{
      border-left: 3px solid var(--accent); padding: 0.65rem 0 0.65rem 1rem;
      border-bottom: 1px solid var(--border);
    }}
    .lenses-overview-article:last-child {{ border-bottom: none; }}
    .lenses-overview-aside-block {{ border: 1px solid var(--border); border-radius: 8px; padding: 0.85rem; }}
    .lenses-overview-hbar-track {{ height: 0.55rem; border-radius: 4px; background: #334155; overflow: hidden; }}
    .lenses-overview-hbar-fill {{ height: 100%; border-radius: 4px; min-width: 2px; }}
    .lenses-overview-hbar-fill--cyan {{ background: #06b6d4; }}
    .lenses-overview-hbar-fill--warning {{ background: #f59e0b; }}
    .lenses-overview-hbar-fill--success {{ background: #22c55e; }}
    .lenses-overview-commit-body {{ white-space: pre-wrap; line-height: 1.45; }}
    @media (min-width: 992px) {{
      .lenses-overview-newsfeed-sticky {{ position: sticky; top: 0.75rem; max-height: calc(100vh - 1.5rem); overflow-y: auto; }}
    }}
    .lenses-overview-donut-wrap {{ display: flex; flex-wrap: wrap; gap: 1rem; align-items: flex-start; }}
    .lenses-overview-donut-swatch {{ display: inline-block; width: 0.65rem; height: 0.65rem; border-radius: 2px; }}
    .lenses-overview-repo-meta {{ line-height: 1.55; }}
    .lenses-overview-quick-links a {{ color: var(--accent); text-decoration: none; }}
    .lenses-overview-quick-links a:hover {{ text-decoration: underline; }}
    .lenses-overview-ext-pill {{ font-weight: 500; }}
    .lenses-overview-repo-details summary {{ cursor: pointer; color: var(--accent); }}
    .lenses-overview-repo-desc-full {{ white-space: pre-wrap; word-break: break-word; line-height: 1.45; }}
    .lenses-overview-repo-lede {{ line-height: 1.5; }}
    .text-cyan {{ color: var(--accent); }}
    .lenses-project-switcher-wrap {{ margin-bottom: 0.75rem; }}
    .lenses-project-switcher-wrap--topbar {{
      flex: 1 1 12rem; min-width: 10rem; max-width: 20rem; align-self: center; margin-bottom: 0;
    }}
    .lenses-project-switcher-label {{
      display: block; font-size: 0.65rem; text-transform: uppercase; letter-spacing: 0.06em;
      color: var(--muted); margin-bottom: 0.25rem;
    }}
    .lenses-project-switcher {{
      width: 100%; max-width: 18rem; padding: 0.35rem 0.5rem; border-radius: 4px;
      border: 1px solid var(--border); background: #111827; color: var(--text); font-size: 0.85rem;
    }}
  </style>
</head>
<body>
{nav_bar(nav_active, handbook_url, forge_url, workspace_projects if workspace_projects is not None else [], switcher_selected, bootstrap=False, roadmap_scope_repo=roadmap_scope_repo)}
<main>
{body}
</main>
</body>
</html>"""


def _wrap_dashboard(
    lenses_repo_root: Path,
    *,
    browser_title: str,
    nav_active: str,
    page_title: str,
    breadcrumb_html: str,
    body_inner: str,
    handbook_url: str,
    forge_url: str,
    body_extra_class: str = "",
    dashboard_extra_css: str = "",
    workspace_projects: list[str] | None = None,
    current_project: str | None = None,
    roadmap_scope_repo: str | None = None,
    search_scope_repo: str | None = None,
) -> str:
    wp = workspace_projects if workspace_projects is not None else []
    sel = switcher_selected_href(current_project, nav_active)
    extra_merged = LENSES_PROJECT_SWITCHER_CSS + (dashboard_extra_css or "")
    sidebar = lenses_sidebar_html(
        nav_active,
        handbook_url,
        forge_url,
        wp,
        sel,
        roadmap_scope_repo=roadmap_scope_repo,
        search_scope_repo=search_scope_repo,
    )
    footer = lenses_footer_html()
    ks = lenses_showcase_page(
        lenses_repo_root,
        browser_title=browser_title,
        page_title=page_title,
        breadcrumb_html=breadcrumb_html,
        sidebar_html=sidebar,
        body_html=body_inner,
        footer_html=footer,
        body_extra_class=body_extra_class,
        dashboard_extra_css=extra_merged,
    )
    if ks is not None:
        return ks
    body = f"{breadcrumb_html}\n{body_inner}\n{footer}"
    return layout_page(
        browser_title,
        nav_active,
        body,
        handbook_url,
        forge_url,
        wp,
        sel,
        roadmap_scope_repo=roadmap_scope_repo,
    )


def _contributors_table_html(lenses_repo_root: Path, rows: list[tuple[str, str]]) -> str:
    """rows: (commits, name) as strings for display."""
    get_showcase = __import__("lenses.ks_layout", fromlist=["get_showcase_page"]).get_showcase_page
    if get_showcase(lenses_repo_root) is not None:
        try:
            from components import render_table  # noqa: WPS433

            return render_table(
                ["Commits", "Author"],
                [[a, b] for a, b in rows],
                cell_escape=True,
            )
        except ImportError:
            pass
    tr = "".join(
        f"<tr><td>{esc(a)}</td><td>{esc(b)}</td></tr>" for a, b in rows
    )
    return (
        '<table class="table table-sm"><thead><tr><th>Commits</th><th>Author</th></tr></thead>'
        f"<tbody>{tr}</tbody></table>"
    )


def _overview_forge_pulse_section(rollup: dict[str, Any]) -> str:
    """Forge execution summary for the home page (multi-repo rollup)."""
    if not rollup.get("ok"):
        return ""
    n_wbs = int(rollup.get("wbs_count") or 0)
    if n_wbs <= 0:
        return (
            '<section class="lenses-overview-forge-pulse mb-4 lenses-overview-aside-block p-3">'
            '<h2 class="h5 text-cyan mb-2">Forge pulse</h2>'
            '<p class="forge-support small mb-0">No <code>WBS.md</code> under '
            '<code>docs/requirements/</code>. Add requirements or open '
            '<a href="/plan">Plan</a>.</p></section>'
        )

    totals = rollup.get("totals") or {}
    t_active = int(totals.get("active_sparks") or 0)
    t_blocked = int(totals.get("blocked_sparks") or 0)
    t_gaps = int(totals.get("spark_rows_with_gaps") or 0)

    hz = rollup.get("horizon_totals") or {}
    hz_html = ""
    if isinstance(hz, dict) and hz:
        hz_html = horizon_badges_html({str(k): int(v) for k, v in hz.items() if int(v) > 0})

    active = rollup.get("active_sparks") or []
    blocked = rollup.get("blocked_sparks") or []
    gaps = rollup.get("gaps") or []
    upcoming = rollup.get("upcoming_milestones") or []
    progress = rollup.get("progress_samples") or []

    def _li_spark(row: dict[str, Any]) -> str:
        sid = esc(str(row.get("spark_id") or ""))
        title = esc(str(row.get("title") or sid))
        href = esc(str(row.get("plan_href") or "/plan"))
        repo = esc(str(row.get("repo_hint") or ""))
        st = str(row.get("status") or "").strip()
        st_s = f' <span class="text-muted">({esc(st)})</span>' if st else ""
        return (
            f'<li class="mb-1"><a href="{href}"><code>{sid}</code></a> {title}{st_s}'
            f'<span class="text-muted small"> · {repo}</span></li>'
        )

    def _li_blocked(row: dict[str, Any]) -> str:
        sid = esc(str(row.get("spark_id") or ""))
        title = esc(str(row.get("title") or sid))
        href = esc(str(row.get("plan_href") or "/plan"))
        blk = esc(str(row.get("blocker") or "")[:160])
        repo = esc(str(row.get("repo_hint") or ""))
        return (
            f'<li class="mb-1"><a href="{href}"><code>{sid}</code></a> {title}'
            f'<br /><span class="small text-warning">{blk}</span>'
            f'<span class="text-muted small"> · {repo}</span></li>'
        )

    def _li_gap(row: dict[str, Any]) -> str:
        sid = esc(str(row.get("spark_id") or ""))
        href = esc(str(row.get("plan_href") or "/plan"))
        g = esc(str(row.get("gap") or ""))
        return (
            f'<li class="mb-1"><a href="{href}"><code>{sid}</code></a> — {g}</li>'
        )

    active_items = "".join(_li_spark(x) for x in active if isinstance(x, dict))
    blocked_items = "".join(_li_blocked(x) for x in blocked if isinstance(x, dict))
    gap_items = "".join(_li_gap(x) for x in gaps if isinstance(x, dict))

    if not active_items:
        active_items = '<li class="forge-support">No active sparks (or no Charge).</li>'
    if not blocked_items:
        blocked_items = '<li class="forge-support">No blocked sparks.</li>'
    if not gap_items:
        gap_items = '<li class="forge-support">No evidence or decision gaps flagged.</li>'

    upcoming_str = ", ".join(esc(str(x)) for x in upcoming[:8]) if upcoming else ""
    up_body = (
        upcoming_str
        if upcoming_str
        else '<span class="forge-support">No milestone schedule parsed.</span>'
    )

    prog_bits: list[str] = []
    for p in progress[:6]:
        if not isinstance(p, dict):
            continue
        lab = esc(str(p.get("label") or ""))
        try:
            pct_f = float(p.get("pct") or 0)
        except (TypeError, ValueError):
            pct_f = 0.0
        rh = esc(str(p.get("repo_hint") or ""))
        prog_bits.append(f'<li class="small mb-0">{lab} — {pct_f:.0f}% <span class="text-muted">({rh})</span></li>')
    prog_html = "<ul class=\"list-unstyled mb-0\">" + "".join(prog_bits) + "</ul>" if prog_bits else (
        '<p class="forge-support small mb-0">No epic % data in roadmaps.</p>'
    )

    summary_line = (
        f"<strong>{t_active}</strong> active spark(s), <strong>{t_blocked}</strong> blocked, "
        f"<strong>{t_gaps}</strong> spark row(s) with readiness gaps."
    )

    return (
        '<section class="lenses-overview-forge-pulse mb-4 lenses-overview-aside-block p-3">'
        '<div class="d-flex flex-wrap align-items-center justify-content-between gap-2 mb-2">'
        '<h2 class="h5 text-cyan mb-0">Forge pulse</h2>'
        '<a class="small" href="/plan">Open Plan</a> · <a class="small" href="/timeline">Timeline</a>'
        "</div>"
        f'<p class="forge-support small mb-3">{summary_line}</p>'
        f"{hz_html}"
        f'<div class="row g-3 mt-1">'
        '<div class="col-lg-4">'
        '<h3 class="h6 text-cyan">Active sparks</h3>'
        f'<ul class="list-unstyled small mb-0">{active_items}</ul>'
        "</div>"
        '<div class="col-lg-4">'
        '<h3 class="h6 text-cyan">Blocked</h3>'
        f'<ul class="list-unstyled small mb-0">{blocked_items}</ul>'
        "</div>"
        '<div class="col-lg-4">'
        '<h3 class="h6 text-cyan">Evidence / decision gaps</h3>'
        f'<ul class="list-unstyled small mb-0">{gap_items}</ul>'
        "</div>"
        "</div>"
        '<div class="row g-3 mt-3">'
        '<div class="col-lg-6">'
        '<h3 class="h6 text-cyan">Upcoming work windows (roadmap)</h3>'
        f'<p class="small mb-0">{up_body}</p>'
        "</div>"
        '<div class="col-lg-6">'
        '<h3 class="h6 text-cyan">Lightweight progress</h3>'
        f"{prog_html}"
        "</div>"
        "</div>"
        "</section>"
    )


def page_overview(
    state: dict[str, Any],
    registry: dict[str, Any],
    handbook_url: str,
    forge_url: str,
    lenses_repo_root: Path,
) -> str:
    children: list[dict[str, Any]] = [
        c for c in (state.get("children") or []) if isinstance(c, dict)
    ]
    n_children = len(children)
    n_git = sum(1 for c in children if c.get("is_git"))
    n_non_git = n_children - n_git
    n_wbs = len(state.get("wbs") or [])
    n_roadmaps = len(state.get("roadmaps") or [])
    websites = state.get("websites") or []
    n_sites = len(websites)
    scripts = state.get("toolset") or {}
    root_scripts = scripts.get("root_scripts") or []
    n_scripts = len(root_scripts)
    project_urls = registry.get("project_urls") or {}
    project_summaries = registry.get("project_summaries") or {}
    website_names = {str(w.get("name", "")) for w in websites if isinstance(w, dict)}
    website_pages_by_name: dict[str, Any] = {}
    for w in websites:
        if not isinstance(w, dict):
            continue
        wn = str(w.get("name", "")).strip()
        if not wn:
            continue
        website_pages_by_name[wn] = w.get("pages")
    handbook_links_by_name: dict[str, list[tuple[str, str]]] = {}
    for c in children:
        cn = str(c.get("name", "")).strip()
        if not cn:
            continue
        cpath = Path(str(c.get("path", "")))
        books = list_child_handbooks(cpath)
        if not books:
            continue
        pages = website_pages_by_name.get(cn)
        is_site = cn in website_names
        handbook_links_by_name[cn] = [
            (_handbook_display_label(b, pages, is_site), b.local_site_rel) for b in books
        ]
    workspace_root_str = str(state.get("workspace_root", ""))
    resolved_str = str(state.get("resolved_at", ""))
    workspace_root = Path(workspace_root_str) if workspace_root_str else Path(".")
    rollup = build_overview_forge_rollup(workspace_root, state)
    forge_pulse = _overview_forge_pulse_section(rollup)

    dated: list[tuple[datetime, dict[str, Any]]] = []
    for c in children:
        if not c.get("is_git"):
            continue
        gi = c.get("git") or {}
        dt = _parse_git_iso_datetime(str(gi.get("commit_date", "")))
        if dt is not None:
            dated.append((dt, c))
    dated.sort(key=lambda x: x[0], reverse=True)
    newest: tuple[datetime, dict[str, Any]] | None = dated[0] if dated else None

    if newest:
        ndt, nc = newest
        nn = str(nc.get("name", ""))
        subj = str((nc.get("git") or {}).get("commit_subject", "") or "").strip()
        if not subj:
            subj = "Latest commit"
        rel = _relative_time_short(ndt)
        latest_line = (
            f"Latest commit: {nn} — {subj} ({rel})."
        )
    else:
        latest_line = "No dated commits in the scan; open a project for git detail."

    tagline_bits: list[str] = [
        f"{n_children} top-level folder{'s' if n_children != 1 else ''}",
        f"{n_git} git repo{'s' if n_git != 1 else ''}",
    ]
    if n_sites:
        tagline_bits.append(f"{n_sites} Firebase site{'s' if n_sites != 1 else ''}")
    tagline = ", ".join(tagline_bits) + "."
    if n_non_git:
        tagline += f" Includes {n_non_git} non-git folder{'s' if n_non_git != 1 else ''}."

    support_points: list[str] = [latest_line]
    if n_wbs:
        support_points.append(
            f"{n_wbs} WBS file{'s' if n_wbs != 1 else ''} under docs/requirements/"
        )
    if n_roadmaps:
        support_points.append(
            f"{n_roadmaps} roadmap file{'s' if n_roadmaps != 1 else ''} under docs/"
        )
    if n_scripts:
        support_points.append(
            f"{n_scripts} shell script{'s' if n_scripts != 1 else ''} at workspace root"
        )

    clarification = (
        f"Workspace: {workspace_root_str} · Scan: {resolved_str}"
    )

    hero_html = ""
    get_showcase = __import__("lenses.ks_layout", fromlist=["get_showcase_page"]).get_showcase_page
    if get_showcase(lenses_repo_root) is not None:
        try:
            from components import render_product_landing_hero  # noqa: WPS433

            hero_html = render_product_landing_hero(
                "Workspace overview",
                tagline,
                kicker="lenses",
                clarification=clarification,
                primary_cta_href="/projects",
                primary_cta_label="Browse projects",
                secondary_cta_href=view_lenses_docs_href("index.html"),
                secondary_cta_label="Lenses docs",
                secondary_links=[("Tutorials", "/tutorials")],
                support_points=support_points,
            )
            hero_html = _rewrite_lenses_hero_spectral_img_src(hero_html)
        except ImportError:
            hero_html = ""
    if not hero_html:
        hero_html = (
            '<div class="lenses-overview-hero-fallback mb-4">'
            '<p class="small text-cyan text-uppercase mb-1">lenses</p>'
            '<h1 class="h2 font-display forge-gradient-text mb-2">Workspace overview</h1>'
            f'<p class="forge-support mb-2">{esc(tagline)}</p>'
            f'<p class="forge-support small mb-2">{esc(clarification)}</p>'
            '<p class="forge-support small mb-0">'
            '<a href="/projects">Browse projects</a> · '
            f'<a href="{esc(view_lenses_docs_href("index.html"))}">Lenses docs</a> · '
            '<a href="/tutorials">Tutorials</a>'
            "</p>"
            "</div>"
        )

    def kpi_tile(href: str, label: str, value: str, cta: str) -> str:
        return (
            f'<a class="forge-card breathe-link d-flex flex-column h-100 w-100 min-w-0 text-decoration-none lenses-overview-kpi" href="{esc(href)}">'
            f'<p class="forge-support small text-uppercase mb-1 text-break">{esc(label)}</p>'
            f'<p class="h3 mb-2 text-break">{value}</p>'
            f'<p class="small text-cyan mb-0 mt-auto text-break">{esc(cta)}</p>'
            f"</a>"
        )

    sorted_children = sorted(children, key=_overview_child_sort_key)
    max_workers = min(12, max(1, len(sorted_children)))
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        rows_data = list(pool.map(_gather_overview_repo_row, sorted_children))

    repo_blocks: list[str] = []
    loc_chart_rows: list[tuple[str, int]] = []
    newsfeed_sections: list[str] = []
    agg_ext: Counter[str] = Counter()
    workspace_tracked_files = 0
    day_maps: list[dict[str, int]] = []
    total_loc_sum = 0
    loc_total_rows: list[tuple[str, int]] = []

    for row in rows_data:
        name, path, c, commits, add_del, loc, day_dict, (ext_rows, ext_total) = row
        day_maps.append(day_dict)
        workspace_tracked_files += ext_total
        for ext, cnt in ext_rows:
            agg_ext[ext] += cnt
        if loc is not None:
            total_loc_sum += loc
            loc_total_rows.append((name, loc))
        if not name:
            continue
        phref = f"/projects/{urllib.parse.quote(name, safe='')}"
        reg_sum = str(project_summaries.get(name, "")).strip()

        gi = c.get("git") or {}
        is_git = bool(c.get("is_git"))
        badges = []
        if is_git:
            dirty = gi.get("dirty")
            badges.append(
                '<span class="badge rounded-pill text-bg-warning">Dirty</span>'
                if dirty
                else '<span class="badge rounded-pill text-bg-success">Clean</span>'
            )
            br = str(gi.get("branch", "") or "").strip()
            if br:
                badges.append(f'<span class="badge rounded-pill text-bg-secondary">{esc(br)}</span>')
        else:
            badges.append('<span class="badge rounded-pill text-bg-secondary">Not git</span>')
        if name in website_names:
            badges.append('<span class="badge rounded-pill text-bg-info">Firebase</span>')
        if project_urls.get(name):
            badges.append('<span class="badge rounded-pill text-bg-primary">Web</span>')

        if add_del is not None:
            a, _d = add_del
            loc_chart_rows.append((name, a))

        repo_blocks.append(
            _overview_repo_section_html(
                name=name,
                repo_path=path,
                phref=phref,
                is_git=is_git,
                gi=gi,
                badges=badges,
                reg_sum=reg_sum,
                add_del=add_del,
                loc=loc,
                day_dict=day_dict,
                ext_rows=ext_rows,
                ext_total=ext_total,
                project_urls=project_urls,
                website_names=website_names,
                handbook_quick_links=handbook_links_by_name.get(name),
            )
        )

        if is_git:
            origin = str(gi.get("origin_url", "") or "").strip()
            commit_items: list[str] = []
            if not commits:
                commit_items.append('<p class="forge-support small mb-0">No commits returned.</p>')
            for cm in commits:
                h_full = str(cm.get("hash_full", "") or "").strip()
                h_short = str(cm.get("hash_short", "") or "").strip()
                subj = str(cm.get("subject", "") or "").strip() or "(no subject)"
                body_raw = str(cm.get("body", "") or "").strip()
                body_ex = esc(_truncate_plain(body_raw, 420)) if body_raw else ""
                dt_raw = str(cm.get("date", "") or "").strip()
                dt_parsed = _parse_git_iso_datetime(dt_raw)
                when = _relative_time_short(dt_parsed) if dt_parsed else dt_raw
                c_url = commit_url_for_remote(origin, h_full) if h_full else ""
                hash_html = (
                    f'<a href="{esc(c_url)}" target="_blank" rel="noopener">{esc(h_short or h_full[:12])}</a>'
                    if c_url
                    else f"<code>{esc(h_short or h_full[:12] or '—')}</code>"
                )
                commit_items.append(
                    f'<article class="lenses-overview-article lenses-overview-feed-commit mb-2">'
                    f'<h4 class="h6 lenses-overview-headline mb-1">{esc(subj)}</h4>'
                    f'<p class="forge-support small mb-1">{hash_html} · {esc(when)}</p>'
                    + (f'<p class="small mb-0 lenses-overview-commit-body">{body_ex}</p>' if body_ex else "")
                    + "</article>"
                )
            newsfeed_sections.append(
                f'<section class="lenses-overview-repo-feed mb-4">'
                f'<h3 class="h6 text-cyan mb-2"><a href="{esc(phref)}">{esc(name)}</a></h3>'
                f'<div class="lenses-overview-feed">{"\n".join(commit_items)}</div>'
                f"</section>"
            )

    loc_chart_rows.sort(key=lambda x: -x[1])
    loc_chart_rows = loc_chart_rows[:40]
    loc_added_svg = svg_loc_added_horizontal_bars(loc_chart_rows)

    loc_total_sorted = sorted(loc_total_rows, key=lambda x: -x[1])[:40]
    total_loc_bars_svg = svg_repo_total_loc_bars(loc_total_sorted)
    donut_html = svg_loc_share_donut(loc_total_rows, top_n=8)

    daily_series = workspace_commits_daily_series(day_maps, days=7)
    daily_commits_svg = svg_commit_daily_bar_chart(daily_series)

    ext_top = sorted(agg_ext.items(), key=lambda x: -x[1])[:15]
    ext_denom = workspace_tracked_files if workspace_tracked_files > 0 else max(1, sum(agg_ext.values()))
    ext_heat_html = extension_heatmap_html(ext_top, ext_denom)

    kpi_row = (
        '<div class="lenses-overview-kpi-grid mb-4">'
        + kpi_tile("/projects", "Top-level folders", esc(str(n_children)), "Open Projects →")
        + kpi_tile("/websites", "Firebase sites", esc(str(n_sites)), "Sites →")
        + kpi_tile("/wbs", "Work breakdown files", esc(str(n_wbs)), "Work Breakdown →")
        + kpi_tile("/plan", "Plan", esc(str(n_roadmaps)), "Open Plan →")
        + kpi_tile("/timeline", "Timeline", esc(str(n_roadmaps)), "Milestone windows →")
        + kpi_tile("/toolset", "Root scripts", esc(str(n_scripts)), "Automation →")
        + "</div>"
    )

    analytics_block = (
        '<section class="lenses-overview-charts mt-2 mb-4">'
        '<h2 class="h5 text-cyan mb-2">Workspace analytics</h2>'
        '<p class="forge-support small mb-3">Total approx. tracked lines (sum of per-repo samples): '
        f"<strong>~{total_loc_sum:,}</strong>. "
        "Same caveats as project stats: newline-based estimate, file count/size caps, binary skips — "
        "not equivalent to <code>cloc</code>.</p>"
        '<div class="row g-4">'
        '<div class="col-lg-6">'
        '<h3 class="h6 text-cyan mb-2">Commits by day (7 days)</h3>'
        '<p class="forge-support small mb-2">Summed across all git repos; UTC calendar days; '
        'git window is <code>--since="7 days ago"</code>.</p>'
        f"{daily_commits_svg}"
        "</div>"
        '<div class="col-lg-6">'
        '<h3 class="h6 text-cyan mb-2">Lines added by repository (7 days)</h3>'
        '<p class="forge-support small mb-2">From <code>git log --numstat</code>; binary and some merge '
        "lines excluded; additions only.</p>"
        f"{loc_added_svg}"
        "</div>"
        '<div class="col-lg-6">'
        '<h3 class="h6 text-cyan mb-2">Repository size (approx. LoC)</h3>'
        '<p class="forge-support small mb-2">Per-repo newline counts (sampled/capped).</p>'
        f"{total_loc_bars_svg}"
        '<h4 class="h6 text-cyan mt-3 mb-2">Share of workspace lines</h4>'
        '<p class="forge-support small mb-2">Top 8 repositories by approx. lines; remainder grouped as Other.</p>'
        f'<div class="lenses-overview-donut-wrap">{donut_html}</div>'
        "</div>"
        '<div class="col-lg-6">'
        '<h3 class="h6 text-cyan mb-2">File types (workspace)</h3>'
        '<p class="forge-support small mb-2">Extension histogram merged from each repo (top 120 extensions '
        f"per repo). Tracked files (sum of repo totals): <strong>{workspace_tracked_files:,}</strong>. "
        "Bar width is share of that total; rare types may be omitted.</p>"
        f"{ext_heat_html}"
        "</div>"
        "</div></section>"
    )

    analytics_block_wrapped = (
        '<details class="lenses-overview-analytics-details mb-4">'
        '<summary class="h6 text-cyan user-select-none" style="cursor:pointer">'
        "Workspace analytics (commits, lines of code, file types)</summary>"
        f'<div class="pt-3 mt-2 border-top border-secondary">{analytics_block}</div>'
        "</details>"
    )

    score_rows: list[tuple[str, int]] = []
    for c in sorted_children:
        sc = c.get("standards_compliance")
        if isinstance(sc, dict) and "score" in sc:
            score_rows.append((str(c.get("name", "")), int(sc.get("score") or 0)))
    score_rows.sort(key=lambda x: -x[1])
    standards_svg = svg_compliance_score_bars(score_rows)
    std_note = str(state.get("standards_compliance_note") or "").strip()
    hb_base = handbook_url.rstrip("/")
    bp_std = f"{hb_base}/sdlc--methodologies-agentic-coding-standards.html"
    standards_block = (
        '<section class="lenses-overview-standards mt-2 mb-4">'
        '<h2 class="h5 text-cyan mb-2">Standards and agentic hygiene</h2>'
        f'<p class="forge-support small mb-2">{esc(std_note)} '
        f'<a href="{esc(bp_std)}" target="_blank" rel="noopener">Agentic coding standards</a> (handbook).</p>'
        '<h3 class="h6 text-cyan mb-2">Compliance score by repository</h3>'
        '<p class="forge-support small mb-2">Heuristic 0–100 from filesystem signals (CI, docs, '
        "sdlc/blueprints, .cursor, Forge paths, locks, Firebase). Not an audit.</p>"
        f"{standards_svg}"
        "</section>"
    )

    main_col = (
        '<div class="col-lg-7 mb-4 mb-lg-0">'
        '<h2 class="h5 text-cyan mb-3">Repositories</h2>'
        + ("".join(repo_blocks) if repo_blocks else '<p class="forge-support">No folders found.</p>')
        + analytics_block_wrapped
        + standards_block
        + "</div>"
    )

    if newsfeed_sections:
        feed_wrap = "".join(newsfeed_sections)
    else:
        feed_wrap = '<p class="forge-support">No git repositories in this workspace.</p>'

    news_col = (
        '<div class="col-lg-5 mb-4">'
        '<div class="lenses-overview-newsfeed-sticky">'
        '<h2 class="h5 text-cyan mb-3">Recent commits by repository</h2>'
        f"{feed_wrap}"
        "</div></div>"
    )

    site_lines: list[str] = []
    for w in websites:
        if not isinstance(w, dict):
            continue
        wn = str(w.get("name", ""))
        if not wn:
            continue
        html_total = w.get("html_total")
        ht = f"{html_total} HTML page(s)" if html_total is not None else "—"
        pub = str(project_urls.get(wn, "")).strip()
        pub_l = (
            f' · <a href="{esc(pub)}" target="_blank" rel="noopener">live</a>' if pub else ""
        )
        site_lines.append(
            f'<li class="mb-2"><a href="/websites">{esc(wn)}</a> — {esc(str(ht))}{pub_l}</li>'
        )
    sites_block = (
        f'<section class="lenses-overview-aside-block mb-md-0 mb-3 h-100">'
        f'<h3 class="h6 text-cyan">Publishing</h3>'
        f'<ul class="list-unstyled small mb-0">'
        + (
            "".join(site_lines)
            if site_lines
            else '<li class="forge-support">No Firebase sites detected.</li>'
        )
        + "</ul></section>"
    )

    wbs_block = (
        f'<section class="lenses-overview-aside-block h-100">'
        f'<h3 class="h6 text-cyan">Requirements</h3>'
        f'<p class="small mb-0"><strong>{n_wbs}</strong> WBS file(s). '
        f'<a href="/wbs">Open WBS</a></p></section>'
    )

    metrics = _load_overview_metrics(lenses_repo_root)
    metrics_strip = _overview_metrics_strip_html(metrics)

    foot = (
        '<p class="forge-support mb-0 mt-4">Workspace discovery is cached briefly on the server '
        "(default ~20s, <code>LENSES_SCAN_CACHE_SEC</code>). "
        "Add <code>?refresh=1</code> to any URL to force a fresh scan. "
        '<a href="/overview/charts-api">API-driven charts</a> (same metrics as below).</p>'
    )

    body_inner = (
        '<div class="lenses-overview lenses-dash">'
        f'<div class="lenses-overview-hero-wrap mb-2">{hero_html}</div>'
        f"{forge_pulse}"
        f"{kpi_row}"
        f'<div class="row g-4 lenses-overview-main align-items-start">{main_col}{news_col}</div>'
        f"{metrics_strip}"
        '<div class="row g-3 mt-1 mb-2">'
        f'<div class="col-md-6">{sites_block}</div>'
        f'<div class="col-md-6">{wbs_block}</div>'
        "</div>"
        f"{foot}</div>"
    )

    bc = lenses_breadcrumb_html(("/", "Overview"))
    return _wrap_dashboard(
        lenses_repo_root,
        browser_title="Overview — lenses",
        nav_active="overview",
        page_title="Overview",
        breadcrumb_html=bc,
        body_inner=body_inner,
        handbook_url=handbook_url,
        forge_url=forge_url,
        workspace_projects=workspace_project_names_sorted(state),
        current_project=None,
    )


def page_projects(
    state: dict[str, Any],
    registry: dict[str, Any],
    handbook_url: str,
    forge_url: str,
    lenses_repo_root: Path,
) -> str:
    website_names = {str(w.get("name", "")) for w in (state.get("websites") or [])}
    website_labels = registry.get("website_labels") or {}
    if not isinstance(website_labels, dict):
        website_labels = {}
    project_urls = registry.get("project_urls") or {}
    project_summaries = registry.get("project_summaries") or {}
    if not isinstance(project_summaries, dict):
        project_summaries = {}
    wbs_counts: dict[str, int] = {}
    for w in state.get("wbs") or []:
        if not isinstance(w, dict):
            continue
        hint = str(w.get("repo_hint", "")).strip()
        if hint:
            wbs_counts[hint] = wbs_counts.get(hint, 0) + 1

    rows: list[dict[str, Any]] = [
        c for c in (state.get("children") or []) if isinstance(c, dict) and str(c.get("name", "")).strip()
    ]

    def _portal_sort_key(ch: dict[str, Any]) -> tuple[bool, int, str]:
        is_git = bool(ch.get("is_git"))
        gi = ch.get("git") or {}
        cu = gi.get("commit_unix")
        ts = int(cu) if isinstance(cu, int) else 0
        if not is_git:
            ts = 0
        return (not is_git, -ts, str(ch.get("name", "")).lower())

    rows.sort(key=_portal_sort_key)

    metrics = _prefetch_portal_repo_metrics(rows)

    get_showcase = __import__("lenses.ks_layout", fromlist=["get_showcase_page"]).get_showcase_page
    ks_preview = False
    if get_showcase(lenses_repo_root) is not None:
        try:
            import components as _ks_components  # noqa: WPS433

            ks_preview = hasattr(_ks_components, "render_topic_preview_trigger")
        except ImportError:
            ks_preview = False

    sections: list[str] = []
    for c in rows:
        name = str(c.get("name", ""))
        path = Path(str(c.get("path", "")))
        card_href = f"/projects/{urllib.parse.quote(name, safe='')}"
        loc, numstat = metrics.get(name, (None, (0, 0)))
        sections.append(
            _project_portal_panel_html(
                name=name,
                path=path,
                c=c,
                website_names=website_names,
                website_labels=website_labels,
                project_urls=project_urls,
                project_summaries=project_summaries,
                wbs_count=wbs_counts.get(name, 0),
                card_href=card_href,
                loc=loc,
                numstat=numstat,
                ks_preview=ks_preview,
            )
        )

    stack = (
        '<div class="lenses-sites-stack" id="lenses-projects-stack">' + "".join(sections) + "</div>"
        if sections
        else '<p class="forge-support">No directories found.</p>'
    )
    body_inner = (
        f"{_lenses_vertical_hero_styles()}"
        '<p class="forge-support">Sorted by last commit (newest first). Each panel summarizes the repo at a glance '
        "(registry summary or README, size, recent activity). "
        "<strong>Open dashboard</strong> goes to the full project page; "
        "when the design system is present, <strong>Preview on this page</strong> opens an embedded view.</p>"
        f"{stack}"
    )
    bc = lenses_breadcrumb_html(("/", "Overview"), ("/projects", "Projects"))
    return _wrap_dashboard(
        lenses_repo_root,
        browser_title="Projects — lenses",
        nav_active="projects",
        page_title="Projects",
        breadcrumb_html=bc,
        body_inner=body_inner,
        handbook_url=handbook_url,
        forge_url=forge_url,
        workspace_projects=workspace_project_names_sorted(state),
        current_project=None,
    )


def page_tutorials(
    state: dict[str, Any],
    _registry: dict[str, Any],
    handbook_url: str,
    forge_url: str,
    lenses_repo_root: Path,
) -> str:
    children: list[dict[str, Any]] = [
        c for c in (state.get("children") or []) if isinstance(c, dict)
    ]
    website_pages_by_name: dict[str, Any] = {}
    websites_list = state.get("websites") or []
    for w in websites_list:
        if not isinstance(w, dict):
            continue
        wn = str(w.get("name", "")).strip()
        if not wn:
            continue
        website_pages_by_name[wn] = w.get("pages")
    website_names = {str(w.get("name", "")) for w in websites_list if isinstance(w, dict)}

    cards: list[str] = []
    for c in sorted(children, key=lambda x: str(x.get("name", "")).lower()):
        cn = str(c.get("name", "")).strip()
        if not cn:
            continue
        cpath = Path(str(c.get("path", "")))
        books = list_child_handbooks(cpath)
        if not books:
            continue
        pages = website_pages_by_name.get(cn)
        is_site = cn in website_names
        proj_href = f"/projects/{urllib.parse.quote(cn, safe='')}"
        for b in books:
            label = _handbook_display_label(b, pages, is_site)
            href = view_local_site_href(cn, b.local_site_rel)
            open_label = (
                "Open engineer handbook"
                if b.kind == "tutorials"
                else "Open tutorial"
            )
            cards.append(
                '<section class="lenses-site-hero-section forge-card mb-3">'
                f'<h2 class="h5 text-cyan mb-2">{esc(cn)}</h2>'
                f'<p class="forge-support small mb-2"><span class="text-body-secondary">'
                f'{esc(b.label_default)}</span> — {esc(label)}</p>'
                '<div class="d-flex flex-wrap gap-2">'
                f'<a class="btn btn-sm btn-forge" href="{esc(href)}">{esc(open_label)}</a>'
                f'<a class="btn btn-sm btn-outline-secondary" href="{esc(proj_href)}">'
                "Project dashboard</a>"
                "</div></section>"
            )

    if not cards:
        body_stack = (
            "<p class=\"forge-support mb-3\">No workspace repositories have a detected "
            "forge-autodoc handbook (<code>tutorial/index.html</code>, "
            "<code>tutorials/index.html</code>, <code>lenses/tutorials/index.html</code>, "
            "or <code>website/tutorials/index.html</code>). "
            "Run <code>./build-fa-tutorials.sh</code> or your site generator (e.g. forgesdlc "
            "<code>python3 generator/build-site.py</code>), then refresh this page.</p>"
            '<p class="forge-support small mb-0">See also '
            f'<a href="{esc(view_lenses_docs_href("index.html"))}">Lenses docs</a> '
            "for setup and the HTTP API reference.</p>"
        )
    else:
        body_stack = (
            "<p class=\"forge-support mb-3\">Handbooks are served on this host as "
            "<code>/local-site/&lt;repo&gt;/tutorial/…</code> or "
            "<code>/local-site/&lt;repo&gt;/tutorials/…</code> (same origin as the dashboard).</p>"
            + "".join(cards)
        )

    body_inner = _lenses_vertical_hero_styles() + body_stack
    bc = lenses_breadcrumb_html(("/", "Overview"), ("/tutorials", "Tutorials"))
    return _wrap_dashboard(
        lenses_repo_root,
        browser_title="Tutorials — lenses",
        nav_active="tutorials",
        page_title="Tutorials",
        breadcrumb_html=bc,
        body_inner=body_inner,
        handbook_url=handbook_url,
        forge_url=forge_url,
        workspace_projects=workspace_project_names_sorted(state),
        current_project=None,
    )


def _project_cta_group_html(label: str, buttons: list[str]) -> str:
    if not buttons:
        return ""
    return (
        '<div class="lenses-project-cta-group">'
        f'<span class="lenses-project-cta-group-label">{esc(label)}</span>'
        '<div class="d-flex flex-wrap gap-2">'
        f'{"".join(buttons)}'
        "</div></div>"
    )


def page_project_detail(
    state: dict[str, Any],
    registry: dict[str, Any],
    project_name: str,
    repo_path: Path,
    handbook_url: str,
    forge_url: str,
    lenses_repo_root: Path,
) -> str:
    child = next(
        (x for x in (state.get("children") or []) if str(x.get("name")) == project_name),
        None,
    )
    gi = (child or {}).get("git") or {}
    is_git = bool((child or {}).get("is_git"))
    origin = str(gi.get("origin_url", ""))
    head_full = str(gi.get("head_full", ""))
    head_short = str(gi.get("head_short", ""))
    repo_https = remote_to_https_repo_url(origin)
    commit_url = commit_url_for_remote(origin, head_full)
    project_urls = registry.get("project_urls") or {}
    project_summaries = registry.get("project_summaries") or {}
    reg_summary = (
        str(project_summaries.get(project_name, "")).strip()
        if isinstance(project_summaries, dict)
        else ""
    )
    external_url = str(project_urls.get(project_name, "")).strip()
    website_names = {str(w.get("name", "")) for w in (state.get("websites") or [])}
    is_site = project_name in website_names
    wbs_entries = [
        w
        for w in (state.get("wbs") or [])
        if isinstance(w, dict) and str(w.get("repo_hint", "")) == project_name
    ]
    roadmap_entries = [
        r
        for r in (state.get("roadmaps") or [])
        if isinstance(r, dict) and str(r.get("repo_hint", "")) == project_name
    ]
    has_wbs = bool(wbs_entries)
    has_roadmap = bool(roadmap_entries)
    sid = re.sub(r"[^a-z0-9_-]+", "-", project_name.lower()).strip("-") or "project"

    stats: dict[str, Any] = {}
    if is_git:
        stats = collect_project_stats(repo_path)

    badges: list[str] = []
    if is_git:
        dirty = gi.get("dirty")
        badges.append(
            '<span class="badge rounded-pill text-bg-warning">Dirty</span>'
            if dirty
            else '<span class="badge rounded-pill text-bg-success">Clean</span>'
        )
        br = str(gi.get("branch", ""))
        if br:
            badges.append(
                f'<span class="badge rounded-pill text-bg-secondary">{esc(br)}</span>'
            )
        if head_short:
            badges.append(
                f'<span class="badge rounded-pill text-bg-dark border border-secondary">'
                f"{esc(head_short)}</span>"
            )
    else:
        badges.append(
            '<span class="badge rounded-pill text-bg-secondary">Not a git repo</span>'
        )
    if is_site:
        badges.append(
            '<span class="badge rounded-pill text-bg-info">Firebase site</span>'
        )
    if has_wbs:
        nw = len(wbs_entries)
        badges.append(
            f'<span class="badge rounded-pill text-bg-dark border border-secondary">'
            f"WBS ×{nw}</span>"
        )
    if has_roadmap:
        nr = len(roadmap_entries)
        badges.append(
            f'<span class="badge rounded-pill text-bg-dark border border-secondary">'
            f"Roadmap ×{nr}</span>"
        )

    kicker = "Git repository" if is_git else "Workspace folder"
    path_line = (
        f'<p class="forge-support small mb-0">Path: <code>{esc(str(repo_path.resolve()))}</code></p>'
    )

    if reg_summary:
        blurb_block = f'<p class="forge-support small mb-0 mt-2">{esc(reg_summary)}</p>'
    else:
        blurb_block = ""

    wk_tb = _website_by_name(state, project_name) if is_site else None
    wk_pages = wk_tb.get("pages") if wk_tb else None
    handbooks = list_child_handbooks(repo_path)
    browse_href = ""
    if is_site:
        browse_href = f"/websites/browse?site={urllib.parse.quote(project_name, safe='')}"

    docs_index_exists = False
    if repo_path.is_dir():
        try:
            rp_docs = repo_path.resolve()
            doc_idx = (rp_docs / "docs" / "index.html").resolve()
            doc_idx.relative_to(rp_docs)
            docs_index_exists = doc_idx.is_file()
        except (OSError, ValueError):
            docs_index_exists = False

    ws_root_raw = state.get("workspace_root")
    board_n = 0
    if isinstance(ws_root_raw, str) and ws_root_raw.strip():
        board_n = board_count_for_project(Path(ws_root_raw.strip()), project_name)

    sticker_hub = f"/board?project={urllib.parse.quote(project_name, safe='')}"
    if handbooks:
        doc_bits = []
        for b in handbooks:
            lbl = _handbook_display_label(b, wk_pages, is_site)
            href = view_local_site_href(project_name, b.local_site_rel)
            doc_bits.append(
                f'{esc(b.label_default)}: <a href="{esc(href)}">{esc(lbl)}</a>'
            )
        doc_tutorial = " · ".join(doc_bits)
    else:
        doc_tutorial = (
            '<span class="text-body-secondary">No forge-autodoc handbook detected</span> '
            "(<code>tutorial/index.html</code>, <code>tutorials/index.html</code>, "
            "<code>lenses/tutorials/index.html</code>, or <code>website/tutorials/index.html</code>)"
        )
    doc_extra = ""
    if docs_index_exists:
        dh = view_local_site_href(project_name, "docs/index.html")
        doc_extra = (
            f'<p class="mb-0 mt-1 forge-support">Docs site: '
            f'<a href="{esc(dh)}">docs/index.html</a></p>'
        )
    doc_inner = f'<div class="forge-support small">{doc_tutorial}</div>{doc_extra}'

    if is_site:
        web_inner = (
            f'<p class="mb-0 forge-support small">Firebase Hosting child. '
            f'<a href="{esc(browse_href)}">Preview in lenses</a> · '
            f'<a href="{esc(view_local_site_href(project_name, "index.html"))}">'
            f"Open local site root</a></p>"
        )
    else:
        web_inner = (
            '<p class="mb-0 forge-support small text-body-secondary">'
            "Not a Firebase Hosting child in this workspace</p>"
        )

    nwbs = len(wbs_entries)
    plan_rows: list[str] = []
    if has_wbs:
        plan_rows.append(
            f'<p class="mb-1 forge-support small">{nwbs} requirement file(s) — '
            f'<a href="/wbs">View WBS</a></p>'
        )
    else:
        plan_rows.append(
            '<p class="mb-1 forge-support small text-body-secondary">'
            "No WBS rooted here</p>"
        )
    if has_roadmap:
        rm_link_bits: list[str] = []
        first_wbs_path = ""
        if wbs_entries:
            first_wbs_path = str(wbs_entries[0].get("rel_path", "")).strip()
        for r in roadmap_entries:
            rp = str(r.get("rel_path", "")).strip()
            if not rp:
                continue
            q = (
                f"wbs_p={urllib.parse.quote(first_wbs_path, safe='')}"
                f"&repo={urllib.parse.quote(project_name, safe='')}"
                f"&roadmap_p={urllib.parse.quote(rp, safe='')}"
            )
            if not first_wbs_path:
                q = (
                    f"repo={urllib.parse.quote(project_name, safe='')}"
                    f"&roadmap_p={urllib.parse.quote(rp, safe='')}"
                )
            plan_href = f"/plan?{q}"
            tl_href = f"/timeline?{q}"
            rm_link_bits.append(
                f'<a href="{esc(plan_href)}">Plan</a> / <a href="{esc(tl_href)}">Timeline</a> '
                f'(<code class="small">{esc(rp)}</code>)'
            )
        nrm = len(rm_link_bits)
        plan_rows.append(
            f'<p class="mb-0 forge-support small">{nrm} roadmap file(s): '
            f'{" · ".join(rm_link_bits)}</p>'
        )
    else:
        plan_rows.append(
            '<p class="mb-0 forge-support small text-body-secondary">'
            "No <code>ROADMAP.md</code> under this project’s <code>docs/</code> tree</p>"
        )
    plan_inner = "".join(plan_rows)

    if board_n:
        sticker_lead = f"{board_n} board(s) · "
    else:
        sticker_lead = '<span class="text-body-secondary">None yet</span> · '
    sticker_inner = (
        f'<p class="mb-0 forge-support small">{sticker_lead}'
        f'<a href="{esc(sticker_hub)}">Sticker board hub</a></p>'
    )

    docs_site_href = (
        view_local_site_href(project_name, "docs/index.html") if docs_index_exists else ""
    )
    hero_quick_parts: list[str] = []
    for b in handbooks:
        hb_lbl = _handbook_display_label(b, wk_pages, is_site)
        hb_href = view_local_site_href(project_name, b.local_site_rel)
        hero_quick_parts.append(
            f'<a class="btn btn-sm btn-outline-secondary" href="{esc(hb_href)}">{esc(hb_lbl)}</a>'
        )
    if is_site:
        hero_quick_parts.append(
            f'<a class="btn btn-sm btn-forge" href="{esc(browse_href)}">Preview in lenses</a>'
        )
        hero_quick_parts.append(
            f'<a class="btn btn-sm btn-outline-info" href="{esc(view_local_site_href(project_name, "index.html"))}">'
            f"Open local site</a>"
        )
    if external_url:
        hero_quick_parts.append(
            f'<a class="btn btn-sm btn-outline-warning" href="{esc(external_url)}" '
            f'target="_blank" rel="noopener">Project site</a>'
        )
    if docs_site_href:
        hero_quick_parts.append(
            f'<a class="btn btn-sm btn-outline-secondary" href="{esc(docs_site_href)}">Docs site</a>'
        )
    hero_quick_html = ""
    if hero_quick_parts:
        hero_quick_html = (
            '<div class="lenses-project-hero-quick d-flex flex-wrap gap-2 mt-2 mb-2" '
            f'aria-label="Quick links">{"".join(hero_quick_parts)}</div>'
        )

    whats_here_block = (
        f'<div class="lenses-project-whats-here mt-3 pt-2 border-top border-secondary '
        f'border-opacity-25" aria-labelledby="lenses-proj-whats-{esc(sid)}">'
        f'<h3 class="h6 text-cyan mb-2" id="lenses-proj-whats-{esc(sid)}">'
        f"What&#8217;s here</h3>"
        f'<div class="lenses-project-whats-here-grid">'
        f'<div class="lenses-project-whats-here-item">'
        f'<div class="lenses-project-whats-here-k small mb-1">Documentation</div>{doc_inner}'
        f"</div>"
        f'<div class="lenses-project-whats-here-item">'
        f'<div class="lenses-project-whats-here-k small mb-1">Website</div>{web_inner}'
        f"</div>"
        f'<div class="lenses-project-whats-here-item">'
        f'<div class="lenses-project-whats-here-k small mb-1">Planning</div>{plan_inner}'
        f"</div>"
        f'<div class="lenses-project-whats-here-item">'
        f'<div class="lenses-project-whats-here-k small mb-1">Sticker boards</div>{sticker_inner}'
        f"</div>"
        f"</div></div>"
    )

    stat_bits: list[str] = []
    if is_git:
        loc = approx_tracked_lines(repo_path)
        if loc is not None:
            stat_bits.append(
                f'<span class="badge rounded-pill text-bg-dark border border-secondary">'
                f"~{loc:,} lines (approx.)</span>"
            )
        stat_bits.append(
            f'<span class="badge rounded-pill text-bg-dark border border-secondary">'
            f"updated {_portal_last_update_label(gi)}</span>"
        )
        add_d, del_d = git_numstat_since(repo_path, 7)
        if add_d or del_d:
            stat_bits.append(
                f'<span class="badge rounded-pill text-bg-dark border border-secondary">'
                f"+{add_d:,} / −{del_d:,} lines (7d)</span>"
            )
        ct = stats.get("commits_total")
        if ct is not None:
            stat_bits.append(
                f'<span class="badge rounded-pill text-bg-dark border border-secondary">'
                f"{esc(str(ct))} commits</span>"
            )
        total_tf = int(stats.get("tracked_files") or 0)
        if total_tf:
            stat_bits.append(
                f'<span class="badge rounded-pill text-bg-dark border border-secondary">'
                f"{total_tf} tracked files</span>"
            )
    stat_strip = (
        f'<div class="lenses-site-stat-strip">{"".join(stat_bits)}</div>'
        if stat_bits
        else ""
    )

    git_line = ""
    if is_git:
        subj = str(gi.get("commit_subject", ""))
        if len(subj) > 140:
            subj = subj[:137].rstrip() + "…"
        c_url = commit_url_for_remote(origin, head_full) if head_full else ""
        rev_html = (
            f'<a href="{esc(c_url)}" target="_blank" rel="noopener">{esc(head_short)}</a>'
            if c_url and head_short
            else esc(head_short)
            if head_short
            else ""
        )
        parts = [x for x in (rev_html, esc(subj) if subj else "") if x]
        if parts:
            git_line = (
                '<p class="forge-support small mb-0 mt-2"><strong>Last commit</strong> '
                + " · ".join(parts)
                + "</p>"
            )

    grp_source: list[str] = []
    if repo_https:
        grp_source.append(
            f'<a class="btn btn-sm btn-outline-info" href="{esc(repo_https)}" '
            f'target="_blank" rel="noopener">Repository</a>'
        )
    if commit_url:
        grp_source.append(
            f'<a class="btn btn-sm btn-outline-info" href="{esc(commit_url)}" '
            f'target="_blank" rel="noopener">Commit</a>'
        )

    grp_ship: list[str] = []
    if external_url:
        grp_ship.append(
            f'<a class="btn btn-sm btn-outline-warning" href="{esc(external_url)}" '
            f'target="_blank" rel="noopener">Project site</a>'
        )
    if is_site:
        grp_ship.append(
            f'<a class="btn btn-sm btn-forge" href="{esc(browse_href)}">Preview in lenses</a>'
        )
        grp_ship.append(
            f'<a class="btn btn-sm btn-outline-info" href="{esc(view_local_site_href(project_name, "index.html"))}">'
            f"Open local site root</a>"
        )
        grp_ship.append(
            '<a class="btn btn-sm btn-outline-secondary" href="/websites">Firebase sites list</a>'
        )

    grp_learn: list[str] = []
    for b in handbooks:
        hb_lbl = _handbook_display_label(b, wk_pages, is_site)
        hb_href = view_local_site_href(project_name, b.local_site_rel)
        grp_learn.append(
            f'<a class="btn btn-sm btn-outline-secondary" href="{esc(hb_href)}">{esc(hb_lbl)}</a>'
        )
    if has_wbs:
        grp_learn.append('<a class="btn btn-sm btn-outline-secondary" href="/wbs">WBS</a>')
    grp_learn.append(
        f'<a class="btn btn-sm btn-outline-secondary" href="{esc(sticker_hub)}">Sticker board</a>'
    )

    strategy_href = f"/projects/{urllib.parse.quote(project_name, safe='')}/strategy"
    charts_api_href = f"/projects/{urllib.parse.quote(project_name, safe='')}/charts-api"
    grp_nav = [
        f'<a class="btn btn-sm btn-outline-secondary" href="{esc(strategy_href)}">'
        f"Repo &amp; strategy</a>",
        f'<a class="btn btn-sm btn-outline-secondary" href="{esc(charts_api_href)}">'
        f"Charts (API)</a>",
        '<a class="btn btn-sm btn-link px-0" href="/projects">← All projects</a>',
    ]

    cta_row = (
        '<div class="lenses-project-cta-groups mt-3">'
        f'{_project_cta_group_html("Source", grp_source)}'
        f'{_project_cta_group_html("Ship / preview", grp_ship)}'
        f'{_project_cta_group_html("Learn & plan", grp_learn)}'
        f'{_project_cta_group_html("Navigate", grp_nav)}'
        "</div>"
    )

    technical = ""
    if is_git and origin:
        cdate = str(gi.get("commit_date", ""))
        date_bit = (
            f'<p class="forge-support small mb-1"><strong>Commit date</strong>: <code>{esc(cdate)}</code></p>'
            if cdate
            else ""
        )
        technical = f"""<details class="mt-3">
<summary class="small forge-support">Technical</summary>
{date_bit}<p class="forge-support small mb-0"><strong>Origin</strong>: <code>{esc(origin)}</code></p>
</details>"""

    readme_panel = ""
    if not reg_summary and repo_path.is_dir():
        prev_long = _readme_excerpt(repo_path, max_len=480)
        if prev_long:
            readme_panel = (
                f'<section class="lenses-site-hero-section forge-card" aria-labelledby="lenses-proj-readme-{esc(sid)}">'
                f'<h3 class="h6 text-cyan mb-2" id="lenses-proj-readme-{esc(sid)}">README preview</h3>'
                f'<p class="forge-support small mb-0">{esc(prev_long)}</p>'
                f"</section>"
            )

    api_stats_href = f"/api/project/{urllib.parse.quote(project_name, safe='')}/stats"
    panels: list[str] = []

    hero_section = (
        f'<section class="lenses-site-hero-section forge-card" '
        f'id="lenses-project-{esc(sid)}" aria-labelledby="lenses-project-title-{esc(sid)}">'
        f'<div class="d-flex flex-wrap justify-content-between gap-2 align-items-start mb-1">'
        f'<div class="lenses-pill-row d-flex flex-wrap gap-1">{"".join(badges)}</div></div>'
        f'<p class="lenses-hero-kicker mb-0">{esc(kicker)}</p>'
        f'<h2 class="text-cyan" id="lenses-project-title-{esc(sid)}">{esc(project_name)}</h2>'
        f"{path_line}{blurb_block}"
        f"{hero_quick_html}"
        f"{whats_here_block}"
        f"{stat_strip}"
        f"{git_line}"
        f"{cta_row}"
        f"{technical}"
        f"</section>"
    )
    panels.append(hero_section)
    panels.append(readme_panel)

    sc_data = (child or {}).get("standards_compliance")
    if isinstance(sc_data, dict) and sc_data.get("checks"):
        panels.append(
            _project_standards_compliance_html(sid, sc_data, handbook_url)
        )

    if is_git:
        weekly = [(x["week"], x["count"]) for x in stats.get("commits_by_week") or []]
        chart_90 = svg_commit_bar_chart(weekly)
        panels.append(
            f'<section class="lenses-site-hero-section forge-card" '
            f'aria-labelledby="lenses-proj-act90-{esc(sid)}">'
            f'<h3 class="h6 text-cyan mb-2" id="lenses-proj-act90-{esc(sid)}">Activity (90 days)</h3>'
            f"{chart_90}"
            f"</section>"
        )

        day_map = commits_by_day_dict(repo_path, 7)
        daily_series = workspace_commits_daily_series([day_map], days=7)
        chart_7 = svg_commit_daily_bar_chart(daily_series, width=520, height=180)
        panels.append(
            f'<section class="lenses-site-hero-section forge-card" '
            f'aria-labelledby="lenses-proj-act7-{esc(sid)}">'
            f'<h3 class="h6 text-cyan mb-2" id="lenses-proj-act7-{esc(sid)}">Activity (7 days)</h3>'
            f'<p class="forge-support small mb-2">Commits per calendar day (rolling window).</p>'
            f"{chart_7}"
            f"</section>"
        )

        contrib_rows = [
            (str(x["commits"]), str(x["name"])) for x in stats.get("contributors") or []
        ]
        contrib_tbl = _contributors_table_html(lenses_repo_root, contrib_rows)
        panels.append(
            f'<section class="lenses-site-hero-section forge-card" '
            f'aria-labelledby="lenses-proj-contrib-{esc(sid)}">'
            f'<h3 class="h6 text-cyan mb-2" id="lenses-proj-contrib-{esc(sid)}">Contributors</h3>'
            f"{contrib_tbl}"
            f"</section>"
        )

        ext_data = [(x["extension"], x["count"]) for x in stats.get("extensions") or []]
        total_tf = int(stats.get("tracked_files") or 0)
        heat = extension_heatmap_html(ext_data, total_tf)
        ct_val = stats.get("commits_total")
        total_line = (
            f'<p class="forge-support small mb-0"><strong>Total commits</strong>: {esc(str(ct_val))}</p>'
            if ct_val is not None
            else ""
        )
        panels.append(
            f'<section class="lenses-site-hero-section forge-card" '
            f'aria-labelledby="lenses-proj-files-{esc(sid)}">'
            f'<h3 class="h6 text-cyan mb-2" id="lenses-proj-files-{esc(sid)}">File types</h3>'
            f'<p class="forge-support small mb-2">Tracked files: {total_tf}</p>'
            f"{heat}"
            f"{total_line}"
            f"</section>"
        )

    git_panel = ""
    if is_git:
        api_git = f"/api/project/{urllib.parse.quote(project_name, safe='')}/git"
        lazy_stats = (
            f'<p class="forge-support small mb-2"><a href="{esc(api_stats_href)}">JSON stats API</a> '
            f"(same data as charts; useful for tooling).</p>"
        )
        git_panel = f"""
<section class="lenses-site-hero-section forge-card" aria-labelledby="lenses-proj-git-{esc(sid)}">
<h3 class="h6 text-cyan mb-2" id="lenses-proj-git-{esc(sid)}">Git actions</h3>
{lazy_stats}
<p class="forge-support small">Runs on this machine against <code>{esc(str(repo_path))}</code>. Fetch and pull need network access.</p>
<div class="d-flex flex-wrap gap-2 mb-2" id="lenses-git-actions" data-git-api="{esc(api_git)}">
  <button type="button" class="btn btn-sm btn-forge" data-lenses-git="status">Status</button>
  <button type="button" class="btn btn-sm btn-forge" data-lenses-git="fetch">Fetch</button>
  <button type="button" class="btn btn-sm btn-forge" data-lenses-git="pull">Pull (ff-only)</button>
</div>
<pre class="lenses-git-out mb-0" id="lenses-git-out" aria-live="polite"></pre>
<script>
(function() {{
  var root = document.getElementById('lenses-git-actions');
  if (!root) return;
  var api = root.getAttribute('data-git-api');
  var out = document.getElementById('lenses-git-out');
  root.querySelectorAll('[data-lenses-git]').forEach(function(btn) {{
    btn.addEventListener('click', function() {{
      var action = btn.getAttribute('data-lenses-git');
      out.textContent = 'Running git ' + action + '…';
      fetch(api, {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify({{ action: action }})
      }}).then(function(r) {{ return r.json(); }}).then(function(j) {{
        var t = (j.ok ? 'OK' : 'Exit ' + j.exit_code) + '\\n';
        if (j.stdout) t += j.stdout;
        if (j.stderr) t += (j.stdout ? '\\n' : '') + j.stderr;
        if (j.error) t += j.error;
        out.textContent = t;
      }}).catch(function(e) {{ out.textContent = String(e); }});
    }});
  }});
}})();
</script>
</section>
"""
    panels.append(git_panel)

    stack = '<div class="lenses-sites-stack lenses-project-stack">' + "".join(panels) + "</div>"
    body_inner = f"{_lenses_vertical_hero_styles()}\n{stack}"
    bc = lenses_breadcrumb_html(
        ("/", "Overview"),
        ("/projects", "Projects"),
        ("", project_name),
    )
    return _wrap_dashboard(
        lenses_repo_root,
        browser_title=f"{project_name} — lenses",
        nav_active="projects",
        page_title=project_name,
        breadcrumb_html=bc,
        body_inner=body_inner,
        handbook_url=handbook_url,
        forge_url=forge_url,
        workspace_projects=workspace_project_names_sorted(state),
        current_project=project_name,
        roadmap_scope_repo=project_name,
    )


def page_project_repo_strategy(
    state: dict[str, Any],
    registry: dict[str, Any],
    project_name: str,
    repo_path: Path,
    handbook_url: str,
    forge_url: str,
    lenses_repo_root: Path,
) -> str:
    child = next(
        (x for x in (state.get("children") or []) if str(x.get("name")) == project_name),
        None,
    )
    gi = (child or {}).get("git") or {}
    is_git = bool((child or {}).get("is_git"))
    sid = re.sub(r"[^a-z0-9_-]+", "-", project_name.lower()).strip("-") or "project"
    ws_names = workspace_child_names(state)
    strat = strategy_registry_entry(registry, project_name)

    back_href = f"/projects/{urllib.parse.quote(project_name, safe='')}"
    lead = (
        f'<p class="forge-support mb-3">'
        f'<a class="btn btn-sm btn-link px-0" href="{esc(back_href)}">← Project dashboard</a>'
        f' · <a class="btn btn-sm btn-link px-0" href="/projects">All projects</a></p>'
    )

    panels: list[str] = []

    if not is_git:
        panels.append(
            f'<section class="lenses-site-hero-section forge-card" '
            f'aria-labelledby="lenses-strat-ng-{esc(sid)}">'
            f'<h2 class="h5 text-cyan" id="lenses-strat-ng-{esc(sid)}">Not a git repository</h2>'
            f'<p class="forge-support small mb-0">Path: <code>{esc(str(repo_path.resolve()))}</code>. '
            f"Submodule layout and remote-branch hints apply to git checkouts only.</p></section>"
        )
    else:
        modules = parse_gitmodules(repo_path)
        status_txt, st_trunc, st_err = git_submodule_status_text(repo_path)
        default_br = remote_default_branch(repo_path)

        rows_html: list[str] = []
        for m in modules:
            pth = str(m.get("path", "") or "")
            url = str(m.get("url", "") or "")
            br = str(m.get("branch", "") or "")
            hint = sibling_workspace_hint(pth, ws_names, project_name)
            hint_cell = hint if hint else "—"
            rows_html.append(
                "<tr>"
                f'<td><code>{esc(pth)}</code></td>'
                f'<td class="small">{esc(url)}</td>'
                f"<td>{esc(br) if br else '—'}</td>"
                f'<td class="small">{hint_cell}</td>'
                "</tr>"
            )
        if rows_html:
            table = (
                '<table class="table table-sm table-bordered mb-0">'
                "<thead><tr>"
                "<th>Path</th><th>URL</th><th>.gitmodules branch</th>"
                "<th>Workspace</th>"
                "</tr></thead>"
                f'<tbody>{"".join(rows_html)}</tbody></table>'
            )
        else:
            table = (
                '<p class="forge-support small mb-0">No <code>.gitmodules</code> at this repo root.</p>'
            )

        if st_err:
            status_block = f'<p class="text-warning small mb-2">{esc(st_err)}</p>'
        elif status_txt:
            note = " (output truncated)" if st_trunc else ""
            status_block = (
                f'<p class="forge-support small mb-2"><code>git submodule status</code>{note}</p>'
                f'<pre class="lenses-git-out mb-0">{esc(status_txt)}</pre>'
            )
        else:
            status_block = (
                '<p class="forge-support small mb-0">No submodule status output.</p>'
            )

        svg = svg_submodule_layout_svg(
            project_name, [str(m.get("path") or "") for m in modules if m.get("path")]
        )

        asset = str(strat.get("ks_diagram_asset") or "").strip()
        ks_extra = ""
        if asset:
            ks_rel = asset.lstrip("/").replace("\\", "/")
            ksp = repo_path / "kitchensink" / ks_rel
            if ksp.is_file():
                ks_extra = ks_diagram_img(ks_rel, alt="Repository illustration")
        if not ks_extra and modules:
            ks_extra = ks_diagram_img(KS_ROADMAP_TEMPLATE, alt="Repository structure")

        viz_block = ""
        if svg:
            viz_block += f'<div class="mb-3">{svg}</div>'
        if ks_extra:
            viz_block += ks_extra

        branching_bits: list[str] = []
        br_cur = str(gi.get("branch", "") or "").strip()
        if br_cur:
            branching_bits.append(f"<li>Current branch: <code>{esc(br_cur)}</code></li>")
        dirty = gi.get("dirty")
        branching_bits.append(
            "<li>Working tree: "
            + (
                "<strong>dirty</strong> (uncommitted changes)"
                if dirty
                else "<strong>clean</strong>"
            )
            + "</li>"
        )
        if default_br:
            branching_bits.append(
                f"<li>Remote default (<code>origin/HEAD</code>): <code>{esc(default_br)}</code></li>"
            )
        else:
            branching_bits.append(
                "<li>Remote default branch not resolved "
                "(try <code>git fetch</code> so <code>origin/HEAD</code> exists).</li>"
            )
        br_note = str(strat.get("branching") or strat.get("branching_notes") or "").strip()
        if br_note:
            branching_bits.append(f"<li>{esc(br_note)}</li>")

        storage_section = (
            f'<section class="lenses-site-hero-section forge-card" '
            f'aria-labelledby="lenses-strat-store-{esc(sid)}">'
            f'<h2 class="h5 text-cyan mb-3" id="lenses-strat-store-{esc(sid)}">'
            f"How code is stored</h2>"
            f"{table}"
            f'<div class="mt-3">{status_block}</div>'
            f"{viz_block}"
            f"</section>"
        )
        branching_section = (
            f'<section class="lenses-site-hero-section forge-card mt-3" '
            f'aria-labelledby="lenses-strat-br-{esc(sid)}">'
            f'<h2 class="h5 text-cyan mb-2" id="lenses-strat-br-{esc(sid)}">Branching</h2>'
            f'<ul class="forge-support small mb-0">{"".join(branching_bits)}</ul>'
            f"</section>"
        )
        panels.extend([storage_section, branching_section])

    maint_raw = strat.get("maintenance")
    if isinstance(maint_raw, list) and maint_raw:
        bullets = [str(x).strip() for x in maint_raw if str(x).strip()]
    else:
        bullets = []
    if not bullets:
        bullets = list(DEFAULT_MAINTENANCE_BULLETS)
    maint_html = "".join(f"<li>{esc(b)}</li>" for b in bullets)
    mn = str(strat.get("maintenance_notes") or "").strip()
    notes_html = f'<p class="forge-support small mt-2 mb-0">{esc(mn)}</p>' if mn else ""

    md_raw = load_optional_strategy_markdown(repo_path) if repo_path.is_dir() else None
    file_html = ""
    if md_raw:
        file_html = (
            '<div class="lenses-repo-strategy-md forge-support small mt-3">'
            f"{markdown_to_html_fragment(md_raw)}</div>"
        )

    maint_section = (
        f'<section class="lenses-site-hero-section forge-card mt-3" '
        f'aria-labelledby="lenses-strat-maint-{esc(sid)}">'
        f'<h2 class="h5 text-cyan mb-2" id="lenses-strat-maint-{esc(sid)}">'
        f"Maintenance rules</h2>"
        f"<ul class=\"mb-0\">{maint_html}</ul>"
        f"{notes_html}"
        f'<p class="forge-support small mt-2 mb-0">Optional: add '
        f"<code>LENSES-REPO-STRATEGY.md</code> at this repo root for team-specific notes.</p>"
        f"{file_html}"
        f"</section>"
    )
    panels.append(maint_section)

    body_inner = (
        f"{_lenses_vertical_hero_styles()}\n{lead}\n"
        '<div class="lenses-sites-stack lenses-project-stack">'
        + "".join(panels)
        + "</div>"
    )
    bc = lenses_breadcrumb_html(
        ("/", "Overview"),
        ("/projects", "Projects"),
        (f"/projects/{urllib.parse.quote(project_name, safe='')}", project_name),
        ("", "Repo & strategy"),
    )
    return _wrap_dashboard(
        lenses_repo_root,
        browser_title=f"{project_name} — repo strategy — lenses",
        nav_active="projects",
        page_title=f"{project_name}: repo & strategy",
        breadcrumb_html=bc,
        body_inner=body_inner,
        handbook_url=handbook_url,
        forge_url=forge_url,
        workspace_projects=workspace_project_names_sorted(state),
        current_project=project_name,
        roadmap_scope_repo=project_name,
    )


def page_toolset(
    state: dict[str, Any],
    handbook_url: str,
    forge_url: str,
    lenses_repo_root: Path,
) -> str:
    ts = state.get("toolset") or {}
    names = ts.get("root_scripts") or []
    cards_raw = ts.get("script_cards")
    if not isinstance(cards_raw, list) or not cards_raw:
        cards_raw = [{"name": n, "blurb": ""} for n in names]
    cards: list[str] = []
    for entry in cards_raw:
        if not isinstance(entry, dict):
            continue
        name = str(entry.get("name", "")).strip()
        if not name:
            continue
        blurb_raw = str(entry.get("blurb", "")).strip()
        blurb = esc(blurb_raw) if blurb_raw else (
            '<span class="forge-support">No description in script comments</span>'
        )
        href = f"/toolset/{urllib.parse.quote(name, safe='')}"
        badges = '<span class="badge rounded-pill text-bg-secondary">Shell</span>'
        cards.append(
            f'<div class="col-md-6 col-xl-4 mb-3">'
            f'<div class="forge-card d-block h-100 p-3">'
            f'<p class="card-label text-cyan mb-2 d-flex lenses-pill-row align-items-center">{badges}</p>'
            f'<h3 class="h5 mt-0 mb-2">{esc(name)}</h3>'
            f'<p class="forge-support small mb-3">{blurb}</p>'
            f'<a class="btn btn-sm btn-forge" href="{esc(href)}">Open run screen →</a>'
            f"</div></div>"
        )
    grid = (
        '<div class="row g-3">' + "".join(cards) + "</div>"
        if cards
        else '<p class="forge-support">No shell scripts at workspace root.</p>'
    )
    cursor = ts.get("cursor_dir") or ""
    cur_html = f"<p><code>{esc(cursor)}</code></p>" if cursor else (
        '<p class="forge-support">No <code>.cursor</code> directory at workspace root.</p>'
    )
    body_inner = f"""<p class="forge-support">Orchestration scripts at the workspace root (not nested repo websites). Open a card to run a script and view console output.</p>
{grid}
<h2 class="h5 text-cyan mt-4">Cursor / IDE</h2>
{cur_html}"""
    bc = lenses_breadcrumb_html(("/", "Overview"), ("/toolset", "Automation"))
    return _wrap_dashboard(
        lenses_repo_root,
        browser_title="Automation — lenses",
        nav_active="toolset",
        page_title="Automation",
        breadcrumb_html=bc,
        body_inner=body_inner,
        handbook_url=handbook_url,
        forge_url=forge_url,
        workspace_projects=workspace_project_names_sorted(state),
        current_project=None,
    )


def page_search(
    state: dict[str, Any],
    _registry: dict[str, Any],
    handbook_url: str,
    forge_url: str,
    lenses_repo_root: Path,
    *,
    query: str,
    hits: list[dict[str, Any]],
    total: int = 0,
    limit: int = 25,
    offset: int = 0,
    scope_repo: str | None = None,
    reindex_notice: str | None = None,
) -> str:
    rows: list[str] = []
    for h in hits:
        u = str(h.get("url", ""))
        u_href = embed_in_app_doc_url(u)
        title = str(h.get("title", "") or u)
        snip = str(h.get("snippet", ""))
        src = str(h.get("source", ""))
        rc = h.get("ref_count")
        ref_line = ""
        if rc is not None and int(rc) > 0:
            ref_line = (
                f'<div class="small text-secondary mt-1">Inbound links: {int(rc)}</div>'
            )
        rows.append(
            f'<li class="mb-3"><a href="{esc(u_href)}"><strong>{esc(title)}</strong></a>'
            f'<div class="small text-secondary mt-1">{esc(src)}</div>'
            f"{ref_line}"
            f'<div class="small mt-1">{esc(snip)}</div></li>'
        )

    def _search_qs(extra: dict[str, str | int]) -> str:
        p: dict[str, str] = {}
        qv = query.strip()
        if qv:
            p["q"] = qv
        if scope_repo:
            p["repo"] = str(scope_repo).strip()
        p["limit"] = str(int(limit))
        for k, v in extra.items():
            p[str(k)] = str(v)
        return urllib.parse.urlencode(p)

    rd_parts: dict[str, str] = {}
    if query.strip():
        rd_parts["q"] = query.strip()
    if scope_repo:
        rd_parts["repo"] = str(scope_repo).strip()
    rd_tail = urllib.parse.urlencode(rd_parts) if rd_parts else ""
    redirect_target = f"/search?{rd_tail}" if rd_tail else "/search"
    idx_href = (
        "/api/search/reindex?redirect="
        + urllib.parse.quote(redirect_target, safe="/?:=&")
    )
    idx_btn = (
        '<p class="mb-3">'
        f'<a class="btn btn-sm btn-forge" href="{esc(idx_href)}">'
        "Build search index</a> "
        '<span class="forge-support small">(indexes each repo’s static output — <code>website/</code>, '
        "<code>public/</code>, or <code>dist/</code>, or <code>firebase.json</code> "
        "<code>hosting.public</code> — plus <code>/docs/</code>)</span>"
        "</p>"
    )
    notice_html = ""
    if reindex_notice == "started":
        notice_html = (
            '<div class="alert alert-info py-2 mb-3" role="status">'
            "Indexing started in the background. Wait a few seconds, then run your search again."
            "</div>"
        )
    elif reindex_notice == "busy":
        notice_html = (
            '<div class="alert alert-warning py-2 mb-3" role="status">'
            "A reindex is already running. Try again in a moment."
            "</div>"
        )
    elif reindex_notice == "forbidden":
        notice_html = (
            '<div class="alert alert-danger py-2 mb-3" role="status">'
            "Reindex is only available from this machine (loopback), or set "
            "<code>LENSES_ALLOW_ACTIONS=1</code> when binding beyond localhost."
            "</div>"
        )
    if not query.strip():
        results = (
            '<p class="forge-support">Enter keywords below, or build the index first.</p>'
            f"{idx_btn}"
        )
    elif rows:
        results = '<ol class="list-unstyled">' + "".join(rows) + "</ol>"
    else:
        results = (
            '<p class="forge-support mb-2">No matching pages in the index.</p>'
            f"{idx_btn}"
            '<p class="forge-support small mb-0">If you have never indexed, use the button above. '
            "Otherwise try different keywords.</p>"
        )

    q_esc = esc(query)
    scope_esc = esc(str(scope_repo).strip()) if scope_repo else ""
    hidden_repo = (
        f'<input type="hidden" name="repo" value="{scope_esc}" />'
        if scope_repo
        else ""
    )
    scope_chip = ""
    if scope_repo:
        clear_params: dict[str, str] = {"limit": str(int(limit)), "offset": "0"}
        if query.strip():
            clear_params["q"] = query.strip()
        clear_href = "/search?" + urllib.parse.urlencode(clear_params)
        scope_chip = (
            f'<p class="small mb-2">Scoped to workspace child <strong>{scope_esc}</strong> '
            f'(<a href="{esc(clear_href)}">clear</a>).</p>'
        )

    pagination_html = ""
    if query.strip() and total > 0:
        end = min(offset + len(hits), total)
        prev_link = ""
        if offset > 0:
            prev_off = max(0, offset - limit)
            prev_link = (
                f'<a class="btn btn-sm btn-outline-secondary me-2" '
                f'href="/search?{_search_qs({"offset": prev_off})}">Previous</a>'
            )
        next_link = ""
        if offset + limit < total:
            next_link = (
                f'<a class="btn btn-sm btn-outline-secondary" '
                f'href="/search?{_search_qs({"offset": offset + limit})}">Next</a>'
            )
        if prev_link or next_link:
            pagination_html = (
                f'<div class="d-flex flex-wrap align-items-center gap-2 mb-3" role="navigation" '
                f'aria-label="Search results pages">'
                f'<span class="small text-secondary me-auto">'
                f"{offset + 1}–{end} of {total}</span>{prev_link}{next_link}</div>"
            )

    body_inner = f"""<form method="get" action="/search" class="mb-3 d-flex flex-wrap gap-2 align-items-center">
  {hidden_repo}
  <input type="hidden" name="limit" value="{int(limit)}" />
  <label for="lenses-search-q" class="visually-hidden">Search query</label>
  <input type="search" id="lenses-search-q" name="q" value="{q_esc}" class="form-control" style="max-width:28rem" placeholder="Keywords…" />
  <button type="submit" class="btn btn-sm btn-forge">Search</button>
</form>
<p class="forge-support small mb-2">Full-text search over local static HTML in each workspace repo, built lenses docs under <code>/docs/</code>, and optional ingested text. Results rank by relevance (title and headings weigh more than body) and inbound link count.</p>
{scope_chip}
{notice_html}
<h2 class="h6 text-cyan">Results</h2>
{pagination_html}
{results}"""
    bc = lenses_breadcrumb_html(("/", "Overview"), ("/search", "Search"))
    return _wrap_dashboard(
        lenses_repo_root,
        browser_title="Search — lenses",
        nav_active="search",
        page_title="Search",
        breadcrumb_html=bc,
        body_inner=body_inner,
        handbook_url=handbook_url,
        forge_url=forge_url,
        workspace_projects=workspace_project_names_sorted(state),
        current_project=None,
        search_scope_repo=scope_repo,
    )


def page_feature_showcase(
    state: dict[str, Any],
    _registry: dict[str, Any],
    handbook_url: str,
    forge_url: str,
    lenses_repo_root: Path,
) -> str:
    """Classic split scrollytelling feature showcase (same story as Studio ``/studio/feature-showcase``)."""
    body_inner = feature_showcase_body_html()
    bc = lenses_breadcrumb_html(("/", "Overview"), ("/feature-showcase", "Showcase"))
    return _wrap_dashboard(
        lenses_repo_root,
        browser_title="Showcase — lenses",
        nav_active="feature_showcase",
        page_title="Feature showcase",
        breadcrumb_html=bc,
        body_inner=body_inner,
        handbook_url=handbook_url,
        forge_url=forge_url,
        workspace_projects=workspace_project_names_sorted(state),
        current_project=None,
    )


def page_toolset_run(
    _state: dict[str, Any],
    script_name: str,
    workspace_root: Path,
    handbook_url: str,
    forge_url: str,
    lenses_repo_root: Path,
) -> str:
    script_path = resolve_toolset_script(workspace_root, script_name)
    wr_esc = esc(str(workspace_root.resolve()))
    if script_path is None:
        body_inner = f"""<p class="forge-support">Unknown or invalid script <code>{esc(script_name)}</code>. Only <code>*.sh</code> files at the workspace root can be run.</p>
<p><a href="/toolset">← Automation</a></p>"""
        bc = lenses_breadcrumb_html(("/", "Overview"), ("/toolset", "Automation"), ("", script_name))
        return _wrap_dashboard(
            lenses_repo_root,
            browser_title="Automation — lenses",
            nav_active="toolset",
            page_title="Automation",
            breadcrumb_html=bc,
            body_inner=body_inner,
            handbook_url=handbook_url,
            forge_url=forge_url,
            workspace_projects=workspace_project_names_sorted(_state),
            current_project=None,
        )

    detail = shell_script_comment_detail(script_path)
    desc_block = (
        f'<pre class="lenses-toolset-desc small mb-3">{esc(detail)}</pre>'
        if detail
        else '<p class="forge-support">No description in script comments.</p>'
    )
    script_js = json.dumps(script_name)
    body_inner = f"""
<p class="forge-support">Runs on this machine with working directory <code>{wr_esc}</code> (same policy as project git actions: loopback only unless <code>LENSES_ALLOW_GIT_ACTIONS=1</code>).</p>
<h2 class="h5 text-cyan">From script header</h2>
{desc_block}
<div class="d-flex flex-wrap gap-2 mb-2">
  <button type="button" class="btn btn-sm btn-forge" id="lenses-toolset-run-btn">Run script…</button>
  <a class="btn btn-sm btn-outline-secondary" href="/toolset">← All automation scripts</a>
</div>
<pre class="lenses-toolset-console mb-0" id="lenses-toolset-console" aria-live="polite"></pre>
<script>
(function() {{
  var btn = document.getElementById('lenses-toolset-run-btn');
  var out = document.getElementById('lenses-toolset-console');
  var script = {script_js};
  var rootPath = {json.dumps(str(workspace_root.resolve()))};
  if (!btn || !out) return;
  btn.addEventListener('click', function() {{
    var msg = 'Run \"' + script + '\" on this computer?\\n\\nWorking directory:\\n' + rootPath + '\\n\\nThis executes arbitrary shell from your workspace.';
    if (!window.confirm(msg)) return;
    out.textContent = 'Running…';
    btn.disabled = true;
    fetch('/api/toolset/run', {{
      method: 'POST',
      headers: {{ 'Content-Type': 'application/json' }},
      body: JSON.stringify({{ script: script }})
    }}).then(function(r) {{ return r.json(); }}).then(function(j) {{
      btn.disabled = false;
      var t = (j.ok ? 'OK' : 'Exit ' + j.exit_code) + '\\n';
      if (j.stdout) t += j.stdout;
      if (j.stderr) t += (j.stdout ? '\\n' : '') + j.stderr;
      if (j.error) t += (t.length > 2 ? '\\n' : '') + j.error;
      out.textContent = t;
    }}).catch(function(e) {{ btn.disabled = false; out.textContent = String(e); }});
  }});
}})();
</script>
"""
    bc = lenses_breadcrumb_html(
        ("/", "Overview"),
        ("/toolset", "Automation"),
        ("", script_name),
    )
    return _wrap_dashboard(
        lenses_repo_root,
        browser_title=f"{script_name} — Automation — lenses",
        nav_active="toolset",
        page_title=script_name,
        breadcrumb_html=bc,
        body_inner=body_inner,
        handbook_url=handbook_url,
        forge_url=forge_url,
        workspace_projects=workspace_project_names_sorted(_state),
        current_project=None,
    )


def page_sticker_board_hub(
    state: dict[str, Any],
    handbook_url: str,
    forge_url: str,
    lenses_repo_root: Path,
    shared_board_available: bool,
    project_filter: str,
) -> str:
    ws = esc(str(state.get("workspace_root", "")))
    sa = "true" if shared_board_available else "false"
    reg = esc(view_lenses_docs_href("registry-configuration.html"))
    pf = esc(project_filter.strip())
    body_inner = f"""<details class="forge-support small mb-3"><summary class="text-cyan" style="cursor:pointer">Storage &amp; sync</summary>
<p class="mt-2 mb-0">Boards are listed from <code>.lenses-local/sticker-board-registry.json</code>; data under
<code>.lenses-local/sticker-boards/&lt;id&gt;.json</code>. Shared boards also use
<code>.lenses-repo/&lt;login&gt;/sticker-boards/&lt;id&gt;.json</code> plus a local overlay for private stickers.
Workspace: <code>{ws}</code>. <strong>Last write wins</strong> across tabs. POST is loopback-only unless
<code>LENSES_ALLOW_GIT_ACTIONS=1</code>. Optional PNG thumbnails (after save) need <code>playwright</code> + Chromium install and
<code>LENSES_BOARD_PREVIEWS</code> not set to <code>0</code>. Shared mode needs a resolved GitHub login — see
<a href="{reg}">registry</a>.</p></details>
<div id="lenses-sticker-board-hub" class="lenses-sticker-hub-root" data-registry-api="/api/sticker-board-registry"
  data-project-filter="{pf}" data-shared-available="{sa}"></div>
<script src="/__lenses/js/sticker-board-hub.js" defer></script>"""
    bc = lenses_breadcrumb_html(("/", "Overview"), ("", "Forge Stickerboards"))
    return _wrap_dashboard(
        lenses_repo_root,
        browser_title="Forge Stickerboards — lenses",
        nav_active="board",
        page_title="Forge Stickerboards",
        breadcrumb_html=bc,
        body_inner=body_inner,
        handbook_url=handbook_url,
        forge_url=forge_url,
        workspace_projects=workspace_project_names_sorted(state),
        current_project=None,
    )


def page_sticker_board_editor(
    state: dict[str, Any],
    handbook_url: str,
    forge_url: str,
    lenses_repo_root: Path,
    shared_board_available: bool,
    board_id: str,
    board_label: str,
    *,
    thumb_capture: bool = False,
    session_login: str | None = None,
) -> str:
    ws = esc(str(state.get("workspace_root", "")))
    sa = "true" if shared_board_available else "false"
    reg = esc(view_lenses_docs_href("registry-configuration.html"))
    bid = esc(board_id)
    blab = esc(board_label or "Board")
    api = esc(f"/api/sticker-board?board_id={urllib.parse.quote(board_id, safe='')}")
    thumb_attr = ' data-thumb="1"' if thumb_capture else ""
    sess = esc((session_login or "").strip())
    sess_attr = f' data-session-login="{sess}"'
    if thumb_capture:
        intro = ""
    else:
        intro = f"""<p class="forge-support">Board <code>{bid}</code> · Workspace <code>{ws}</code>.
Local vs shared storage is per board; shared stickers need a resolved GitHub login — see <a href="{reg}">registry</a>.</p>
"""
    body_inner = f"""{intro}<div id="lenses-sticker-board" class="lenses-sticker-root" data-api="{api}" data-board-id="{bid}"
  data-board-label="{blab}" data-back-href="/board" data-shared-available="{sa}"{sess_attr}{thumb_attr}></div>
<script src="/__lenses/js/sticker-board.js" defer></script>"""
    bc = lenses_breadcrumb_html(
        ("/board", "Forge Stickerboards"),
        ("", board_label or "Board"),
    )
    body_cls = "lenses-board-thumb-capture" if thumb_capture else ""
    dash_css = board_thumb_capture_extra_css() if thumb_capture else ""
    return _wrap_dashboard(
        lenses_repo_root,
        browser_title=f"{board_label or 'Board'} — Forge Stickerboards — lenses",
        nav_active="board",
        page_title=board_label or "Board",
        breadcrumb_html=bc,
        body_inner=body_inner,
        handbook_url=handbook_url,
        forge_url=forge_url,
        body_extra_class=body_cls,
        dashboard_extra_css=dash_css,
        workspace_projects=workspace_project_names_sorted(state),
        current_project=None,
    )


def _website_top_level_html_path(path: str) -> bool:
    """True if path is a single segment under hosting public (e.g. foo.html), not nested dirs."""
    p = path.replace("\\", "/").strip()
    if not p or "/" in p:
        return False
    pl = p.lower()
    return pl.endswith(".html") or pl.endswith(".htm")


def _website_top_level_page_rows(pages: list[Any]) -> list[dict[str, str]]:
    """Top-level .html paths under hosting public (non-index first, then index)."""
    rows = [
        p
        for p in pages
        if isinstance(p, dict)
        and _website_top_level_html_path(str(p.get("path", "")).strip())
    ]
    non_idx = [
        p
        for p in rows
        if str(p.get("path", "")).lower().strip() not in ("index.html", "")
    ]
    idx_rows = [
        p
        for p in rows
        if str(p.get("path", "")).lower().strip() == "index.html"
    ]
    ordered = non_idx + idx_rows
    return [
        {
            "path": str(p.get("path", "")),
            "label": str(p.get("label", p.get("path", ""))),
        }
        for p in ordered
    ]


def _website_key_pages_grid(
    pages: list[Any], *, max_links: int = 8
) -> list[dict[str, str]]:
    return _website_top_level_page_rows(pages)[:max_links]


def _website_key_page_cell_html(site_name: str, kp: dict[str, str]) -> str:
    rel = kp["path"]
    lab = html.unescape(kp["label"])
    ph = view_local_site_href(site_name, rel)
    return (
        f'<div><a class="text-decoration-none lenses-key-page-link" href="{esc(ph)}">{esc(lab)}</a>'
        f'<span class="d-block forge-support lenses-key-page-path">{esc(rel)}</span></div>'
    )


def _website_index_health_html(html_indexed: int, html_total: int) -> str:
    if html_total <= 0 and html_indexed <= 0:
        return '<span class="lenses-site-meta-muted">—</span>'
    if html_total <= 0:
        return f'<span class="lenses-site-meta-muted">{html_indexed} in index</span>'
    pct = min(100, max(0, int(round(100.0 * html_indexed / html_total))))
    if html_indexed < html_total:
        label = f"{html_indexed} / {html_total}"
    else:
        label = f"{html_total} indexed"
    return (
        f'<div class="lenses-index-health">'
        f'<div class="progress lenses-index-progress" role="progressbar" '
        f'aria-valuenow="{pct}" aria-valuemin="0" aria-valuemax="100" '
        f'aria-label="Index coverage">'
        f'<div class="progress-bar bg-info" style="width: {pct}%"></div></div>'
        f'<span class="lenses-site-meta-muted lenses-index-health-label">{esc(label)}</span>'
        f"</div>"
    )


def _firebase_site_status_chips_html(*, is_git: bool, gi: dict[str, Any]) -> str:
    """Dirty/clean + branch (max ~4 chips total; branch truncated with full title)."""
    chips: list[str] = []
    if is_git:
        dirty = gi.get("dirty")
        chips.append(
            '<span class="badge rounded-pill text-bg-warning">Dirty</span>'
            if dirty
            else '<span class="badge rounded-pill text-bg-success">Clean</span>'
        )
        br = str(gi.get("branch", "")).strip()
        if br:
            br_disp = br if len(br) <= 28 else br[:25].rstrip() + "…"
            chips.append(
                f'<span class="badge rounded-pill text-bg-secondary lenses-site-branch-chip" '
                f'title="{esc(br)}">{esc(br_disp)}</span>'
            )
    if not chips:
        return ""
    return (
        f'<div class="lenses-site-status-chips d-flex flex-wrap align-items-center gap-2 mb-2" '
        f'role="group" aria-label="Repository status">{"".join(chips)}</div>'
    )


def _firebase_site_commit_cell_html(*, is_git: bool, gi: dict[str, Any]) -> str:
    if not is_git:
        return '<span class="lenses-site-meta-muted">—</span>'
    subj_full = str(gi.get("commit_subject", ""))
    subj_show = subj_full
    if len(subj_show) > 56:
        subj_show = subj_show[:53].rstrip() + "…"
    rel_t = _portal_last_update_label(gi)
    subj_title = f' title="{esc(subj_full)}"' if subj_full else ""
    parts: list[str] = [
        f'<span class="lenses-site-meta-muted">{esc(rel_t)}</span>'
    ]
    if subj_show:
        parts.append(
            f'<span class="lenses-site-meta-v lenses-site-meta-truncate"{subj_title}>'
            f"{esc(subj_show)}</span>"
        )
    return f'<div class="d-flex flex-column gap-1 min-w-0">{"".join(parts)}</div>'


def _firebase_site_meta_grid_html(
    *,
    output_cell: str,
    index_cell: str,
    commit_cell: str,
    idx_mtime: str,
) -> str:
    mtime_raw = (idx_mtime or "").strip()
    mtime_title = f' title="{esc(mtime_raw)}"' if len(mtime_raw) > 28 else ""
    mtime_display = esc(mtime_raw) if mtime_raw and mtime_raw != "—" else "—"
    return (
        f'<div class="lenses-site-meta-grid" role="group" aria-label="Site metadata">'
        f'<div><div class="lenses-site-meta-k">Output</div>'
        f'<div class="lenses-site-meta-v">{output_cell}</div></div>'
        f'<div><div class="lenses-site-meta-k">Index</div>'
        f'<div class="lenses-site-meta-v">{index_cell}</div></div>'
        f'<div><div class="lenses-site-meta-k">Last commit</div>'
        f'<div class="lenses-site-meta-v">{commit_cell}</div></div>'
        f'<div><div class="lenses-site-meta-k">Index mtime</div>'
        f'<div class="lenses-site-meta-v lenses-site-meta-truncate"{mtime_title}>'
        f"{mtime_display}</div></div>"
        f"</div>"
    )


def _firebase_site_pages_section_html(*, name: str, page_rows: list[dict[str, str]]) -> str:
    preview_n = 3
    preview_rows = page_rows[:preview_n]
    rest_rows = page_rows[preview_n:]
    preview_cells = "".join(_website_key_page_cell_html(name, kp) for kp in preview_rows)
    preview_block = (
        f'<div class="lenses-key-pages-preview">{preview_cells}</div>'
        if preview_cells
        else ""
    )
    rest_grid = (
        '<div class="lenses-key-pages-grid">'
        + "".join(_website_key_page_cell_html(name, kp) for kp in rest_rows)
        + "</div>"
    )
    n_pages = len(page_rows)
    expand_block = ""
    if rest_rows:
        expand_block = (
            f'<details class="forge-support small lenses-site-details lenses-site-pages-expand">'
            f"<summary>View all {n_pages} top-level pages</summary>"
            f'<div class="mt-2">{rest_grid}</div></details>'
        )
    if not page_rows:
        pages_body = (
            '<p class="forge-support small mb-0">No top-level HTML pages in index yet — run the site '
            "generator, or open <strong>Preview in lenses</strong> for the full tree.</p>"
        )
    else:
        pages_body = preview_block + expand_block
    return (
        f'<div class="lenses-site-pages-block">'
        f'<div class="lenses-pages-heading">Top-level pages</div>{pages_body}</div>'
    )


def _firebase_site_repo_details_html(
    *,
    readme_detail: str,
    html_total: int,
    html_indexed: int,
    idx_mtime: str,
    pub: str,
    fb_site: str,
    rev_html: str,
    subj_full: str,
    br: str,
) -> str:
    details_readme = ""
    if readme_detail:
        details_readme = f'<p class="forge-support small mb-2">{esc(readme_detail)}</p>'
    detail_lines = [
        f'<p class="small forge-support mb-1"><strong>Branch</strong> · {esc(br) if br else "—"}</p>',
        f'<p class="small forge-support mb-1"><strong>HTML files</strong> · {html_total}</p>',
        f'<p class="small forge-support mb-1"><strong>Indexed</strong> · {html_indexed}</p>',
        f'<p class="small forge-support mb-1"><strong>index.html mtime</strong> · {esc(idx_mtime)}</p>',
        f'<p class="small forge-support mb-1"><strong>Hosting public</strong> · <code>{esc(pub)}</code></p>',
    ]
    if fb_site:
        detail_lines.append(
            f'<p class="small forge-support mb-1"><strong>Firebase site</strong> · '
            f"<code>{esc(fb_site)}</code></p>"
        )
    if rev_html:
        subj_esc = esc(subj_full) if subj_full else ""
        detail_lines.append(
            f'<p class="small forge-support mb-2"><strong>Revision</strong> · {rev_html}'
            + (f" · {subj_esc}" if subj_esc else "")
            + "</p>"
        )
    repo_details_body = details_readme + "".join(detail_lines)
    return (
        f'<details class="forge-support small lenses-site-details mb-1">'
        f'<summary>Repository &amp; build details</summary>'
        f'<div class="mt-2 pt-1 border-top border-secondary border-opacity-25">'
        f"{repo_details_body}</div></details>"
    )


def _firebase_site_cta_column_html(
    *,
    browse_href: str,
    preview_root: str,
    ext_btn: str,
    proj_href: str,
    copy_row: str,
) -> str:
    more_inner = (
        f'<a class="btn btn-sm btn-outline-secondary mb-2 d-inline-block" href="{esc(proj_href)}">'
        f"Project dashboard</a>"
        f"{copy_row}"
    )
    more_actions = (
        f'<details class="forge-support small lenses-site-details">'
        f'<summary>More actions</summary><div class="mt-2">{more_inner}</div></details>'
    )
    return (
        f'<div class="d-flex flex-column gap-2 lenses-site-cta-col">'
        f'<a class="btn btn-forge" href="{esc(browse_href)}">Preview in lenses</a>'
        f'<a class="btn btn-sm btn-outline-secondary" href="{esc(preview_root)}">Open local root</a>'
        f"{ext_btn}"
        f"{more_actions}"
        f"</div>"
    )


def _firebase_site_header_row_html(
    *,
    sid: str,
    kicker: str,
    name: str,
    summary_html: str,
    status_chips_html: str,
    cta_block: str,
) -> str:
    return (
        f'<div class="row g-3 align-items-start mb-1">'
        f'<div class="col-12 col-lg-7">'
        f"{status_chips_html}"
        f'<p class="lenses-hero-kicker mb-0">{esc(kicker)}</p>'
        f'<h2 class="text-cyan lenses-site-title" id="lenses-site-title-{esc(sid)}">{esc(name)}</h2>'
        f"{summary_html}"
        f"</div>"
        f'<div class="col-12 col-lg-5">{cta_block}</div>'
        f"</div>"
    )


def _firebase_site_card_html(
    *,
    name: str,
    sid: str,
    search_blob: str,
    kicker: str,
    child: dict[str, Any] | None,
    gi: dict[str, Any],
    fb_site: str,
    pub: str,
    html_total: int,
    html_indexed: int,
    idx_mtime: str,
    pages: list[Any],
    sugg: dict[str, Any],
    readme_short: str,
    readme_detail: str,
    project_urls: dict[str, Any],
) -> str:
    is_git = bool(child and child.get("is_git"))
    status_chips_html = _firebase_site_status_chips_html(is_git=is_git, gi=gi)

    br = str(gi.get("branch", "")) if is_git else ""

    out_bits: list[str] = [f"<code>{esc(pub)}</code>"]
    if fb_site:
        out_bits.append(f'<span class="lenses-site-meta-muted"> · {esc(fb_site)}</span>')
    output_cell = "".join(out_bits)

    index_cell = _website_index_health_html(html_indexed, html_total)
    commit_cell = _firebase_site_commit_cell_html(is_git=is_git, gi=gi)

    summary_line = _portal_first_sentence(readme_short, max_len=140)
    summary_html = ""
    if summary_line:
        summary_html = (
            f'<p class="lenses-site-summary forge-support mb-0" title="{esc(readme_short)}">'
            f"{esc(summary_line)}</p>"
        )

    preview_root = view_local_site_href(name, "index.html")
    browse_href = f"/websites/browse?site={urllib.parse.quote(name, safe='')}"
    proj_href = f"/projects/{urllib.parse.quote(name, safe='')}"
    ext_url = str(project_urls.get(name, "")).strip()

    page_rows = _website_top_level_page_rows(pages)

    copy_btns: list[str] = []
    for key in ("build", "deploy"):
        cmd = str(sugg.get(key, "")).strip()
        if cmd:
            copy_btns.append(
                f'<button type="button" class="btn btn-sm btn-outline-secondary lenses-copy-cmd" '
                f'data-cmd="{esc(cmd)}">Copy {esc(key)}</button>'
            )
    copy_row = (
        '<div class="d-flex flex-wrap gap-1 mt-2">' + "".join(copy_btns) + "</div>"
        if copy_btns
        else ""
    )

    ext_btn = ""
    if ext_url:
        ext_btn = (
            f'<a class="btn btn-sm btn-outline-warning" href="{esc(ext_url)}" '
            f'target="_blank" rel="noopener">Published site</a>'
        )

    origin = str(gi.get("origin_url", "")) if is_git else ""
    head_full = str(gi.get("head_full", "")) if is_git else ""
    head_short = str(gi.get("head_short", "")) if is_git else ""
    subj_full = str(gi.get("commit_subject", "")) if is_git else ""
    c_url = commit_url_for_remote(origin, head_full) if head_full else ""
    rev_html = (
        f'<a href="{esc(c_url)}" target="_blank" rel="noopener">{esc(head_short)}</a>'
        if c_url and head_short
        else esc(head_short)
        if head_short
        else ""
    )

    repo_details = _firebase_site_repo_details_html(
        readme_detail=readme_detail,
        html_total=html_total,
        html_indexed=html_indexed,
        idx_mtime=idx_mtime,
        pub=pub,
        fb_site=fb_site,
        rev_html=rev_html,
        subj_full=subj_full,
        br=br,
    )

    cta_block = _firebase_site_cta_column_html(
        browse_href=browse_href,
        preview_root=preview_root,
        ext_btn=ext_btn,
        proj_href=proj_href,
        copy_row=copy_row,
    )

    header_row = _firebase_site_header_row_html(
        sid=sid,
        kicker=kicker,
        name=name,
        summary_html=summary_html,
        status_chips_html=status_chips_html,
        cta_block=cta_block,
    )

    meta_grid = _firebase_site_meta_grid_html(
        output_cell=output_cell,
        index_cell=index_cell,
        commit_cell=commit_cell,
        idx_mtime=idx_mtime,
    )

    pages_section = _firebase_site_pages_section_html(name=name, page_rows=page_rows)

    return (
        f'<section class="lenses-site-card lenses-site-hero-section forge-card" '
        f'id="lenses-site-{esc(sid)}" aria-labelledby="lenses-site-title-{esc(sid)}" '
        f'data-lenses-search="{esc(search_blob)}">'
        f"{header_row}"
        f"{meta_grid}"
        f"{pages_section}"
        f'<div class="lenses-run-slot mt-2" data-lenses-run-site="{esc(name)}"></div>'
        f"{repo_details}"
        f"</section>"
    )


def page_websites(
    state: dict[str, Any],
    registry: dict[str, Any],
    handbook_url: str,
    forge_url: str,
    lenses_repo_root: Path,
) -> str:
    labels = registry.get("website_labels") or {}
    project_urls = registry.get("project_urls") or {}
    sections: list[str] = []
    for w in state.get("websites") or []:
        name = str(w.get("name", ""))
        if not name:
            continue
        label = str(labels.get(name, "") or "")
        child = _child_by_name(state, name)
        gi = (child or {}).get("git") or {}
        fb_site = str(w.get("firebase_site_id", "") or "")
        pub = str(w.get("hosting_public", "website"))
        html_total = int(w.get("html_total") or 0)
        html_indexed = int(w.get("html_indexed") or 0)
        idx_mtime = _fmt_mtime(w.get("index_html_mtime"))
        pages = w.get("pages") or []
        if not isinstance(pages, list):
            pages = []
        sugg = w.get("suggested_commands") or {}
        if not isinstance(sugg, dict):
            sugg = {}
        repo_path = Path(str((child or {}).get("path", ""))) if child else Path()
        readme_short = _readme_excerpt(repo_path, max_len=280) if repo_path.is_dir() else ""
        readme_detail = _readme_excerpt(repo_path, max_len=1200) if repo_path.is_dir() else ""
        search_parts = [name, label, fb_site, pub, readme_short, readme_detail]
        for p in pages[:80]:
            if isinstance(p, dict):
                search_parts.extend(
                    [str(p.get("label", "")), str(p.get("path", ""))]
                )
        search_blob = " ".join(x for x in search_parts if x).lower()
        sid = re.sub(r"[^a-z0-9_-]+", "-", name.lower()).strip("-") or "site"
        kicker = label if label else "Firebase hosting site"
        gi_d = gi if isinstance(gi, dict) else {}
        pu_d = project_urls if isinstance(project_urls, dict) else {}
        sections.append(
            _firebase_site_card_html(
                name=name,
                sid=sid,
                search_blob=search_blob,
                kicker=kicker,
                child=child,
                gi=gi_d,
                fb_site=fb_site,
                pub=pub,
                html_total=html_total,
                html_indexed=html_indexed,
                idx_mtime=idx_mtime,
                pages=pages,
                sugg=sugg,
                readme_short=readme_short,
                readme_detail=readme_detail,
                project_urls=pu_d,
            )
        )

    stack = (
        '<div class="lenses-sites-stack" id="lenses-sites-grid">' + "".join(sections) + "</div>"
        if sections
        else '<p class="forge-support">No Firebase site repos detected.</p>'
    )
    body_inner = f"""
{_lenses_vertical_hero_styles()}
<p class="forge-support">Built static output is served at <code>/local-site/&lt;repo&gt;/…</code> on this same host (default <strong>127.0.0.1</strong>), so you can use <strong>Preview in lenses</strong> and keep the top navigation visible.</p>
<div class="forge-card p-3 mb-4">
  <div class="row g-2 align-items-start">
    <div class="col-md-6">
      <label class="form-label small text-cyan mb-1" for="lenses-global-q">Search sites &amp; pages</label>
      <input type="search" id="lenses-global-q" class="form-control form-control-sm" placeholder="Filter by name, path, title…" autocomplete="off" />
    </div>
    <div class="col-md-6 d-flex flex-column gap-2">
      <div id="lenses-auth-panel" class="small forge-support mb-0">Checking session…</div>
      <div class="d-none" id="lenses-auth-form">
        <input type="password" id="lenses-gh-token" class="form-control form-control-sm mb-1" placeholder="GitHub PAT (fine-grained or classic)" autocomplete="off" />
        <button type="button" class="btn btn-sm btn-forge" id="lenses-auth-submit">Sign in with PAT</button>
        <button type="button" class="btn btn-sm btn-outline-secondary d-none" id="lenses-auth-logout">Sign out</button>
      </div>
    </div>
  </div>
</div>
{stack}
<script>
(function() {{
  var q = document.getElementById('lenses-global-q');
  if (q) {{
    q.addEventListener('input', function() {{
      var needle = (q.value || '').toLowerCase().trim();
      document.querySelectorAll('.lenses-site-card').forEach(function(card) {{
        var hay = (card.getAttribute('data-lenses-search') || '').toLowerCase();
        card.style.display = !needle || hay.indexOf(needle) >= 0 ? '' : 'none';
      }});
    }});
  }}
  document.querySelectorAll('.lenses-copy-cmd').forEach(function(btn) {{
    btn.setAttribute('data-label', btn.textContent);
    btn.addEventListener('click', function() {{
      var t = btn.getAttribute('data-cmd') || '';
      if (navigator.clipboard && navigator.clipboard.writeText) {{
        navigator.clipboard.writeText(t).then(function() {{
          btn.textContent = 'Copied';
          setTimeout(function() {{ btn.textContent = btn.getAttribute('data-label') || 'Copy'; }}, 1500);
        }});
      }}
    }});
  }});
  var panel = document.getElementById('lenses-auth-panel');
  var form = document.getElementById('lenses-auth-form');
  var tok = document.getElementById('lenses-gh-token');
  var sub = document.getElementById('lenses-auth-submit');
  var out = document.getElementById('lenses-auth-logout');
  function fillRunButtons(status) {{
    document.querySelectorAll('.lenses-run-slot').forEach(function(slot) {{ slot.innerHTML = ''; }});
    if (!status || !status.session_ok || !status.action_keys_by_site) return;
    document.querySelectorAll('.lenses-run-slot').forEach(function(slot) {{
      var site = slot.getAttribute('data-lenses-run-site');
      var keys = status.action_keys_by_site[site];
      if (!keys || !keys.length) return;
      var wrap = document.createElement('div');
      wrap.className = 'd-flex flex-wrap gap-1';
      keys.forEach(function(action) {{
        var b = document.createElement('button');
        b.type = 'button';
        b.className = 'btn btn-sm btn-outline-danger';
        b.textContent = 'Run ' + action;
        b.addEventListener('click', function() {{
          b.disabled = true;
          fetch('/api/actions/run', {{
            method: 'POST',
            headers: {{ 'Content-Type': 'application/json' }},
            body: JSON.stringify({{ site: site, action: action }})
          }}).then(function(r) {{ return r.json(); }}).then(function(j) {{
            var msg = j.ok ? 'OK' : 'Failed';
            if (j.stderr) msg += '\\n' + j.stderr.slice(0, 2000);
            if (j.stdout) msg += '\\n' + j.stdout.slice(0, 2000);
            alert(msg);
            b.disabled = false;
          }}).catch(function(e) {{ alert(String(e)); b.disabled = false; }});
        }});
        wrap.appendChild(b);
      }});
      slot.appendChild(wrap);
    }});
  }}
  function refreshAuth() {{
    fetch('/api/auth/status').then(function(r) {{ return r.json(); }}).then(function(s) {{
      if (!panel || !form) return;
      if (!s.expected_configured) {{
        panel.textContent = 'Allowlisted actions need expected GitHub login (registry, .lenses-repo, or gh).';
        form.classList.add('d-none');
        return;
      }}
      form.classList.remove('d-none');
      if (s.session_ok) {{
        panel.textContent = 'Signed in as ' + (s.session_login || '') + ' (matches ' + (s.expected_login || '') + ').';
        if (sub) sub.classList.add('d-none');
        if (tok) tok.classList.add('d-none');
        if (out) out.classList.remove('d-none');
      }} else {{
        panel.textContent = 'Paste a GitHub PAT for ' + (s.expected_login || '') + ' to run allowlisted builds.';
        if (sub) sub.classList.remove('d-none');
        if (tok) tok.classList.remove('d-none');
        if (out) out.classList.add('d-none');
      }}
      fillRunButtons(s);
    }}).catch(function() {{
      if (panel) panel.textContent = 'Could not load auth status.';
    }});
  }}
  if (sub && tok) {{
    sub.addEventListener('click', function() {{
      var v = (tok.value || '').trim();
      if (!v) return;
      sub.disabled = true;
      fetch('/api/auth/github', {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify({{ token: v }})
      }}).then(function(r) {{ return r.json(); }}).then(function(j) {{
        sub.disabled = false;
        if (j.ok) {{ tok.value = ''; refreshAuth(); }}
        else {{ alert(j.error || 'Auth failed'); }}
      }}).catch(function(e) {{ sub.disabled = false; alert(String(e)); }});
    }});
  }}
  if (out) {{
    out.addEventListener('click', function() {{
      fetch('/api/auth/logout', {{ method: 'POST' }}).then(function() {{ refreshAuth(); }});
    }});
  }}
  refreshAuth();
}})();
</script>
"""
    bc = lenses_breadcrumb_html(("/", "Overview"), ("/websites", "Sites"))
    return _wrap_dashboard(
        lenses_repo_root,
        browser_title="Sites — lenses",
        nav_active="websites",
        page_title="Sites",
        breadcrumb_html=bc,
        body_inner=body_inner,
        handbook_url=handbook_url,
        forge_url=forge_url,
        workspace_projects=workspace_project_names_sorted(state),
        current_project=None,
    )


def page_websites_browse(
    state: dict[str, Any],
    registry: dict[str, Any],
    site_name: str,
    handbook_url: str,
    forge_url: str,
    lenses_repo_root: Path,
) -> str:
    w = _website_by_name(state, site_name)
    if w is None:
        body_inner = "<p>Unknown site.</p>"
        bc = lenses_breadcrumb_html(("/", "Overview"), ("/websites", "Sites"))
        return _wrap_dashboard(
            lenses_repo_root,
            browser_title="Browse — lenses",
            nav_active="websites",
            page_title="Sites",
            breadcrumb_html=bc,
            body_inner=body_inner,
            handbook_url=handbook_url,
            forge_url=forge_url,
            workspace_projects=workspace_project_names_sorted(state),
            current_project=None,
        )
    labels = registry.get("website_labels") or {}
    label = str(labels.get(site_name, "") or "")
    pages = w.get("pages") or []
    if not isinstance(pages, list):
        pages = []
    default_src = local_site_href(site_name, "index.html")
    lis = []
    for p in pages:
        if not isinstance(p, dict):
            continue
        rel = str(p.get("path", ""))
        if not rel:
            continue
        href = local_site_href(site_name, rel)
        lab = str(p.get("label", rel))
        lis.append(
            f'<li class="mb-1"><a class="lenses-chapter-link text-decoration-none" href="#" '
            f'data-href="{esc(href)}">{esc(lab)}</a>'
            f'<span class="d-none lenses-chapter-needle">{esc((lab + " " + rel).lower())}</span></li>'
        )
    list_html = (
        '<ul class="list-unstyled small mb-0" id="lenses-chapter-ul">' + "".join(lis) + "</ul>"
        if lis
        else '<p class="forge-support small">No pages indexed.</p>'
    )
    sub = f" — {label}" if label else ""
    body_inner = f"""
<style>
.lenses-browse-root {{ display: flex; flex-direction: column; min-height: calc(100vh - 8rem); }}
.lenses-browse-toolbar {{ flex: 0 0 auto; display: flex; flex-wrap: wrap; gap: 0.5rem; align-items: center; margin-bottom: 0.75rem; }}
.lenses-browse-split {{ flex: 1 1 auto; display: flex; flex-direction: row; gap: 0.75rem; min-height: 0; }}
.lenses-browse-side {{ flex: 0 0 14rem; max-width: 40%; overflow: auto; border: 1px solid var(--forge-border, #1e293b); border-radius: 8px; padding: 0.5rem; }}
.lenses-browse-frame-wrap {{ flex: 1 1 auto; min-width: 0; min-height: 420px; border: 1px solid var(--forge-border, #1e293b); border-radius: 8px; overflow: hidden; background: #020617; }}
.lenses-browse-frame-wrap iframe {{ width: 100%; height: 100%; min-height: 420px; border: 0; display: block; }}
@media (max-width: 768px) {{
  .lenses-browse-split {{ flex-direction: column; }}
  .lenses-browse-side {{ max-width: none; max-height: 12rem; }}
}}
</style>
<div class="lenses-browse-root">
  <div class="lenses-browse-toolbar forge-support">
    <a href="/websites" class="btn btn-sm btn-outline-secondary">All sites</a>
    <a href="{esc(default_src)}" target="_blank" rel="noopener" class="btn btn-sm btn-outline-info">Open root in new tab</a>
    <input type="search" id="lenses-chapter-q" class="form-control form-control-sm" style="max-width:16rem" placeholder="Filter pages…" autocomplete="off" />
    <span class="small">{esc(site_name)}{esc(sub)}</span>
  </div>
  <div class="lenses-browse-split">
    <aside class="lenses-browse-side">{list_html}</aside>
    <div class="lenses-browse-frame-wrap">
      <iframe id="lenses-site-iframe" title="Site preview" src="{esc(default_src)}"></iframe>
    </div>
  </div>
</div>
<script>
(function() {{
  var iframe = document.getElementById('lenses-site-iframe');
  document.querySelectorAll('.lenses-chapter-link').forEach(function(a) {{
    a.addEventListener('click', function(e) {{
      e.preventDefault();
      var u = a.getAttribute('data-href');
      if (iframe && u) iframe.src = u;
    }});
  }});
  var cq = document.getElementById('lenses-chapter-q');
  if (cq) {{
    cq.addEventListener('input', function() {{
      var needle = (cq.value || '').toLowerCase().trim();
      document.querySelectorAll('#lenses-chapter-ul li').forEach(function(li) {{
        var nd = li.querySelector('.lenses-chapter-needle');
        var hay = nd ? nd.textContent : li.textContent;
        li.style.display = !needle || hay.indexOf(needle) >= 0 ? '' : 'none';
      }});
    }});
  }}
}})();
</script>
"""
    bc = lenses_breadcrumb_html(
        ("/", "Overview"),
        ("/websites", "Sites"),
        ("", f"Preview · {site_name}"),
    )
    return _wrap_dashboard(
        lenses_repo_root,
        browser_title=f"{site_name} preview — lenses",
        nav_active="websites",
        page_title=f"Preview · {site_name}",
        breadcrumb_html=bc,
        body_inner=body_inner,
        handbook_url=handbook_url,
        forge_url=forge_url,
        workspace_projects=workspace_project_names_sorted(state),
        current_project=None,
    )


def wbs_view_link(rel_path: str) -> str:
    q = urllib.parse.urlencode({"p": rel_path})
    return f"/wbs/view?{q}"


def page_wbs(
    state: dict[str, Any],
    handbook_url: str,
    forge_url: str,
    lenses_repo_root: Path,
    workspace_root: Path,
    registry: dict[str, Any],
) -> str:
    proj_rows = build_wbs_project_rows(state)
    table_rows: list[str] = []
    for pr in proj_rows:
        base = resolve_wbs_project_base(workspace_root, registry, pr.key)
        has_md = wbs_md_exists(base) if base is not None else False
        wbs_cells: list[str] = []
        if pr.wbs_entries:
            for w in pr.wbs_entries:
                rp = str(w.get("rel_path", ""))
                link = wbs_view_link(rp)
                wbs_cells.append(
                    f'<div><code class="small">{esc(rp)}</code> '
                    f'<a href="{esc(link)}">View</a></div>'
                )
        else:
            wbs_cells.append('<span class="text-muted">—</span>')
        wbs_col = "".join(wbs_cells) if wbs_cells else '<span class="text-muted">—</span>'

        if pr.key == "__workspace__":
            proj_link = f'<strong>{esc(pr.label)}</strong>'
        else:
            ph = f"/projects/{urllib.parse.quote(pr.key, safe='')}"
            proj_link = f'<a href="{esc(ph)}"><strong>{esc(pr.label)}</strong></a>'
        proj_cell = (
            f'<td>{proj_link}'
            f'<div class="small text-muted lenses-wbs-branch mt-1" data-project-key="{esc(pr.key)}">'
            "…</div></td>"
        )

        if has_md:
            action_cell = '<td><span class="text-muted">WBS.md present</span></td>'
        else:
            action_cell = (
                '<td><div class="wbs-create-panel" data-project-key="'
                + esc(pr.key)
                + '">'
                '<div class="small text-muted lenses-wbs-tags-loading mb-1">Loading release tags…</div>'
                '<div class="d-none lenses-wbs-create-tools d-flex flex-wrap gap-2 align-items-end">'
                '<div><label class="small text-muted mb-0 d-block">Release</label>'
                '<select class="form-select form-select-sm lenses-wbs-tag-select" '
                'style="min-width:10rem" aria-label="Existing release tag">'
                '<option value="">— optional —</option></select></div>'
                '<div><label class="small text-muted mb-0 d-block">New tag</label>'
                '<input type="text" class="form-control form-control-sm lenses-wbs-new-tag" '
                'style="min-width:9rem" placeholder="e.g. v1.0.0" autocomplete="off" /></div>'
                '<div><button type="button" class="btn btn-sm btn-primary lenses-wbs-create-btn">'
                "Create WBS.md</button></div></div>"
                '<p class="small text-danger mb-0 mt-1 lenses-wbs-create-err d-none"></p>'
                "</div></td>"
            )

        table_rows.append(
            f"<tr>{proj_cell}<td>{wbs_col}</td>{action_cell}</tr>"
        )

    table = (
        '<table class="table table-sm table-hover align-middle">'
        "<thead><tr><th>Project</th><th>WBS files</th><th>Actions</th></tr></thead><tbody>"
        + (
            "\n".join(table_rows)
            if table_rows
            else '<tr><td colspan="3">No workspace projects found.</td></tr>'
        )
        + "</tbody></table>"
    )
    wbs_script = """
<script>
(function() {
  fetch("/api/wbs-management").then(function(r) { return r.json(); }).then(function(data) {
    var map = {};
    (data.projects || []).forEach(function(p) { map[p.key] = p; });
    document.querySelectorAll(".lenses-wbs-branch").forEach(function(el) {
      var key = el.getAttribute("data-project-key");
      var proj = map[key];
      if (!proj) {
        el.textContent = "";
        return;
      }
      var br = proj.branch ? "Branch: " + proj.branch : "";
      var git = proj.is_git ? br : "Not a git repo";
      el.textContent = git;
    });
    document.querySelectorAll(".wbs-create-panel").forEach(function(panel) {
      var key = panel.getAttribute("data-project-key");
      var proj = map[key];
      var sel = panel.querySelector(".lenses-wbs-tag-select");
      var load = panel.querySelector(".lenses-wbs-tags-loading");
      var tools = panel.querySelector(".lenses-wbs-create-tools");
      if (!proj || !sel) return;
      (proj.tags || []).forEach(function(t) {
        var o = document.createElement("option");
        o.value = t;
        o.textContent = t;
        sel.appendChild(o);
      });
      if (load) load.classList.add("d-none");
      if (tools) tools.classList.remove("d-none");
      var btn = panel.querySelector(".lenses-wbs-create-btn");
      var err = panel.querySelector(".lenses-wbs-create-err");
      var newInp = panel.querySelector(".lenses-wbs-new-tag");
      if (!btn) return;
      btn.addEventListener("click", function() {
        var baseline = (sel.value || "").trim();
        var newTag = newInp ? (newInp.value || "").trim() : "";
        btn.disabled = true;
        if (err) err.classList.add("d-none");
        fetch("/api/wbs/create", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ project: key, baseline_tag: baseline, new_tag: newTag })
        }).then(function(r) { return r.json().then(function(j) { return { status: r.status, j: j }; }); })
        .then(function(x) {
          btn.disabled = false;
          if (x.j && x.j.ok && x.j.rel_path) {
            window.location.href = "/wbs/view?p=" + encodeURIComponent(x.j.rel_path);
            return;
          }
          if (err) {
            var msg = (x.j && x.j.error) ? String(x.j.error) : "Failed";
            if (x.j && x.j.detail) msg += " — " + String(x.j.detail);
            if (x.j && x.j.tag_stderr) msg += " " + String(x.j.tag_stderr);
            err.textContent = msg;
            err.classList.remove("d-none");
          }
        }).catch(function() {
          btn.disabled = false;
          if (err) {
            err.textContent = "Request failed";
            err.classList.remove("d-none");
          }
        });
      });
    });
  }).catch(function() {
    document.querySelectorAll(".lenses-wbs-tags-loading").forEach(function(el) {
      el.textContent = "Could not load release tags. Refresh the page or check the server log.";
    });
  });
})();
</script>
"""
    body_inner = (
        '<p class="forge-support">All workspace projects. Blueprint-style work breakdown files live under '
        '<code>docs/requirements/</code>. '
        "Use <strong>Release</strong> to record an existing tag in the new file; "
        "<strong>New tag</strong> creates an annotated git tag at the current commit (git repos only).</p>"
        + table
        + wbs_script
    )
    bc = lenses_breadcrumb_html(("/", "Overview"), ("/wbs", "Work Breakdown"))
    return _wrap_dashboard(
        lenses_repo_root,
        browser_title="Work Breakdown — lenses",
        nav_active="wbs",
        page_title="Work Breakdown",
        breadcrumb_html=bc,
        body_inner=body_inner,
        handbook_url=handbook_url,
        forge_url=forge_url,
        workspace_projects=workspace_project_names_sorted(state),
        current_project=None,
    )


def page_wbs_view(
    rel_path: str,
    content: str,
    handbook_url: str,
    forge_url: str,
    lenses_repo_root: Path,
    state: dict[str, Any] | None = None,
) -> str:
    body_inner = f'<pre class="small" style="overflow:auto;white-space:pre-wrap">{esc(content)}</pre>'
    body_inner = (
        f'<p class="forge-support"><code>{esc(rel_path)}</code></p>'
        f'<p><a href="/wbs">← Back to Work Breakdown list</a></p>'
        + body_inner
    )
    bc = lenses_breadcrumb_html(
        ("/", "Overview"),
        ("/wbs", "Work Breakdown"),
        ("", "Work Breakdown file"),
    )
    return _wrap_dashboard(
        lenses_repo_root,
        browser_title="Work Breakdown view — lenses",
        nav_active="wbs",
        page_title="Work Breakdown file",
        breadcrumb_html=bc,
        body_inner=body_inner,
        handbook_url=handbook_url,
        forge_url=forge_url,
        workspace_projects=workspace_project_names_sorted(state),
        current_project=None,
    )


def page_workspace_md_view(
    rel_path: str,
    content: str,
    handbook_url: str,
    forge_url: str,
    lenses_repo_root: Path,
    state: dict[str, Any] | None = None,
) -> str:
    body_inner = f'<pre class="small" style="overflow:auto;white-space:pre-wrap">{esc(content)}</pre>'
    body_inner = (
        f'<p class="forge-support"><code>{esc(rel_path)}</code></p>'
        f'<p><a href="/plan">← Back to Plan</a></p>'
        + body_inner
    )
    bc = lenses_breadcrumb_html(
        ("/", "Overview"),
        ("/plan", "Plan"),
        ("", "Source file"),
    )
    return _wrap_dashboard(
        lenses_repo_root,
        browser_title="Source file — lenses",
        nav_active="plan",
        page_title="Source file",
        breadcrumb_html=bc,
        body_inner=body_inner,
        handbook_url=handbook_url,
        forge_url=forge_url,
        workspace_projects=workspace_project_names_sorted(state),
        current_project=None,
    )


def roadmap_summary_fragment(md_text: str) -> str:
    metrics = extract_chart_metrics(md_text)
    gantt = extract_gantt_model(md_text)
    date_shift = extract_date_shift_model(md_text)
    return roadmap_summary_html(metrics, gantt, date_shift)


def roadmap_date_editor_fragment(
    lenses_repo_root: Path,
    rel_path: str,
    md_text: str,
    include_script: bool = True,
) -> str:
    """Editable Initial/Target date table (kitchensink); optional ``/__ks/js/roadmap-dates.js`` tag."""
    from lenses.ks_layout import _ensure_ks_import_path

    _ensure_ks_import_path(lenses_repo_root)
    try:
        from roadmap_date_editor import (  # type: ignore[import-untyped]
            render_roadmap_date_editor,
            roadmap_date_editor_script_url,
        )
    except ImportError:
        return (
            '<p class="forge-support">Date editor unavailable '
            "(kitchensink <code>roadmap_date_editor</code> not importable).</p>"
        )
    dsm = extract_date_shift_model(md_text)
    rows_raw = dsm.get("rows") if isinstance(dsm, dict) else []
    rows: list[dict[str, Any]] = []
    if isinstance(rows_raw, list):
        for r in rows_raw:
            if isinstance(r, dict):
                rows.append(r)
    html_out = render_roadmap_date_editor(
        rel_path=rel_path,
        rows=rows,
        api_url="/api/roadmap-dates",
    )
    if include_script:
        su = roadmap_date_editor_script_url()
        html_out += (
            f'<script src="{esc(su)}" async data-forge-roadmap-dates-js="1"></script>'
        )
    return html_out


def page_roadmap_timeline_document(md_text: str, rel_path: str) -> str:
    """Full-page scrollable Gantt for iframe / direct open."""
    model = extract_gantt_model(md_text)
    ds_model = extract_date_shift_model(md_text)
    inner = roadmap_gantt_html(model, heading=True)
    ds_html = roadmap_date_shift_html(ds_model, heading=True)
    if inner and ds_html:
        inner = f'<div class="lenses-roadmap-timeline-stack">{inner}{ds_html}</div>'
    elif ds_html and not inner:
        inner = ds_html
    elif not inner and not ds_html:
        inner = (
            '<p class="forge-support">No milestone / epic horizon data and no Initial/Target '
            "dates to draw a timeline. Use milestone tables with <code>M1.x</code> in the "
            "Horizon column and/or optional ISO date columns per "
            "<code>ROADMAP.template.md</code>.</p>"
        )
    title = esc(rel_path)
    head = _roadmap_preview_head_inner()
    return (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n<head>\n'
        '<meta charset="utf-8"/>\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1"/>\n'
        f"<title>Timeline — {title}</title>\n"
        f"{head}"
        "<style>\n"
        ".lenses-roadmap-timeline-doc .lenses-roadmap-gantt-svg { overflow-x: auto; }\n"
        "</style>\n"
        "</head>\n"
        '<body class="lenses-roadmap-preview-doc lenses-roadmap-timeline-doc">\n'
        f"{inner}\n"
        "</body>\n</html>\n"
    )


def _roadmap_preview_head_inner() -> str:
    return (
        '<link rel="stylesheet" href="/__ks/css/forge-theme.css" />\n'
        '<link rel="stylesheet" href="/__ks/css/forgesdlc-theme.css" />\n'
        "<style>\n"
        "body.lenses-roadmap-preview-doc { margin:0; padding:1rem 1.1rem; "
        "background: var(--bs-body-bg, #0f172a); color: var(--bs-body-color, #e2e8f0); }\n"
        ".lenses-roadmap-table-wrap { margin-bottom: 1rem; }\n"
        "</style>\n"
    )


def page_roadmap_preview_document(
    rel_path: str,
    section_id: str,
    md_text: str,
) -> str:
    parsed = parse_roadmap_markdown(md_text)
    sec = find_section(parsed, section_id)
    if sec is None:
        inner = '<p class="forge-support">Section not found.</p>'
    else:
        inner = section_to_html(sec)
    title_src = parsed.doc_title or rel_path
    title = esc(title_src)
    head = _roadmap_preview_head_inner()
    return (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n<head>\n'
        '<meta charset="utf-8"/>\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1"/>\n'
        f"<title>{title}</title>\n"
        f"{head}"
        "</head>\n"
        '<body class="lenses-roadmap-preview-doc">\n'
        f"{inner}\n"
        "</body>\n</html>\n"
    )


def page_timeline(
    state: dict[str, Any],
    handbook_url: str,
    forge_url: str,
    lenses_repo_root: Path,
    query: dict[str, list[str]],
) -> str:
    """Full-width milestone / epic timeline with Plan-compatible selectors."""
    wbs_rows = [w for w in (state.get("wbs") or []) if isinstance(w, dict)]
    rms = [r for r in (state.get("roadmaps") or []) if isinstance(r, dict)]
    valid_wbs = {str(w.get("rel_path", "")) for w in wbs_rows if str(w.get("rel_path", "")).strip()}
    valid_rm = {str(r.get("rel_path", "")) for r in rms if str(r.get("rel_path", "")).strip()}

    repo_q = (query.get("repo") or [""])[0].strip()
    wbs_q = (query.get("wbs_p") or [""])[0].strip()
    rm_q = (query.get("roadmap_p") or [""])[0].strip()

    if wbs_q not in valid_wbs and wbs_rows:
        wbs_q = str(wbs_rows[0].get("rel_path", "")).strip()
    if wbs_q:
        for w in wbs_rows:
            if str(w.get("rel_path", "")).strip() == wbs_q:
                repo_q = str(w.get("repo_hint", "")).strip()
                break
    if not repo_q and wbs_rows:
        repo_q = str(wbs_rows[0].get("repo_hint", "")).strip()
        wbs_q = str(wbs_rows[0].get("rel_path", "")).strip()
    if not repo_q and rms:
        repo_q = str(rms[0].get("repo_hint", "")).strip()

    rms_for_repo = [
        str(r.get("rel_path", "")).strip()
        for r in rms
        if str(r.get("repo_hint", "")).strip() == repo_q
    ]
    if rm_q not in valid_rm or (rms_for_repo and rm_q not in rms_for_repo):
        rm_q = rms_for_repo[0] if rms_for_repo else ""

    workspace_root = Path(str(state.get("workspace_root") or "."))
    wp = workspace_project_names_sorted(state)
    scope = workspace_project_for_repo(repo_q, wp)
    scope_hint = (
        '<p class="small text-muted mb-2 lenses-roadmap-scope-hint">'
        "Each requirements file and roadmap is tagged to one <strong>repository</strong>. "
        "Choose <strong>Repository</strong> first; the other two lists only show paths for that repo "
        "(leave Repository unset to list every path).</p>"
    )

    repo_opts: list[str] = ['<option value="">— Repository —</option>']
    for h in _repo_hints_wbs_then_roadmaps(wbs_rows, rms):
        sel = " selected" if h == repo_q else ""
        repo_opts.append(f'<option value="{esc(h)}"{sel}>{esc(h)}</option>')
    wbs_opts: list[str] = ['<option value="" data-repo="">— WBS file —</option>']
    for w in wbs_rows:
        rp = str(w.get("rel_path", "")).strip()
        if not rp:
            continue
        h = str(w.get("repo_hint", "")).strip()
        sel = " selected" if rp == wbs_q else ""
        wbs_opts.append(
            f'<option value="{esc(rp)}" data-repo="{esc(h)}"{sel}>{esc(rp)}</option>'
        )
    rm_opts: list[str] = [
        '<option value="" data-repo="">— Roadmap (optional) —</option>'
    ]
    for r in rms:
        rp = str(r.get("rel_path", "")).strip()
        if not rp:
            continue
        h = str(r.get("repo_hint", "")).strip()
        sel = " selected" if rp == rm_q else ""
        rm_opts.append(
            f'<option value="{esc(rp)}" data-repo="{esc(h)}"{sel}>{esc(rp)}</option>'
        )

    gantt_block = (
        '<p class="forge-support">Select a repository and a roadmap that contains milestone schedule '
        "and epic horizon tables.</p>"
    )
    metrics_row = ""
    src_link = ""
    if rm_q:
        rpth = workspace_root / rm_q.replace("\\", "/").strip("/")
        if rpth.is_file():
            md = rpth.read_text(encoding="utf-8", errors="replace")
            gm = extract_gantt_model(md)
            gh = roadmap_gantt_html(gm, heading=True)
            dsm = extract_date_shift_model(md)
            dsh = roadmap_date_shift_html(dsm, heading=True)
            if gh or dsh:
                gantt_block = (
                    f'<div class="lenses-timeline-gantt w-100">{gh or ""}{dsh or ""}</div>'
                )
            else:
                gantt_block = (
                    '<p class="forge-support">No Gantt slice or Initial/Target dates found. Use '
                    "milestone tables plus epics with <code>M#.#</code> in the Horizon column, "
                    "and/or optional ISO date columns per <code>ROADMAP.template.md</code>.</p>"
                )
            met = extract_chart_metrics(md)
            hz_html = horizon_badges_html(met.get("horizon_counts") or {})
            epic_pairs: list[tuple[str, float]] = []
            for item in met.get("epic_bars") or []:
                if isinstance(item, (list, tuple)) and len(item) >= 2:
                    try:
                        epic_pairs.append((str(item[0]), float(item[1])))
                    except (TypeError, ValueError):
                        continue
            prog = svg_epic_progress_bars(epic_pairs, width=720) if epic_pairs else ""
            if hz_html or prog:
                metrics_row = (
                    '<div class="lenses-timeline-metrics row g-3 mt-3">'
                    f'<div class="col-12">{hz_html}</div>'
                    f'<div class="col-12">{prog}</div>'
                    "</div>"
                )
            vh = roadmap_timeline_view_link(rm_q)
            src_link = f'<a href="{esc(vh)}">Roadmap source</a>'

    q_plan = (
        f"wbs_p={urllib.parse.quote(wbs_q, safe='')}&repo={urllib.parse.quote(repo_q, safe='')}"
    )
    if rm_q:
        q_plan += f"&roadmap_p={urllib.parse.quote(rm_q, safe='')}"
    plan_link = f"/plan?{q_plan}"
    standalone = (
        f"/roadmaps/timeline?p={urllib.parse.quote(rm_q, safe='')}" if rm_q else ""
    )

    controls = (
        '<div class="row g-2 mb-3 align-items-end">'
        '<div class="col-md-3">'
        '<label for="lenses-timeline-repo" class="form-label small text-muted mb-1">Repository</label>'
        f'<select id="lenses-timeline-repo" class="form-select form-select-sm">{"".join(repo_opts)}</select>'
        "</div>"
        '<div class="col-md-5">'
        '<label for="lenses-timeline-wbs" class="form-label small text-muted mb-1">Requirements / WBS</label>'
        f'<select id="lenses-timeline-wbs" class="form-select form-select-sm">{"".join(wbs_opts)}</select>'
        "</div>"
        '<div class="col-md-4">'
        '<label for="lenses-timeline-roadmap" class="form-label small text-muted mb-1">Roadmap</label>'
        f'<select id="lenses-timeline-roadmap" class="form-select form-select-sm">{"".join(rm_opts)}</select>'
        "</div>"
        "</div>"
    )

    links_line = (
        f'<p class="forge-support small mb-0">'
        f'<a href="{esc(plan_link)}">Open Plan</a>'
        + (f' · <a href="{esc(standalone)}">Standalone timeline</a>' if standalone else "")
        + (f" · {src_link}" if src_link else "")
        + "</p>"
    )

    script = f"<script>\n{FORGE_TIMELINE_SCRIPT}\n</script>"
    body_inner = (
        '<div class="lenses-timeline-shell lenses-dash">'
        '<p class="forge-support">Milestone columns and epic horizon windows. '
        "Click a bar (when an epic id is present) to open that epic in Plan.</p>"
        f"{scope_hint}"
        f"{controls}"
        f"{gantt_block}"
        f"{metrics_row}"
        f"{links_line}"
        f"{script}"
        "</div>"
    )

    extra_css = """
<style>
.lenses-timeline-gantt .lenses-roadmap-gantt-svg { width: 100%; overflow-x: auto; }
.lenses-gantt-bar[data-lenses-node-id] { cursor: pointer; }
</style>
"""

    if scope:
        bc = lenses_breadcrumb_html(
            ("/", "Overview"),
            (f"/projects/{urllib.parse.quote(scope, safe='')}", scope),
            ("", "Timeline"),
        )
    else:
        bc = lenses_breadcrumb_html(("/", "Overview"), ("", "Timeline"))
    return _wrap_dashboard(
        lenses_repo_root,
        browser_title="Timeline — lenses",
        nav_active="timeline",
        page_title="Timeline",
        breadcrumb_html=bc,
        body_inner=body_inner,
        handbook_url=handbook_url,
        forge_url=forge_url,
        dashboard_extra_css=extra_css,
        workspace_projects=wp,
        current_project=scope,
        roadmap_scope_repo=scope,
    )


def page_plan(
    state: dict[str, Any],
    handbook_url: str,
    forge_url: str,
    lenses_repo_root: Path,
    query: dict[str, list[str]] | None = None,
) -> str:
    qs = query or {}
    repo_q = (qs.get("repo") or [""])[0].strip()
    wp = workspace_project_names_sorted(state)
    scope = workspace_project_for_repo(repo_q, wp)
    scope_hint = (
        '<p class="small text-muted mb-2 lenses-roadmap-scope-hint">'
        "Each requirements file and roadmap is tagged to one <strong>repository</strong>. "
        "Choose <strong>Repository</strong> first; the other two lists only show paths for that repo "
        "(leave Repository unset to list every path).</p>"
    )
    wbs_rows = [w for w in (state.get("wbs") or []) if isinstance(w, dict)]
    rms = [r for r in (state.get("roadmaps") or []) if isinstance(r, dict)]
    repo_opts: list[str] = ['<option value="">— Repository —</option>']
    for h in _repo_hints_wbs_then_roadmaps(wbs_rows, rms):
        repo_opts.append(f'<option value="{esc(h)}">{esc(h)}</option>')
    wbs_opts: list[str] = ['<option value="" data-repo="">— WBS file —</option>']
    for w in wbs_rows:
        rp = str(w.get("rel_path", ""))
        if not rp:
            continue
        h = str(w.get("repo_hint", "")).strip()
        wbs_opts.append(
            f'<option value="{esc(rp)}" data-repo="{esc(h)}">{esc(rp)}</option>'
        )
    rm_opts: list[str] = [
        '<option value="" data-repo="">— Roadmap (optional) —</option>'
    ]
    for r in rms:
        rp = str(r.get("rel_path", ""))
        if not rp:
            continue
        h = str(r.get("repo_hint", "")).strip()
        rm_opts.append(
            f'<option value="{esc(rp)}" data-repo="{esc(h)}">{esc(rp)}</option>'
        )

    hb = esc(handbook_url)
    fg = esc(forge_url)

    script = f"<script>\n{FORGE_PLAN_SCRIPT}\n</script>"

    controls = (
        '<div class="row g-2 mb-3 align-items-end">'
        '<div class="col-md-3">'
        '<label for="lenses-plan-repo" class="form-label small text-muted mb-1">Repository</label>'
        f'<select id="lenses-plan-repo" class="form-select form-select-sm">{"".join(repo_opts)}</select>'
        "</div>"
        '<div class="col-md-5">'
        '<label for="lenses-plan-wbs" class="form-label small text-muted mb-1">Requirements / WBS</label>'
        f'<select id="lenses-plan-wbs" class="form-select form-select-sm">{"".join(wbs_opts)}</select>'
        "</div>"
        '<div class="col-md-4">'
        '<label for="lenses-plan-roadmap" class="form-label small text-muted mb-1">Roadmap (optional)</label>'
        f'<select id="lenses-plan-roadmap" class="form-select form-select-sm">{"".join(rm_opts)}</select>'
        "</div>"
        "</div>"
    )

    body_inner = (
        '<div class="lenses-plan-shell lenses-dash">'
        '<p class="forge-support mb-2 lenses-plan-lede"><strong>Roadmap management</strong> — '
        "<strong>Plan</strong> is the default view. Requirements live in <code>docs/requirements/WBS.md</code>; "
        "<code>docs/**/ROADMAP.md</code> is optional horizon context.</p>"
        '<dl class="lenses-plan-glossary row row-cols-1 row-cols-md-2 g-2 mb-3 small">'
        "<dt class=\"col-auto text-muted\">Today</dt><dd class=\"col\"><span class=\"text-body\">Operational view</span> "
        '<span class="forge-support">· Charge</span></dd>'
        "<dt class=\"col-auto text-muted\">Task</dt><dd class=\"col\"><span class=\"text-body\">Unit of work in WBS</span> "
        '<span class="forge-support">· Spark</span></dd>'
        "<dt class=\"col-auto text-muted\">Decision log</dt><dd class=\"col\"><span class=\"text-body\">ADR-style record</span> "
        '<span class="forge-support">· Ember</span></dd>'
        "<dt class=\"col-auto text-muted\">Discipline session</dt><dd class=\"col\">"
        '<span class="text-body\">Facilitated session</span> <span class="forge-support">· Versona</span></dd>'
        "</dl>"
        f"{scope_hint}"
        f"{controls}"
        '<ul class="nav nav-tabs mb-3 lenses-plan-main-tabs" role="tablist" aria-label="Plan sections">'
        '<li class="nav-item" role="presentation">'
        '<button type="button" class="nav-link active" id="lenses-plan-tab-plan" role="tab" '
        'aria-selected="true" aria-controls="lenses-plan-panel-plan" tabindex="0">Plan</button></li>'
        '<li class="nav-item" role="presentation">'
        '<button type="button" class="nav-link" id="lenses-plan-tab-today" role="tab" '
        'aria-selected="false" aria-controls="lenses-plan-panel-today" tabindex="-1">Today '
        '<span class="forge-support fw-normal">· Charge</span></button></li>'
        '<li class="nav-item" role="presentation">'
        '<button type="button" class="nav-link" id="lenses-plan-tab-source" role="tab" '
        'aria-selected="false" aria-controls="lenses-plan-panel-source" tabindex="-1">Source '
        '<span class="forge-support fw-normal">· Roadmap</span></button></li>'
        "</ul>"
        '<div id="lenses-plan-panel-plan" role="tabpanel" aria-labelledby="lenses-plan-tab-plan">'
        '<details class="mb-2 lenses-plan-summary-details" id="lenses-plan-summary-details">'
        '<summary class="small text-muted cursor-pointer">Roadmap summary (collapsible)</summary>'
        '<div id="lenses-plan-summary" class="card p-2 mt-2 lenses-roadmap-summary-card"></div>'
        "</details>"
        '<div class="row g-2 mb-2 align-items-center">'
        '<div class="col-md-6 col-lg-5">'
        '<label for="lenses-plan-search" class="visually-hidden">Filter work tree</label>'
        '<input type="search" id="lenses-plan-search" class="form-control form-control-sm" '
        'placeholder="Filter by id, title, status, phase, blockers, docs…" autocomplete="off"/>'
        "</div>"
        '<div class="col-md-6 col-lg-7 text-md-end">'
        '<span class="small text-muted me-1">Quick filters:</span>'
        '<button type="button" class="btn btn-sm btn-outline-secondary me-1" id="lenses-filter-blocked" '
        'title="Stories with blocked sparks">Blocked</button>'
        '<button type="button" class="btn btn-sm btn-outline-secondary me-1" id="lenses-filter-decisions" '
        'title="Stories with Ember decisions">Ember</button>'
        '<button type="button" class="btn btn-sm btn-outline-secondary" id="lenses-filter-versona" '
        'title="Stories with Versona sessions">Versona</button>'
        "</div>"
        "</div>"
        '<div id="lenses-plan-explorer-row" class="lenses-plan-explorer row g-0 border border-secondary rounded overflow-hidden">'
        '<div class="lenses-plan-pane lenses-plan-pane-left col-12 col-lg-3 border-bottom border-lg-0 '
        'border-lg-end border-secondary p-2">'
        '<h3 class="h6 text-cyan mb-2">Work hierarchy</h3>'
        '<div id="lenses-plan-explorer-tree" class="lenses-plan-tree" aria-label="Work hierarchy"></div>'
        '<div id="lenses-plan-extra-groups" class="mt-2 small"></div>'
        "</div>"
        '<div class="lenses-plan-pane lenses-plan-pane-center col-12 col-lg-5 border-bottom border-lg-0 '
        'border-lg-end border-secondary p-3 lenses-plan-center-pane">'
        '<h3 class="h6 text-cyan mb-2">Overview</h3>'
        '<div id="lenses-plan-explorer-center"></div>'
        "</div>"
        '<div class="lenses-plan-pane lenses-plan-pane-right col-12 col-lg-4 p-3 bg-body-secondary" '
        'id="lenses-plan-pane-right">'
        '<div class="d-flex align-items-start justify-content-between gap-2 mb-2">'
        '<h3 class="h6 text-cyan mb-0">Detail <span class="forge-support fw-normal small">· rail</span></h3>'
        '<button type="button" class="btn btn-sm btn-outline-secondary lenses-plan-rail-toggle" '
        'id="lenses-plan-rail-toggle" aria-expanded="true" aria-controls="lenses-plan-pane-right" '
        'title="Show or hide the detail column">Hide detail</button>'
        "</div>"
        '<div id="lenses-plan-explorer-rail" class="lenses-plan-explorer-rail-host"></div>'
        "</div>"
        "</div>"
        "</div>"
        '<div id="lenses-plan-panel-source" class="d-none" role="tabpanel" aria-labelledby="lenses-plan-tab-source">'
        '<p class="forge-support small">Raw <code>ROADMAP.md</code> preview (section from outline).</p>'
        '<div class="card lenses-roadmap-preview-window p-0 border border-secondary">'
        '<iframe id="lenses-plan-source-frame" class="w-100 lenses-roadmap-preview-frame" '
        'title="Roadmap source" style="min-height:min(70vh,36rem);border:0"></iframe>'
        "</div>"
        "</div>"
        '<div id="lenses-plan-panel-today" class="d-none" role="tabpanel" aria-labelledby="lenses-plan-tab-today">'
        '<p class="forge-support small mb-2 lenses-plan-today-lede">Operational view from <code>forge/charge.md</code> '
        'plus WBS context. <span class="text-muted">Primary labels in body text; Forge names secondary.</span></p>'
        '<div class="row g-2 mb-3 align-items-end">'
        '<div class="col-md-4 col-lg-3">'
        '<label for="lenses-today-phase" class="form-label small text-muted mb-1">Phase prefix</label>'
        '<select id="lenses-today-phase" class="form-select form-select-sm">'
        '<option value="">All</option>'
        "</select>"
        "</div>"
        '<div class="col-md-8 col-lg-9 text-lg-end">'
        '<span class="small text-muted me-1">Show:</span>'
        '<button type="button" class="btn btn-sm btn-outline-secondary me-1 lenses-today-chip" '
        'id="lenses-today-filter-blocked" data-today-filter="blocked">Blocked</button>'
        '<button type="button" class="btn btn-sm btn-outline-secondary me-1 lenses-today-chip" '
        'id="lenses-today-filter-banked" data-today-filter="banked">Banked</button>'
        '<button type="button" class="btn btn-sm btn-outline-secondary lenses-today-chip" '
        'id="lenses-today-filter-done" data-today-filter="done">Done / resolved</button>'
        "</div>"
        "</div>"
        '<div id="lenses-today-content" class="lenses-today-content small"></div>'
        "</div>"
        f"{script}"
        "</div>"
    )

    extra_css = """
<style>
.lenses-plan-lede { line-height: 1.5; }
.lenses-plan-glossary dd { margin-bottom: 0; }
.lenses-plan-glossary dt { font-weight: 500; }
.lenses-plan-main-tabs .nav-link:focus-visible {
  outline: 2px solid rgba(6,182,212,0.55);
  outline-offset: 2px;
}
.lenses-plan-rail-toggle:focus-visible {
  outline: 2px solid rgba(6,182,212,0.55);
  outline-offset: 2px;
}
.lenses-plan-tree { max-height: min(55vh, 28rem); overflow-y: auto; outline: none; }
.lenses-plan-tree:focus-visible { outline: 2px solid rgba(6,182,212,0.5); outline-offset: 2px; }
.lenses-tree-item { cursor: pointer; font-size: 0.875rem; line-height: 1.45; }
.lenses-tree-item-active {
  background: rgba(6,182,212,0.14);
  box-shadow: inset 0 0 0 1px rgba(6,182,212,0.4);
}
.lenses-tree-item:focus-visible { outline: 2px solid rgba(6,182,212,0.65); outline-offset: 1px; }
.lenses-plan-center-pane { min-height: min(52vh, 26rem); overflow-y: auto; }
.lenses-plan-slot-body { line-height: 1.5; }
.lenses-plan-explorer-rail-host { max-height: min(70vh, 36rem); overflow-y: auto; }
.lenses-roadmap-summary-card { min-height: 2.25rem; }
.lenses-roadmap-preview-window { background: var(--bs-body-bg, #0f172a); }
.lenses-plan-main-tabs.nav-tabs .nav-link { cursor: pointer; background: transparent; border: none; }
.lenses-plan-main-tabs.nav-tabs .nav-link.active { color: var(--bs-cyan, #06b6d4); border-bottom: 2px solid rgba(6,182,212,0.65); }
.lenses-story-cockpit .nav-tabs .nav-link:focus-visible { outline: 2px solid rgba(6,182,212,0.55); outline-offset: 2px; }
.lenses-plan-summary-details > summary { list-style: none; }
.lenses-plan-summary-details > summary::-webkit-details-marker { display: none; }
#lenses-filter-blocked.active, #lenses-filter-decisions.active, #lenses-filter-versona.active {
  background: rgba(6,182,212,0.16);
  border-color: rgba(6,182,212,0.5);
}
.lenses-today-chip.active {
  background: rgba(6,182,212,0.16);
  border-color: rgba(6,182,212,0.5);
}
.lenses-today-content table { font-size: 0.875rem; }
.lenses-today-section-title { font-size: 0.95rem; font-weight: 600; letter-spacing: 0.02em; }
.lenses-plan-today-lede { line-height: 1.45; }
.lenses-plan-pane-right .forge-support { opacity: 0.92; }
.lenses-plan-story-mode .lenses-plan-pane-right { display: none !important; }
.lenses-plan-story-mode .lenses-plan-pane-center { flex: 1 1 auto; max-width: 100%; }
.lenses-plan-explorer-row.lenses-plan-rail-collapsed .lenses-plan-pane-right { display: none !important; }
.lenses-plan-explorer-row.lenses-plan-rail-collapsed:not(.lenses-plan-story-mode) .lenses-plan-pane-center {
  flex: 1 1 auto;
  max-width: 100%;
}
.lenses-plan-empty-title { font-size: 0.95rem; font-weight: 600; margin-bottom: 0.25rem; }
</style>
"""

    if scope:
        bc = lenses_breadcrumb_html(
            ("/", "Overview"),
            (f"/projects/{urllib.parse.quote(scope, safe='')}", scope),
            ("", "Plan"),
        )
    else:
        bc = lenses_breadcrumb_html(("/", "Overview"), ("", "Plan"))
    return _wrap_dashboard(
        lenses_repo_root,
        browser_title="Plan — lenses",
        nav_active="plan",
        page_title="Plan",
        breadcrumb_html=bc,
        body_inner=body_inner,
        handbook_url=handbook_url,
        forge_url=forge_url,
        dashboard_extra_css=extra_css,
        workspace_projects=wp,
        current_project=scope,
        roadmap_scope_repo=scope,
    )
