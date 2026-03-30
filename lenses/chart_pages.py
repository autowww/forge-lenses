"""HTML for API-driven chart pages (parallel to SSR dashboard charts)."""

from __future__ import annotations

import urllib.parse
from pathlib import Path
from typing import Any

from lenses.render import _wrap_dashboard, esc, lenses_breadcrumb_html


def _chart_mount(kind: str, title: str, api_url: str) -> str:
    return (
        f'<section class="lenses-site-hero-section forge-card mb-4" data-ks-chart-wrap="{esc(kind)}">'
        f'<h3 class="h6 text-cyan mb-2">{esc(title)}</h3>'
        f'<div class="ks-chart-mount" data-ks-chart data-ks-chart-kind="{esc(kind)}" '
        f'data-ks-chart-url="{esc(api_url)}"></div>'
        "</section>"
    )


def _charts_script() -> str:
    return """<script>
document.addEventListener('DOMContentLoaded', function() {
  if (window.ForgeDataCharts) { window.ForgeDataCharts.mountAll(document); }
});
</script>"""


def page_overview_charts_api(
    state: dict[str, Any],
    registry: dict[str, Any],
    handbook_url: str,
    forge_url: str,
    lenses_repo_root: Path,
) -> str:
    """Workspace charts via client fetch (same kinds as SSR overview analytics)."""
    api = "/api/chart-data/overview"
    intro = (
        '<p class="forge-support mb-3">This page mirrors <a href="/">Overview</a> analytics using '
        f'<code>forge-data-charts.js</code> and <code>{esc(api)}</code>. '
        'Classic server-rendered charts remain on the main overview.</p>'
    )
    blocks = [
        intro,
        _chart_mount("commit_daily", "Commits by day (7 days)", api),
        _chart_mount("loc_added_horizontal", "Lines added by repository (7 days)", api),
        _chart_mount("loc_total_bars", "Repository size (approx. LoC)", api),
        _chart_mount("loc_share_donut", "Share of workspace lines", api),
        _chart_mount("compliance_bars", "Compliance score by repository", api),
        _chart_mount("extension_heatmap", "File types (workspace)", api),
        _charts_script(),
    ]
    bc = lenses_breadcrumb_html(
        ("/", "Overview"),
        ("/overview/charts-api", "Charts (API)"),
    )
    head_extra = (
        '<link rel="stylesheet" href="/__ks/css/forge-data-charts.css">'
        '<script src="/__ks/js/forge-data-charts.js" defer></script>'
    )
    return _wrap_dashboard(
        lenses_repo_root,
        browser_title="Overview charts (API) — lenses",
        nav_active="overview",
        page_title="Overview — API charts",
        breadcrumb_html=bc,
        body_inner="\n".join(blocks),
        handbook_url=handbook_url,
        forge_url=forge_url,
        dashboard_extra_css=head_extra,
    )


def page_project_charts_api(
    state: dict[str, Any],
    registry: dict[str, Any],
    project_name: str,
    child_path: Path,
    handbook_url: str,
    forge_url: str,
    lenses_repo_root: Path,
) -> str:
    """Per-project charts via client fetch (same kinds as SSR project detail)."""
    enc = urllib.parse.quote(project_name, safe="")
    api = f"/api/project/{enc}/chart-data"
    phref = f"/projects/{enc}"
    intro = (
        f'<p class="forge-support mb-3">API-driven charts for <strong>{esc(project_name)}</strong>. '
        f'Server-rendered project page: <a href="{esc(phref)}">project detail</a>.</p>'
    )
    blocks = [
        intro,
        _chart_mount("commit_weekly", "Activity (90 days)", api),
        _chart_mount("commit_daily", "Activity (7 days)", api),
        _chart_mount("contributors", "Contributors", api),
        _chart_mount("extension_heatmap", "File types", api),
        _chart_mount("compliance_bars", "Standards compliance (score)", api),
        _chart_mount("submodule_layout", "Submodule layout", api),
        _charts_script(),
    ]
    bc = lenses_breadcrumb_html(
        ("/projects", "Projects"),
        (phref, project_name),
        (f"{phref}/charts-api", "Charts (API)"),
    )
    head_extra = (
        '<link rel="stylesheet" href="/__ks/css/forge-data-charts.css">'
        '<script src="/__ks/js/forge-data-charts.js" defer></script>'
    )
    return _wrap_dashboard(
        lenses_repo_root,
        browser_title=f"{project_name} — API charts — lenses",
        nav_active="projects",
        page_title=f"{project_name} — API charts",
        breadcrumb_html=bc,
        body_inner="\n".join(blocks),
        handbook_url=handbook_url,
        forge_url=forge_url,
        dashboard_extra_css=head_extra,
    )
