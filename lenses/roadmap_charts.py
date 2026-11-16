"""Server-generated SVG summary charts for roadmap tables (no external chart libs)."""

from __future__ import annotations

import html
import math
from datetime import date, datetime, timedelta
from typing import Any

# KS diagram templates (static SVG) — served under /__ks/assets/svg/
KS_ROADMAP_TEMPLATE = "assets/svg/template-roadmap.svg"
KS_TIMELINE_TEMPLATE = "assets/svg/template-timeline.svg"


def _esc(s: str) -> str:
    return html.escape(s, quote=True)


def svg_epic_progress_bars(
    rows: list[tuple[str, float]],
    *,
    width: int = 420,
    row_h: float = 22.0,
    margin_l: float = 8.0,
    margin_r: float = 8.0,
    margin_t: float = 6.0,
    label_w: float = 200.0,
    bar_w: float = 180.0,
) -> str:
    if not rows:
        return ""
    n = min(len(rows), 24)
    rows = rows[:n]
    inner_h = margin_t + n * row_h + 8
    height = int(inner_h)
    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'role="img" aria-label="Epic percent complete" '
        f'style="width:100%;max-width:{width}px;height:auto">',
        '<rect width="100%" height="100%" fill="transparent"/>',
    ]
    y = margin_t
    for label, pct in rows:
        pct = max(0.0, min(100.0, float(pct)))
        short = label[:42] + ("…" if len(label) > 42 else "")
        title = _esc(f"{label}: {pct:.0f}%")
        parts.append(
            f'<text x="{margin_l:.1f}" y="{y + 14:.1f}" fill="var(--forge-muted,#94a3b8)" '
            f'font-size="11">{_esc(short)}</text>'
        )
        bx = margin_l + label_w
        parts.append(
            f'<rect x="{bx:.1f}" y="{y + 4:.1f}" width="{bar_w:.1f}" height="10" '
            f'rx="2" fill="#334155"><title>{title}</title></rect>'
        )
        fill_w = bar_w * (pct / 100.0)
        if fill_w > 0.5:
            parts.append(
                f'<rect x="{bx:.1f}" y="{y + 4:.1f}" width="{fill_w:.1f}" height="10" '
                f'rx="2" fill="rgba(6,182,212,0.9)"><title>{title}</title></rect>'
            )
        y += row_h
    parts.append("</svg>")
    return "\n".join(parts)


def svg_status_donut(status_counts: dict[str, int], *, size: int = 200) -> str:
    pairs = [(k, v) for k, v in status_counts.items() if v > 0]
    if not pairs:
        return ""
    total = sum(v for _, v in pairs)
    if total <= 0:
        return ""
    pairs.sort(key=lambda x: -x[1])
    colors = [
        "rgba(6,182,212,0.92)",
        "rgba(245,158,11,0.9)",
        "rgba(34,197,94,0.85)",
        "rgba(148,163,184,0.9)",
        "rgba(168,85,247,0.85)",
        "rgba(236,72,153,0.85)",
    ]
    r_outer, r_inner = 78.0, 44.0
    cx, cy = size / 2, size / 2
    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" '
        f'role="img" aria-label="Status distribution" '
        f'style="width:100%;max-width:{size}px;height:auto">',
        '<rect width="100%" height="100%" fill="transparent"/>',
    ]
    ang = -math.pi / 2
    for i, (name, val) in enumerate(pairs[:10]):
        frac = val / total
        if frac <= 0:
            continue
        sweep = 2 * math.pi * frac
        fill = colors[i % len(colors)]
        a0, a1 = ang, ang + sweep
        x1o, y1o = cx + r_outer * math.cos(a0), cy + r_outer * math.sin(a0)
        x2o, y2o = cx + r_outer * math.cos(a1), cy + r_outer * math.sin(a1)
        x1i, y1i = cx + r_inner * math.cos(a1), cy + r_inner * math.sin(a1)
        x2i, y2i = cx + r_inner * math.cos(a0), cy + r_inner * math.sin(a0)
        large = 1 if sweep > math.pi else 0
        d = (
            f"M {x1o:.2f} {y1o:.2f} A {r_outer:.2f} {r_outer:.2f} 0 {large} 1 {x2o:.2f} {y2o:.2f} "
            f"L {x1i:.2f} {y1i:.2f} A {r_inner:.2f} {r_inner:.2f} 0 {large} 0 {x2i:.2f} {y2i:.2f} Z"
        )
        pct = 100.0 * frac
        nm = name[:40] + ("…" if len(name) > 40 else "")
        title = _esc(f"{nm}: {val} ({pct:.1f}%)")
        parts.append(f'<path d="{d}" fill="{fill}"><title>{title}</title></path>')
        ang = a1
    parts.append("</svg>")
    leg: list[str] = ['<div class="lenses-roadmap-donut-legend small mt-2">']
    for i, (name, val) in enumerate(pairs[:10]):
        pct = 100.0 * val / total
        fill = colors[i % len(colors)]
        nm = _esc(name[:36])
        leg.append(
            f'<div class="d-flex align-items-center gap-2 mb-1">'
            f'<span class="lenses-overview-donut-swatch" style="background:{fill}"></span>'
            f"<span>{nm}</span>"
            f'<span class="text-muted ms-auto">{pct:.1f}%</span></div>'
        )
    leg.append("</div>")
    return "\n".join(parts) + "\n" + "\n".join(leg)


