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
from lenses.ks_layout import board_thumb_capture_extra_css, lenses_showcase_page
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
from lenses.roadmap_charts import KS_ROADMAP_TEMPLATE, ks_diagram_img, roadmap_summary_html
from lenses.roadmap_outline import (
    extract_chart_metrics,
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
    for c in checks:
        if not isinstance(c, dict):
            continue
        st = str(c.get("status", ""))
        icon = "✓" if st == "pass" else ("◌" if st in ("na", "skipped") else "!")
        row_cls = ""
        if st == "warn":
            row_cls = " class=\"table-warning\""
        elif st in ("na", "skipped"):
            row_cls = " class=\"table-secondary\""
        rows.append(
            f"<tr{row_cls}>"
            f"<td>{esc(icon)}</td>"
            f"<td>{esc(str(c.get('label', '')))}</td>"
            f"<td class=\"small\">{esc(str(c.get('detail', '')))}</td>"
            f"</tr>"
        )
    tbl = (
        '<table class="table table-sm table-bordered mb-2">'
        '<thead><tr><th scope="col"></th><th scope="col">Check</th><th scope="col">Detail</th></tr></thead>'
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
    return (
        f'<section class="lenses-site-hero-section forge-card" '
        f'aria-labelledby="lenses-proj-std-{esc(sid)}">'
        f'<h3 class="h6 text-cyan mb-2" id="lenses-proj-std-{esc(sid)}">'
        f"Standards and agentic hygiene</h3>"
        f'<p class="forge-support small mb-2">'
        f'<span class="badge rounded-pill {tier_badge} me-2">{esc(tier)} · {score}/100</span>'
        f"{esc(summary)} "
        f'<a href="{esc(bp_link)}" target="_blank" rel="noopener">Blueprint: agentic coding standards</a>.'
        f"</p>"
        f"{tbl}"
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
  border-left: 4px solid var(--bs-cyan, #06b6d4);
  background: linear-gradient(105deg, rgba(6, 182, 212, 0.07) 0%, transparent 45%);
  border-radius: 10px;
  padding: 1.25rem 1.35rem;
  margin-bottom: 1.5rem;
}
.lenses-site-hero-section .lenses-hero-kicker {
  font-size: 0.72rem;
  letter-spacing: 0.07em;
  text-transform: uppercase;
  color: var(--forge-text-4, #64748b);
  font-weight: 600;
}
.lenses-site-hero-section h2 { font-size: 1.35rem; margin: 0.35rem 0 0.25rem; }
.lenses-site-stat-strip { display: flex; flex-wrap: wrap; gap: 0.45rem; margin: 0.85rem 0 0.25rem; align-items: center; }
.lenses-site-stat-strip .badge { font-weight: 500; }
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
            f'<a href="{esc(local_site_href(name, ""))}">Preview</a>'
        )
    if handbook_quick_links:
        for hb_label, hb_rel in handbook_quick_links:
            link_parts.append(
                f'<a href="{esc(local_site_href(name, hb_rel))}" '
                f'target="_blank" rel="noopener">{esc(hb_label)}</a>'
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


def lenses_sidebar_html(nav_active: str, handbook_url: str, forge_url: str) -> str:
    items = [
        ("overview", "/", "Overview"),
        ("projects", "/projects", "Projects"),
        ("tutorials", "/tutorials", "Tutorials"),
        ("toolset", "/toolset", "Toolset"),
        ("websites", "/websites", "Websites"),
        ("board", "/board", "Sticker board"),
        ("wbs", "/wbs", "WBS"),
        ("roadmaps", "/roadmaps", "Roadmaps"),
    ]
    lines = [
        '<p class="nav-section-label">Workspace</p>',
        '<div class="nav-rail">',
    ]
    for key, href, label in items:
        cls = " active" if nav_active == key else ""
        lines.append(
            f'<a class="doc-sidebar-link{cls}" href="{esc(href)}">{esc(label)}</a>'
        )
    lines.append("</div>")
    lines.append('<p class="nav-section-label">Reference</p>')
    lines.append('<div class="nav-rail">')
    lines.append(
        '<a class="doc-sidebar-link" href="/docs/index.html">Lenses docs</a>'
    )
    lines.append("</div>")
    lines.append('<p class="nav-section-label">Published</p>')
    lines.append('<div class="nav-rail">')
    lines.append(
        f'<a class="doc-sidebar-link" href="{esc(handbook_url)}" target="_blank" rel="noopener">Handbook</a>'
    )
    lines.append(
        f'<a class="doc-sidebar-link" href="{esc(forge_url)}" target="_blank" rel="noopener">Forge</a>'
    )
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


def nav_bar(
    active: str,
    handbook_url: str,
    forge_url: str,
) -> str:
    items = [
        ("overview", "/", "Overview"),
        ("projects", "/projects", "Projects"),
        ("tutorials", "/tutorials", "Tutorials"),
        ("toolset", "/toolset", "Toolset"),
        ("websites", "/websites", "Websites"),
        ("board", "/board", "Sticker board"),
        ("wbs", "/wbs", "WBS"),
        ("roadmaps", "/roadmaps", "Roadmaps"),
    ]
    links = []
    for key, href, label in items:
        cls = " active" if active == key else ""
        links.append(
            f'<a class="lenses-nav-link{cls}" href="{esc(href)}">{esc(label)}</a>'
        )
    links.append(
        f'<a class="lenses-nav-link lenses-nav-docs" href="/docs/index.html">Lenses docs</a>'
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
    .lenses-overview-lede {{ font-size: 1.05rem; line-height: 1.55; }}
    .lenses-overview-kpi-row {{ display: flex; flex-wrap: wrap; gap: 0.75rem; }}
    .lenses-overview-kpi-row > div {{ flex: 1 1 10rem; min-width: 9rem; }}
    .lenses-overview-kpi {{
      display: block; border: 1px solid var(--border); border-radius: 8px;
      padding: 0.85rem; text-decoration: none; color: inherit;
    }}
    .lenses-overview-kpi:hover {{ border-color: var(--accent); }}
    .lenses-overview-main {{ display: flex; flex-wrap: wrap; gap: 1.5rem; }}
    .lenses-overview-main > div:first-child {{ flex: 2 1 20rem; min-width: 0; }}
    .lenses-overview-main > div:last-child {{ flex: 1 1 14rem; }}
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
  </style>
</head>
<body>
{nav_bar(nav_active, handbook_url, forge_url)}
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
) -> str:
    sidebar = lenses_sidebar_html(nav_active, handbook_url, forge_url)
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
        dashboard_extra_css=dashboard_extra_css,
    )
    if ks is not None:
        return ks
    body = f"{breadcrumb_html}\n{body_inner}\n{footer}"
    return layout_page(browser_title, nav_active, body, handbook_url, forge_url)


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
                secondary_cta_href="/docs/index.html",
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
            '<a href="/docs/index.html">Lenses docs</a> · '
            '<a href="/tutorials">Tutorials</a>'
            "</p>"
            "</div>"
        )

    def kpi_tile(href: str, label: str, value: str, cta: str) -> str:
        return (
            f'<div class="col">'
            f'<a class="forge-card breathe-link d-block h-100 text-decoration-none lenses-overview-kpi" href="{esc(href)}">'
            f'<p class="forge-support small text-uppercase mb-1">{esc(label)}</p>'
            f'<p class="h3 mb-2">{value}</p>'
            f'<p class="small text-cyan mb-0">{esc(cta)}</p>'
            f"</a></div>"
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
        '<div class="row row-cols-2 row-cols-md-3 row-cols-xl-6 g-3 mb-4 lenses-overview-kpi-row">'
        + kpi_tile("/projects", "Top-level folders", esc(str(n_children)), "Open Projects →")
        + kpi_tile("/websites", "Firebase sites", esc(str(n_sites)), "Websites →")
        + kpi_tile("/wbs", "WBS files", esc(str(n_wbs)), "WBS →")
        + kpi_tile("/roadmaps", "Roadmaps", esc(str(n_roadmaps)), "Roadmaps →")
        + kpi_tile("/toolset", "Root scripts", esc(str(n_scripts)), "Toolset →")
        + kpi_tile(
            "/projects",
            "Approx. lines (sum)",
            esc(f"~{total_loc_sum:,}"),
            "Newlines, capped per repo →",
        )
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
        + analytics_block
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
        '<p class="forge-support mb-0 mt-4">Reload any page to refresh discovery '
        "(no server-side cache).</p>"
    )

    body_inner = (
        '<div class="lenses-overview lenses-dash">'
        f'<div class="lenses-overview-hero-wrap mb-2">{hero_html}</div>'
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
            href = local_site_href(cn, b.local_site_rel)
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
                f'<a class="btn btn-sm btn-forge" href="{esc(href)}" '
                f'target="_blank" rel="noopener">{esc(open_label)}</a>'
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
            '<a href="/docs/index.html">Lenses docs</a> for setup and the HTTP API reference.</p>'
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
    has_wbs = bool(wbs_entries)
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
    preview_root = ""
    if is_site:
        browse_href = f"/websites/browse?site={urllib.parse.quote(project_name, safe='')}"
        preview_root = local_site_href(project_name, "index.html")

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
            href = local_site_href(project_name, b.local_site_rel)
            doc_bits.append(
                f'{esc(b.label_default)}: <a href="{esc(href)}" target="_blank" rel="noopener">'
                f"{esc(lbl)}</a>"
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
        dh = local_site_href(project_name, "docs/index.html")
        doc_extra = (
            f'<p class="mb-0 mt-1 forge-support">Docs site: '
            f'<a href="{esc(dh)}" target="_blank" rel="noopener">docs/index.html</a></p>'
        )
    doc_inner = f'<div class="forge-support small">{doc_tutorial}</div>{doc_extra}'

    if is_site:
        web_inner = (
            f'<p class="mb-0 forge-support small">Firebase Hosting child. '
            f'<a href="{esc(browse_href)}">Preview in lenses</a> · '
            f'<a href="{esc(preview_root)}" target="_blank" rel="noopener">'
            f"Open local site root</a></p>"
        )
    else:
        web_inner = (
            '<p class="mb-0 forge-support small text-body-secondary">'
            "Not a Firebase Hosting child in this workspace</p>"
        )

    nwbs = len(wbs_entries)
    if has_wbs:
        plan_inner = (
            f'<p class="mb-0 forge-support small">{nwbs} requirement file(s) — '
            f'<a href="/wbs">View WBS</a></p>'
        )
    else:
        plan_inner = (
            '<p class="mb-0 forge-support small text-body-secondary">'
            "No WBS rooted here</p>"
        )

    if board_n:
        sticker_lead = f"{board_n} board(s) · "
    else:
        sticker_lead = '<span class="text-body-secondary">None yet</span> · '
    sticker_inner = (
        f'<p class="mb-0 forge-support small">{sticker_lead}'
        f'<a href="{esc(sticker_hub)}">Sticker board hub</a></p>'
    )

    docs_site_href = (
        local_site_href(project_name, "docs/index.html") if docs_index_exists else ""
    )
    hero_quick_parts: list[str] = []
    for b in handbooks:
        hb_lbl = _handbook_display_label(b, wk_pages, is_site)
        hb_href = local_site_href(project_name, b.local_site_rel)
        hero_quick_parts.append(
            f'<a class="btn btn-sm btn-outline-secondary" href="{esc(hb_href)}" '
            f'target="_blank" rel="noopener">{esc(hb_lbl)}</a>'
        )
    if is_site:
        hero_quick_parts.append(
            f'<a class="btn btn-sm btn-forge" href="{esc(browse_href)}">Preview in lenses</a>'
        )
        hero_quick_parts.append(
            f'<a class="btn btn-sm btn-outline-info" href="{esc(preview_root)}" '
            f'target="_blank" rel="noopener">Open local site</a>'
        )
    if external_url:
        hero_quick_parts.append(
            f'<a class="btn btn-sm btn-outline-warning" href="{esc(external_url)}" '
            f'target="_blank" rel="noopener">Project site</a>'
        )
    if docs_site_href:
        hero_quick_parts.append(
            f'<a class="btn btn-sm btn-outline-secondary" href="{esc(docs_site_href)}" '
            f'target="_blank" rel="noopener">Docs site</a>'
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
            f'<a class="btn btn-sm btn-outline-info" href="{esc(preview_root)}" '
            f'target="_blank" rel="noopener">Open local site root</a>'
        )
        grp_ship.append(
            '<a class="btn btn-sm btn-outline-secondary" href="/websites">Firebase sites list</a>'
        )

    grp_learn: list[str] = []
    for b in handbooks:
        hb_lbl = _handbook_display_label(b, wk_pages, is_site)
        hb_href = local_site_href(project_name, b.local_site_rel)
        grp_learn.append(
            f'<a class="btn btn-sm btn-outline-secondary" href="{esc(hb_href)}" '
            f'target="_blank" rel="noopener">{esc(hb_lbl)}</a>'
        )
    if has_wbs:
        grp_learn.append('<a class="btn btn-sm btn-outline-secondary" href="/wbs">WBS</a>')
    grp_learn.append(
        f'<a class="btn btn-sm btn-outline-secondary" href="{esc(sticker_hub)}">Sticker board</a>'
    )

    strategy_href = f"/projects/{urllib.parse.quote(project_name, safe='')}/strategy"
    grp_nav = [
        f'<a class="btn btn-sm btn-outline-secondary" href="{esc(strategy_href)}">'
        f"Repo &amp; strategy</a>",
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
    bc = lenses_breadcrumb_html(("/", "Overview"), ("/toolset", "Toolset"))
    return _wrap_dashboard(
        lenses_repo_root,
        browser_title="Toolset — lenses",
        nav_active="toolset",
        page_title="Toolset",
        breadcrumb_html=bc,
        body_inner=body_inner,
        handbook_url=handbook_url,
        forge_url=forge_url,
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
<p><a href="/toolset">← Toolset</a></p>"""
        bc = lenses_breadcrumb_html(("/", "Overview"), ("/toolset", "Toolset"), ("", script_name))
        return _wrap_dashboard(
            lenses_repo_root,
            browser_title="Toolset — lenses",
            nav_active="toolset",
            page_title="Toolset",
            breadcrumb_html=bc,
            body_inner=body_inner,
            handbook_url=handbook_url,
            forge_url=forge_url,
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
  <a class="btn btn-sm btn-outline-secondary" href="/toolset">← All toolset scripts</a>
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
        ("/toolset", "Toolset"),
        ("", script_name),
    )
    return _wrap_dashboard(
        lenses_repo_root,
        browser_title=f"{script_name} — Toolset — lenses",
        nav_active="toolset",
        page_title=script_name,
        breadcrumb_html=bc,
        body_inner=body_inner,
        handbook_url=handbook_url,
        forge_url=forge_url,
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
    reg = esc("/docs/registry-configuration.html")
    pf = esc(project_filter.strip())
    body_inner = f"""<details class="forge-support small mb-3"><summary class="text-cyan" style="cursor:pointer">Storage &amp; sync</summary>
<p class="mt-2 mb-0">Boards are listed from <code>.lenses-local/sticker-board-registry.json</code>; data under
<code>.lenses-local/sticker-boards/&lt;id&gt;.json</code>. Shared boards also use
<code>.lenses-repo/&lt;login&gt;/sticker-boards/&lt;id&gt;.json</code> plus a local overlay for private stickers.
Workspace: <code>{ws}</code>. <strong>Last write wins</strong> across tabs. POST is loopback-only unless
<code>LENSES_ALLOW_GIT_ACTIONS=1</code>. Optional PNG thumbnails (after save) need <code>html2image</code> + Chromium and
<code>LENSES_BOARD_PREVIEWS</code> not set to <code>0</code>. Shared mode needs a resolved GitHub login — see
<a href="{reg}">registry</a>.</p></details>
<div id="lenses-sticker-board-hub" class="lenses-sticker-hub-root" data-registry-api="/api/sticker-board-registry"
  data-project-filter="{pf}" data-shared-available="{sa}"></div>
<script src="/__lenses/js/sticker-board-hub.js" defer></script>"""
    bc = lenses_breadcrumb_html(("/", "Overview"), ("", "Stickerboardefo"))
    return _wrap_dashboard(
        lenses_repo_root,
        browser_title="Stickerboardefo — lenses",
        nav_active="board",
        page_title="Stickerboardefo",
        breadcrumb_html=bc,
        body_inner=body_inner,
        handbook_url=handbook_url,
        forge_url=forge_url,
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
) -> str:
    ws = esc(str(state.get("workspace_root", "")))
    sa = "true" if shared_board_available else "false"
    reg = esc("/docs/registry-configuration.html")
    bid = esc(board_id)
    blab = esc(board_label or "Board")
    api = esc(f"/api/sticker-board?board_id={urllib.parse.quote(board_id, safe='')}")
    thumb_attr = ' data-thumb="1"' if thumb_capture else ""
    if thumb_capture:
        intro = ""
    else:
        intro = f"""<p class="forge-support">Board <code>{bid}</code> · Workspace <code>{ws}</code>.
Local vs shared storage is per board; shared stickers need a resolved GitHub login — see <a href="{reg}">registry</a>.</p>
"""
    body_inner = f"""{intro}<div id="lenses-sticker-board" class="lenses-sticker-root" data-api="{api}" data-board-id="{bid}"
  data-board-label="{blab}" data-back-href="/board" data-shared-available="{sa}"{thumb_attr}></div>
<script src="/__lenses/js/sticker-board.js" defer></script>"""
    bc = lenses_breadcrumb_html(
        ("/board", "Stickerboardefo"),
        ("", board_label or "Board"),
    )
    body_cls = "lenses-board-thumb-capture" if thumb_capture else ""
    dash_css = board_thumb_capture_extra_css() if thumb_capture else ""
    return _wrap_dashboard(
        lenses_repo_root,
        browser_title=f"{board_label or 'Board'} — Stickerboardefo — lenses",
        nav_active="board",
        page_title=board_label or "Board",
        breadcrumb_html=bc,
        body_inner=body_inner,
        handbook_url=handbook_url,
        forge_url=forge_url,
        body_extra_class=body_cls,
        dashboard_extra_css=dash_css,
    )


def _website_top_level_html_path(path: str) -> bool:
    """True if path is a single segment under hosting public (e.g. foo.html), not nested dirs."""
    p = path.replace("\\", "/").strip()
    if not p or "/" in p:
        return False
    pl = p.lower()
    return pl.endswith(".html") or pl.endswith(".htm")


def _website_key_pages_grid(
    pages: list[Any], *, max_links: int = 8
) -> list[dict[str, str]]:
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
    out: list[dict[str, str]] = []
    for p in ordered[:max_links]:
        out.append(
            {
                "path": str(p.get("path", "")),
                "label": str(p.get("label", p.get("path", ""))),
            }
        )
    return out


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
        readme_raw = _readme_excerpt(repo_path, max_len=280) if repo_path.is_dir() else ""
        search_parts = [name, label, fb_site, pub, readme_raw]
        for p in pages[:80]:
            if isinstance(p, dict):
                search_parts.extend(
                    [str(p.get("label", "")), str(p.get("path", ""))]
                )
        search_blob = " ".join(x for x in search_parts if x).lower()
        sid = re.sub(r"[^a-z0-9_-]+", "-", name.lower()).strip("-") or "site"

        badges: list[str] = []
        if child and child.get("is_git"):
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

        kicker = label if label else "Firebase hosting site"
        pub_line = (
            f'<p class="forge-support small mb-0">Build output: <code>{esc(pub)}</code>'
            f"{f' · Firebase <code>{esc(fb_site)}</code>' if fb_site else ''}</p>"
        )
        readme_block = ""
        if readme_raw:
            readme_block = (
                f'<p class="forge-support small mb-0 mt-2">{esc(readme_raw)}</p>'
            )

        stat_bits: list[str] = [
            f'<span class="badge rounded-pill text-bg-dark border border-secondary">{html_total} HTML files</span>'
        ]
        if html_indexed and html_total and html_indexed < html_total:
            stat_bits.append(
                f'<span class="badge rounded-pill text-bg-dark border border-secondary">'
                f"{html_indexed} / {html_total} indexed</span>"
            )
        elif html_indexed:
            stat_bits.append(
                f'<span class="badge rounded-pill text-bg-dark border border-secondary">'
                f"{html_indexed} pages in index</span>"
            )
        stat_bits.append(
            f'<span class="badge rounded-pill text-bg-dark border border-secondary">'
            f"index mtime {esc(idx_mtime)}</span>"
        )
        stat_bits.append(
            f'<span class="badge rounded-pill text-bg-dark border border-secondary">public <code>{esc(pub)}</code></span>'
        )
        if fb_site:
            stat_bits.append(
                f'<span class="badge rounded-pill text-bg-dark border border-secondary">'
                f"site <code>{esc(fb_site)}</code></span>"
            )

        git_line = ""
        if child and child.get("is_git"):
            origin = str(gi.get("origin_url", ""))
            head_full = str(gi.get("head_full", ""))
            head_short = str(gi.get("head_short", ""))
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

        preview_root = local_site_href(name, "index.html")
        browse_href = f"/websites/browse?site={urllib.parse.quote(name, safe='')}"
        proj_href = f"/projects/{urllib.parse.quote(name, safe='')}"
        ext_url = str(project_urls.get(name, "")).strip()

        key_pages = _website_key_pages_grid(pages)
        grid_cells: list[str] = []
        for kp in key_pages:
            rel = kp["path"]
            lab = kp["label"]
            ph = local_site_href(name, rel)
            grid_cells.append(
                f'<div><a class="text-decoration-none lenses-key-page-link" href="{esc(ph)}" '
                f'target="_blank" rel="noopener">{esc(lab)}</a>'
                f'<span class="d-block forge-support" style="font-size:0.72rem">{esc(rel)}</span></div>'
            )
        key_grid_html = (
            '<div class="lenses-key-pages-grid">' + "".join(grid_cells) + "</div>"
            if grid_cells
            else '<p class="forge-support small mb-0">No top-level HTML pages in index yet — run the site generator, or open <strong>Preview in lenses</strong> for the full tree.</p>'
        )

        copy_btns = []
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
                f'target="_blank" rel="noopener">Published site</a> '
            )

        sections.append(
            f'<section class="lenses-site-card lenses-site-hero-section forge-card" '
            f'id="lenses-site-{esc(sid)}" aria-labelledby="lenses-site-title-{esc(sid)}" '
            f'data-lenses-search="{esc(search_blob)}">'
            f'<div class="d-flex flex-wrap justify-content-between gap-2 align-items-start mb-1">'
            f'<div>{"".join(badges)}</div></div>'
            f'<p class="lenses-hero-kicker mb-0">{esc(kicker)}</p>'
            f'<h2 class="text-cyan" id="lenses-site-title-{esc(sid)}">{esc(name)}</h2>'
            f"{pub_line}{readme_block}"
            f'<div class="lenses-site-stat-strip">{"".join(stat_bits)}</div>'
            f"{git_line}"
            f'<h3 class="h6 text-cyan mt-3 mb-2">Top-level pages</h3>'
            f"{key_grid_html}"
            f'<div class="d-flex flex-wrap gap-2 mt-3">'
            f'<a class="btn btn-sm btn-forge" href="{esc(browse_href)}">Preview in lenses</a>'
            f'<a class="btn btn-sm btn-outline-info" href="{esc(preview_root)}" target="_blank" rel="noopener">Open local root</a>'
            f"{ext_btn}"
            f'<a class="btn btn-sm btn-outline-secondary" href="{esc(proj_href)}">Project dashboard</a>'
            f"</div>"
            f'<div class="lenses-run-slot mt-2" data-lenses-run-site="{esc(name)}"></div>'
            f"{copy_row}"
            f"</section>"
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
  <div class="row g-2 align-items-end">
    <div class="col-md-6">
      <label class="form-label small text-cyan mb-1" for="lenses-global-q">Search sites &amp; pages</label>
      <input type="search" id="lenses-global-q" class="form-control form-control-sm" placeholder="Filter by name, path, title…" autocomplete="off" />
    </div>
    <div class="col-md-6">
      <div id="lenses-auth-panel" class="small forge-support">Checking session…</div>
      <div class="mt-2 d-none" id="lenses-auth-form">
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
    bc = lenses_breadcrumb_html(("/", "Overview"), ("/websites", "Websites"))
    return _wrap_dashboard(
        lenses_repo_root,
        browser_title="Websites — lenses",
        nav_active="websites",
        page_title="Websites",
        breadcrumb_html=bc,
        body_inner=body_inner,
        handbook_url=handbook_url,
        forge_url=forge_url,
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
        bc = lenses_breadcrumb_html(("/", "Overview"), ("/websites", "Websites"))
        return _wrap_dashboard(
            lenses_repo_root,
            browser_title="Browse — lenses",
            nav_active="websites",
            page_title="Websites",
            breadcrumb_html=bc,
            body_inner=body_inner,
            handbook_url=handbook_url,
            forge_url=forge_url,
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
        ("/websites", "Websites"),
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
    )


def wbs_view_link(rel_path: str) -> str:
    q = urllib.parse.urlencode({"p": rel_path})
    return f"/wbs/view?{q}"


def page_wbs(
    state: dict[str, Any],
    handbook_url: str,
    forge_url: str,
    lenses_repo_root: Path,
) -> str:
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
        '<table class="table table-sm"><thead><tr><th>Path</th><th>Kind</th><th>Top folder</th><th></th></tr></thead><tbody>'
        + (
            "\n".join(rows)
            if rows
            else '<tr><td colspan="4">No WBS.md / WBS.csv found.</td></tr>'
        )
        + "</tbody></table>"
    )
    body_inner = (
        '<p class="forge-support">Blueprint-style work breakdown files under '
        '<code>docs/requirements/</code>.</p>'
        + table
    )
    bc = lenses_breadcrumb_html(("/", "Overview"), ("/wbs", "WBS"))
    return _wrap_dashboard(
        lenses_repo_root,
        browser_title="WBS — lenses",
        nav_active="wbs",
        page_title="WBS",
        breadcrumb_html=bc,
        body_inner=body_inner,
        handbook_url=handbook_url,
        forge_url=forge_url,
    )


def page_wbs_view(
    rel_path: str,
    content: str,
    mime_hint: str,
    handbook_url: str,
    forge_url: str,
    lenses_repo_root: Path,
) -> str:
    if mime_hint == "csv":
        body_inner = f'<pre class="small" style="overflow:auto">{esc(content)}</pre>'
    else:
        body_inner = f'<pre class="small" style="overflow:auto;white-space:pre-wrap">{esc(content)}</pre>'
    body_inner = (
        f'<p class="forge-support"><code>{esc(rel_path)}</code></p>'
        f'<p><a href="/wbs">← Back to WBS list</a></p>'
        + body_inner
    )
    bc = lenses_breadcrumb_html(
        ("/", "Overview"),
        ("/wbs", "WBS"),
        ("", "WBS file"),
    )
    return _wrap_dashboard(
        lenses_repo_root,
        browser_title="WBS view — lenses",
        nav_active="wbs",
        page_title="WBS file",
        breadcrumb_html=bc,
        body_inner=body_inner,
        handbook_url=handbook_url,
        forge_url=forge_url,
    )


def roadmap_summary_fragment(md_text: str) -> str:
    metrics = extract_chart_metrics(md_text)
    return roadmap_summary_html(metrics)


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


def page_roadmaps(
    state: dict[str, Any],
    handbook_url: str,
    forge_url: str,
    lenses_repo_root: Path,
) -> str:
    rms = [r for r in (state.get("roadmaps") or []) if isinstance(r, dict)]
    opts: list[str] = [
        '<option value="">— Select roadmap —</option>',
    ]
    for r in rms:
        rp = str(r.get("rel_path", ""))
        if not rp:
            continue
        opts.append(f'<option value="{esc(rp)}">{esc(rp)}</option>')
    select_html = (
        '<label for="lenses-roadmap-file" class="form-label small text-muted mb-1">'
        "Roadmap file</label>"
        '<select id="lenses-roadmap-file" class="form-select form-select-sm lenses-roadmap-file-select">'
        f'{"".join(opts)}</select>'
    )
    if not rms:
        select_html = (
            '<p class="forge-support">No <code>ROADMAP.md</code> files found under <code>docs/</code>.</p>'
        )

    script = """
<script>
(function () {
  var fileSel = document.getElementById("lenses-roadmap-file");
  var outlineEl = document.getElementById("lenses-roadmap-outline");
  var summaryEl = document.getElementById("lenses-roadmap-summary");
  var frame = document.getElementById("lenses-roadmap-frame");
  if (!outlineEl || !summaryEl || !frame) return;

  function qs() {
    var o = {};
    var s = window.location.search.replace(/^\\?/, "");
    if (!s) return o;
    s.split("&").forEach(function (pair) {
      var i = pair.indexOf("=");
      if (i < 0) return;
      var k = decodeURIComponent(pair.slice(0, i).replace(/\\+/g, " "));
      var v = decodeURIComponent(pair.slice(i + 1).replace(/\\+/g, " "));
      o[k] = v;
    });
    return o;
  }

  function setUrl(p, section) {
    var q = new URLSearchParams();
    if (p) q.set("p", p);
    if (section) q.set("section", section);
    var tail = q.toString();
    var path = window.location.pathname + (tail ? "?" + tail : "");
    if (window.history && window.history.replaceState) {
      window.history.replaceState({}, "", path);
    }
  }

  function loadSummary(p) {
    summaryEl.innerHTML = '<p class="forge-support small mb-0">Loading summary…</p>';
    fetch("/roadmaps/summary?p=" + encodeURIComponent(p))
      .then(function (r) { return r.text(); })
      .then(function (html) { summaryEl.innerHTML = html; })
      .catch(function () {
        summaryEl.innerHTML = '<p class="forge-support text-warning">Summary failed to load.</p>';
      });
  }

  function setFrame(p, section) {
    frame.src = "/roadmaps/preview?p=" + encodeURIComponent(p) +
      "&section=" + encodeURIComponent(section);
  }

  function renderOutline(data, p, preferredSection) {
    outlineEl.innerHTML = "";
    var sections = data.sections || [];
    var firstId = sections.length ? sections[0].id : "";
    sections.forEach(function (s) {
      var li = document.createElement("button");
      li.type = "button";
      li.className = "list-group-item list-group-item-action lenses-roadmap-outline-item text-start";
      li.dataset.sectionId = s.id;
      var pad = (s.level > 2 ? (s.level - 2) * 0.65 : 0);
      li.style.paddingLeft = (0.85 + pad) + "rem";
      li.textContent = s.title;
      li.addEventListener("click", function () {
        outlineEl.querySelectorAll(".active").forEach(function (x) { x.classList.remove("active"); });
        li.classList.add("active");
        setFrame(p, s.id);
        setUrl(p, s.id);
      });
      outlineEl.appendChild(li);
    });
    var pick = preferredSection;
    if (pick && !sections.some(function (x) { return x.id === pick; })) pick = "";
    var use = pick || firstId;
    if (use) {
      setFrame(p, use);
      setUrl(p, use);
      outlineEl.querySelectorAll(".lenses-roadmap-outline-item").forEach(function (el) {
        if (el.dataset.sectionId === use) el.classList.add("active");
      });
    } else {
      frame.src = "about:blank";
    }
  }

  function loadRoadmap(p, preferredSection) {
    if (!p) {
      summaryEl.innerHTML = "";
      outlineEl.innerHTML = '<div class="list-group-item text-muted">Select a roadmap file.</div>';
      frame.src = "about:blank";
      setUrl("", "");
      return;
    }
    loadSummary(p);
    fetch("/api/roadmap-outline?p=" + encodeURIComponent(p))
      .then(function (r) {
        if (!r.ok) throw new Error("bad");
        return r.json();
      })
      .then(function (data) { renderOutline(data, p, preferredSection || ""); })
      .catch(function () {
        outlineEl.innerHTML = '<div class="list-group-item text-danger">Failed to load outline.</div>';
      });
  }

  if (fileSel) {
    fileSel.addEventListener("change", function () {
      loadRoadmap(fileSel.value, "");
    });
  }

  var q0 = qs();
  var initialP = q0.p || "";
  var initialSec = q0.section || "";
  if (fileSel && initialP) {
    fileSel.value = initialP;
    loadRoadmap(initialP, initialSec);
  } else if (fileSel && fileSel.value) {
    loadRoadmap(fileSel.value, "");
  } else {
    outlineEl.innerHTML = '<div class="list-group-item text-muted">Select a roadmap file.</div>';
    summaryEl.innerHTML = "";
    frame.src = "about:blank";
  }
})();
</script>
"""

    body_inner = (
        '<div class="lenses-roadmap-shell lenses-dash">'
        '<p class="forge-support">Browse <code>ROADMAP.md</code> files by section. '
        "Summary charts update when you change the file; the preview window updates per section.</p>"
        f'<div class="mb-3">{select_html}</div>'
        '<div id="lenses-roadmap-summary" class="card mb-3 p-3 lenses-roadmap-summary-card"></div>'
        '<div class="row g-3">'
        '<div class="col-md-4">'
        '<h3 class="h6 text-cyan mb-2">Outline</h3>'
        '<div id="lenses-roadmap-outline" class="list-group lenses-roadmap-outline"></div>'
        "</div>"
        '<div class="col-md-8">'
        '<h3 class="h6 text-cyan mb-2">Preview</h3>'
        '<div class="card lenses-roadmap-preview-window p-0 border border-secondary">'
        '<iframe id="lenses-roadmap-frame" class="w-100 lenses-roadmap-preview-frame" '
        'title="Roadmap section preview" style="min-height:28rem;border:0"></iframe>'
        "</div>"
        "</div>"
        "</div>"
        "</div>"
        f"{script}"
    )

    extra_css = """
.lenses-roadmap-outline { max-height: min(70vh, 36rem); overflow-y: auto; }
.lenses-roadmap-outline-item { cursor: pointer; font-size: 0.9rem; }
.lenses-roadmap-outline-item.active { background: rgba(6,182,212,0.12); border-color: rgba(6,182,212,0.35); }
.lenses-roadmap-preview-window { background: var(--bs-body-bg, #0f172a); }
.lenses-roadmap-summary-card { min-height: 3rem; }
.lenses-roadmap-file-select { max-width: 42rem; }
"""

    bc = lenses_breadcrumb_html(("/", "Overview"), ("", "Roadmaps"))
    return _wrap_dashboard(
        lenses_repo_root,
        browser_title="Roadmaps — lenses",
        nav_active="roadmaps",
        page_title="Roadmaps",
        breadcrumb_html=bc,
        body_inner=body_inner,
        handbook_url=handbook_url,
        forge_url=forge_url,
        dashboard_extra_css=extra_css,
    )
