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