def horizon_badges_html(horizon_counts: dict[str, int]) -> str:
    if not horizon_counts:
        return ""
    order = ("NOW", "NEXT", "LATER", "FIRST", "PARALLEL")
    bits: list[str] = ['<div class="lenses-roadmap-horizon d-flex flex-wrap gap-2 align-items-center">']
    bits.append('<span class="small text-muted me-1">Horizon:</span>')
    for key in order:
        n = horizon_counts.get(key, 0)
        if n:
            bits.append(
                f'<span class="badge rounded-pill text-bg-info">{_esc(key)} × {n}</span>'
            )
    for k, n in sorted(horizon_counts.items()):
        if k not in order and n:
            bits.append(
                f'<span class="badge rounded-pill text-bg-secondary">{_esc(k)} × {n}</span>'
            )
    bits.append("</div>")
    return "".join(bits)


def ks_diagram_img(rel_under_ks: str, *, alt: str, max_width_px: int = 220) -> str:
    src = "/__ks/" + rel_under_ks.lstrip("/")
    return (
        f'<div class="lenses-roadmap-ks-diagram text-center mb-2 w-100">'
        f'<img src="{_esc(src)}" alt="{_esc(alt)}" '
        f'style="width:100%;max-width:min(100%,{max_width_px}px);height:auto;opacity:0.9" '
        f'loading="lazy" />'
        f"</div>"
    )


def svg_roadmap_gantt(
    model: dict[str, Any],
    *,
    width: int = 900,
    label_w: float = 212.0,
    row_h: float = 28.0,
    header_h: float = 36.0,
) -> str:
    """Ordinal timeline: columns = milestones, rows = epic bars."""
    milestones = model.get("milestones") if isinstance(model.get("milestones"), list) else []
    bars_raw = model.get("bars") if isinstance(model.get("bars"), list) else []
    if not milestones or not bars_raw:
        return ""

    bars: list[dict[str, Any]] = []
    for b in bars_raw[:48]:
        if not isinstance(b, dict):
            continue
        try:
            s = int(b["start"])
            e = int(b["end"])
        except (KeyError, TypeError, ValueError):
            continue
        label = str(b.get("label") or "Epic")
        st = str(b.get("status") or "")
        epic_id = str(b.get("epic_id") or "").strip()
        bars.append(
            {"start": s, "end": e, "label": label, "status": st, "epic_id": epic_id}
        )

    if not bars:
        return ""

    n = len(milestones)
    margin_l = 10.0
    margin_r = 10.0
    chart_x0 = margin_l + label_w
    chart_w = max(120.0, float(width) - margin_l - margin_r - label_w)
    slot_w = chart_w / float(n) if n else chart_w
    height = int(header_h + len(bars) * row_h + 14)
    grid_stroke = "rgba(6,182,212,0.14)"

    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'role="img" aria-label="Roadmap timeline by milestone" '
        f'preserveAspectRatio="xMinYMin meet" '
        f'style="width:100%;height:auto;display:block">',
        '<rect width="100%" height="100%" fill="transparent"/>',
    ]

    for j in range(n + 1):
        x = chart_x0 + j * slot_w
        parts.append(
            f'<line x1="{x:.2f}" y1="{header_h - 4:.2f}" x2="{x:.2f}" y2="{height - 6:.2f}" '
            f'stroke="{grid_stroke}" stroke-width="1"/>'
        )

    for j, mid in enumerate(milestones):
        cx = chart_x0 + (j + 0.5) * slot_w
        short = mid[:10] + ("…" if len(mid) > 10 else "")
        parts.append(
            f'<text x="{cx:.2f}" y="{header_h - 14:.2f}" text-anchor="middle" '
            f'fill="var(--forge-muted,#94a3b8)" font-size="11" font-weight="600">'
            f"{_esc(short)}</text>"
        )

    fills = ("rgba(6,182,212,0.82)", "rgba(245,158,11,0.78)")
    y0 = header_h
    for i, bar in enumerate(bars):
        s, e = bar["start"], bar["end"]
        s = max(0, min(n - 1, s))
        e = max(0, min(n - 1, e))
        if e < s:
            s, e = e, s
        bx = chart_x0 + s * slot_w + 2
        bw = (e - s + 1) * slot_w - 4
        bw = max(bw, 6.0)
        y = y0 + i * row_h + 5
        fill = fills[i % 2]
        lab = bar["label"]
        short = lab[:46] + ("…" if len(lab) > 46 else "")
        tip = lab
        if bar.get("status"):
            tip = f"{lab} ({bar['status']})"
        eid = str(bar.get("epic_id") or "").strip()
        data_eid = f' data-lenses-node-id="{_esc(eid)}"' if eid else ""
        parts.append(
            f'<text x="{margin_l:.1f}" y="{y + 12:.1f}" fill="var(--forge-muted,#94a3b8)" '
            f'font-size="10.5">{_esc(short)}</text>'
        )
        parts.append(
            f'<rect x="{bx:.2f}" y="{y:.2f}" width="{bw:.2f}" height="16" rx="3" '
            f'class="lenses-gantt-bar"{data_eid}'
            f' fill="{fill}" stroke="rgba(15,23,42,0.5)" stroke-width="0.5">'
            f"<title>{_esc(tip)}</title></rect>"
        )

    parts.append("</svg>")
    return "\n".join(parts)


def _parse_iso_date(s: str | None) -> date | None:
    if not s or not isinstance(s, str):
        return None
    try:
        return datetime.strptime(s.strip()[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _range_ends(a: str | None, b: str | None) -> tuple[date | None, date | None]:
    da = _parse_iso_date(a)
    db = _parse_iso_date(b)
    if da and db:
        if da > db:
            da, db = db, da
        return da, db
    if da and not db:
        return da, da
    if db and not da:
        return db, db
    return None, None


def svg_roadmap_date_shift(
    model: dict[str, Any],
    *,
    width: int = 900,
    label_w: float = 200.0,
    row_h: float = 36.0,
    header_h: float = 36.0,
    bar_h: float = 11.0,
) -> str:
    """Calendar strip: initial vs target ranges per epic (ISO dates)."""
    raw_rows = model.get("rows") if isinstance(model.get("rows"), list) else []
    if not raw_rows:
        return ""

    rows: list[dict[str, Any]] = []
    all_dates: list[date] = []
    for r in raw_rows[:40]:
        if not isinstance(r, dict):
            continue
        i0, i1 = _range_ends(
            str(r.get("initial_start") or ""),
            str(r.get("initial_end") or ""),
        )
        t0, t1 = _range_ends(
            str(r.get("target_start") or ""),
            str(r.get("target_end") or ""),
        )
        if not any((i0, i1, t0, t1)):
            continue
        label = str(r.get("label") or "Epic")[:52]
        eid = str(r.get("epic_id") or "").strip()
        rows.append(
            {
                "label": label,
                "epic_id": eid,
                "i0": i0,
                "i1": i1,
                "t0": t0,
                "t1": t1,
            }
        )
        for d in (i0, i1, t0, t1):
            if d:
                all_dates.append(d)

    if not rows or not all_dates:
        return ""

    t_min = min(all_dates)
    t_max = max(all_dates)
    if t_min == t_max:
        t_min = t_min - timedelta(days=7)
        t_max = t_max + timedelta(days=7)
    span_days = max(1, (t_max - t_min).days + 1)

    margin_l = 8.0
    margin_r = 10.0
    margin_b = 22.0
    chart_x0 = margin_l + label_w
    chart_w = max(120.0, float(width) - margin_l - margin_r - label_w)
    n = len(rows)
    height = int(header_h + n * row_h + margin_b)

    def x_for(d: date) -> float:
        off = (d - t_min).days
        return chart_x0 + (off / float(span_days)) * chart_w

    fill_initial = "rgba(148,163,184,0.88)"
    fill_target = "rgba(6,182,212,0.85)"
    grid_stroke = "rgba(6,182,212,0.12)"

    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'role="img" aria-label="Initial vs target date ranges" '
        f'preserveAspectRatio="xMinYMin meet" '
        f'style="width:100%;height:auto;display:block">',
        '<rect width="100%" height="100%" fill="transparent"/>',
    ]
    # Axis labels (start / end of window)
    parts.append(
        f'<text x="{chart_x0:.2f}" y="{header_h - 10:.2f}" fill="var(--forge-muted,#94a3b8)" '
        f'font-size="10">{_esc(str(t_min))}</text>'
    )
    parts.append(
        f'<text x="{chart_x0 + chart_w:.2f}" y="{header_h - 10:.2f}" text-anchor="end" '
        f'fill="var(--forge-muted,#94a3b8)" font-size="10">{_esc(str(t_max))}</text>'
    )
    # Legend
    lx = chart_x0 + chart_w * 0.35
    parts.append(
        f'<rect x="{lx:.1f}" y="4" width="10" height="8" rx="2" fill="{fill_initial}"/>'
        f'<text x="{lx + 14:.1f}" y="11" fill="var(--forge-muted,#94a3b8)" font-size="9">Initial</text>'
    )
    parts.append(
        f'<rect x="{lx + 72:.1f}" y="4" width="10" height="8" rx="2" fill="{fill_target}"/>'
        f'<text x="{lx + 86:.1f}" y="11" fill="var(--forge-muted,#94a3b8)" font-size="9">Target</text>'
    )

    for j in range(5):
        frac = j / 4.0
        x = chart_x0 + frac * chart_w
        parts.append(
            f'<line x1="{x:.2f}" y1="{header_h:.2f}" x2="{x:.2f}" y2="{height - margin_b:.2f}" '
            f'stroke="{grid_stroke}" stroke-width="1"/>'
        )

    y0 = header_h
    for i, bar in enumerate(rows):
        y = y0 + i * row_h
        lab = bar["label"]
        short = lab[:44] + ("…" if len(lab) > 44 else "")
        parts.append(
            f'<text x="{margin_l:.1f}" y="{y + 14:.1f}" fill="var(--forge-muted,#94a3b8)" '
            f'font-size="10">{_esc(short)}</text>'
        )
        i0, i1 = bar["i0"], bar["i1"]
        t0, t1 = bar["t0"], bar["t1"]
        data_eid = ""
        eid = str(bar.get("epic_id") or "")
        if eid:
            data_eid = f' data-lenses-node-id="{_esc(eid)}"'
        # Initial bar (upper)
        if i0 and i1:
            xa, xb = x_for(i0), x_for(i1)
            if xb < xa:
                xa, xb = xb, xa
            bw = max(xb - xa, 3.0)
            tip = f"Initial: {i0} – {i1}"
            parts.append(
                f'<rect x="{xa:.2f}" y="{y + 2:.1f}" width="{bw:.2f}" height="{bar_h:.1f}" rx="2" '
                f'fill="{fill_initial}"{data_eid}><title>{_esc(tip)}</title></rect>'
            )
        # Target bar (lower)
        if t0 and t1:
            xa, xb = x_for(t0), x_for(t1)
            if xb < xa:
                xa, xb = xb, xa
            bw = max(xb - xa, 3.0)
            tip = f"Target: {t0} – {t1}"
            parts.append(
                f'<rect x="{xa:.2f}" y="{y + 15:.1f}" width="{bw:.2f}" height="{bar_h:.1f}" rx="2" '
                f'fill="{fill_target}"{data_eid}><title>{_esc(tip)}</title></rect>'
            )

    parts.append("</svg>")
    return "\n".join(parts)


def roadmap_date_shift_html(model: dict[str, Any], *, heading: bool = True) -> str:
    if not model.get("has_date_shift"):
        return ""
    svg = svg_roadmap_date_shift(model)
    if not svg:
        return ""
    h = (
        '<h3 class="h6 text-cyan mb-2">Calendar (initial vs target)</h3>'
        if heading
        else ""
    )
    return (
        f'<div class="lenses-roadmap-dateshift-wrap mb-2">{h}'
        f'<div class="lenses-roadmap-dateshift-svg">{svg}</div></div>'
    )


def roadmap_gantt_html(model: dict[str, Any], *, heading: bool = True) -> str:
    """Wrapper div + optional heading for Gantt SVG."""
    if not model.get("has_gantt"):
        return ""
    svg = svg_roadmap_gantt(model)
    if not svg:
        return ""
    h = (
        '<h3 class="h6 text-cyan mb-2">Timeline (by milestone)</h3>'
        if heading
        else ""
    )
    return (
        f'<div class="lenses-roadmap-gantt-wrap mb-2">{h}'
        f'<div class="lenses-roadmap-gantt-svg">{svg}</div></div>'
    )


def roadmap_summary_html(
    metrics: dict[str, Any],
    gantt_model: dict[str, Any] | None = None,
    date_shift_model: dict[str, Any] | None = None,
    *,
    include_ks_diagrams: bool = True,
) -> str:
    """HTML fragment for #lenses-roadmap-summary in the shell page."""
    gantt_model = gantt_model or {}
    date_shift_model = date_shift_model or {}
    has_gantt = bool(gantt_model.get("has_gantt"))
    has_date_shift = bool(date_shift_model.get("has_date_shift"))
    has_any = bool(metrics.get("has_chartable"))
    epic_bars = metrics.get("epic_bars") or []
    status_counts = metrics.get("status_counts") or {}
    horizon_counts = metrics.get("horizon_counts") or {}

    if isinstance(epic_bars, list):
        epic_pairs: list[tuple[str, float]] = []
        for item in epic_bars:
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                epic_pairs.append((str(item[0]), float(item[1])))
    else:
        epic_pairs = []

    if (
        not has_any
        and not epic_pairs
        and not status_counts
        and not horizon_counts
        and not has_gantt
        and not has_date_shift
    ):
        return (
            '<div class="lenses-roadmap-summary-empty">'
            '<p class="lenses-plan-empty-title">No chartable tables</p>'
            '<p class="forge-support small mb-0">'
            "Add tables with status, % complete, horizon, or optional Initial/Target "
            "date columns to ROADMAP.md.</p>"
            "</div>"
        )

    blocks: list[str] = ['<div class="lenses-roadmap-summary-inner">']

    gantt_html = roadmap_gantt_html(gantt_model, heading=True)
    if gantt_html:
        blocks.append(f'<div class="mb-3">{gantt_html}</div>')

    date_shift_html = roadmap_date_shift_html(date_shift_model, heading=True)
    if date_shift_html:
        blocks.append(f'<div class="mb-3">{date_shift_html}</div>')

    metrics_inner: list[str] = ['<div class="row g-3">']

    diagram_bits = ""
    # Native KS templates are 680px wide; avoid squeezing into a narrow column.
    _diagram_max = 680
    if include_ks_diagrams and not gantt_html and not date_shift_html:
        if horizon_counts:
            diagram_bits += ks_diagram_img(
                KS_TIMELINE_TEMPLATE,
                alt="Timeline diagram template",
                max_width_px=_diagram_max,
            )
        elif epic_pairs or status_counts:
            diagram_bits += ks_diagram_img(
                KS_ROADMAP_TEMPLATE,
                alt="Roadmap diagram template",
                max_width_px=_diagram_max,
            )

    if diagram_bits:
        metrics_inner.append(
            '<div class="col-12">'
            '<div class="d-flex justify-content-center lenses-roadmap-ks-diagram-outer">'
            f"{diagram_bits}"
            "</div></div>"
        )

    metrics_inner.append('<div class="col-12"><div class="row g-3">')

    hz = horizon_badges_html(horizon_counts if isinstance(horizon_counts, dict) else {})
    if hz:
        metrics_inner.append(f'<div class="col-12">{hz}</div>')

    if epic_pairs:
        metrics_inner.append(
            '<div class="col-lg-6">'
            '<h3 class="h6 text-cyan mb-2">Progress (% complete)</h3>'
            f"{svg_epic_progress_bars(epic_pairs)}"
            "</div>"
        )

    sc = status_counts if isinstance(status_counts, dict) else {}
    donut = svg_status_donut(sc)
    if donut:
        metrics_inner.append(
            '<div class="col-lg-6">'
            '<h3 class="h6 text-cyan mb-2">Status mix</h3>'
            f'<div class="lenses-overview-donut-wrap">{donut}</div>'
            "</div>"
        )

    metrics_inner.append("</div></div>")
    metrics_inner.append("</div>")

    metrics_block = "\n".join(metrics_inner)
    has_metrics_row = bool(diagram_bits or hz or epic_pairs or donut)
    if (gantt_html or date_shift_html) and has_metrics_row:
        blocks.append(
            '<details class="lenses-roadmap-metrics-details mt-1">'
            '<summary class="h6 text-cyan mb-0 user-select-none" style="cursor:pointer">'
            "Metrics</summary>"
            f'<div class="pt-3 border-top border-secondary mt-2">{metrics_block}</div>'
            "</details>"
        )
    elif has_metrics_row:
        blocks.append(metrics_block)

    blocks.append("</div>")
    return "\n".join(blocks)
