"""Classic (server-rendered) scrollytelling feature showcase — mirrors Studio /studio/feature-showcase."""

from __future__ import annotations

import html as html_lib
import json


def _esc(s: str) -> str:
    return html_lib.escape(s, quote=True)


# Same content shape as lenses-enterprise example data (edit URLs/copy here for Classic).
FEATURE_SHOWCASE_ITEMS: list[dict[str, str]] = [
    {
        "id": "unified",
        "heading": "One workspace for every repo",
        "summary": "Scan once, browse projects, sites, and roadmaps without switching tools.",
        "description": "Workspace state stays in sync with your filesystem and git metadata.",
        "bg": "https://images.unsplash.com/photo-1497366216548-37526070297c?auto=format&fit=crop&w=1400&q=80",
        "main": "https://images.unsplash.com/photo-1460925895917-afdab827c52f?auto=format&fit=crop&w=1000&q=80",
        "main_alt": "Analytics dashboard on a laptop",
        "cta_label": "Explore projects",
        "cta_href": "/projects",
    },
    {
        "id": "charts",
        "heading": "Charts that stay honest",
        "summary": "WBS, timelines, and overview charts generated from the same truth as your boards.",
        "description": "Resize, filter, and drill down without exporting to a spreadsheet.",
        "bg": "https://images.unsplash.com/photo-1551288049-bebda4e38f71?auto=format&fit=crop&w=1400&q=80",
        "main": "https://images.unsplash.com/photo-1543286386-713bdd548da4?auto=format&fit=crop&w=1000&q=80",
        "main_alt": "Colorful data visualization",
        "cta_label": "Open charts",
        "cta_href": "/overview/charts-api",
    },
    {
        "id": "websites",
        "heading": "Static sites at a glance",
        "summary": "See Firebase-ready sites, page counts, and jump into browse mode fast.",
        "description": "",
        "bg": "https://images.unsplash.com/photo-1504639725590-34dda098e8c3?auto=format&fit=crop&w=1400&q=80",
        "main": "https://images.unsplash.com/photo-1517694712202-14dd9538aa97?auto=format&fit=crop&w=1000&q=80",
        "main_alt": "Laptop showing code editor",
        "cta_label": "Browse websites",
        "cta_href": "/websites",
    },
    {
        "id": "boards",
        "heading": "Boards for real work",
        "summary": "Capture stickers, notes, and next steps where your team already looks.",
        "description": "",
        "bg": "https://images.unsplash.com/photo-1531403009284-440f080d1e12?auto=format&fit=crop&w=1400&q=80",
        "main": "https://images.unsplash.com/photo-1522071820081-009f0129c71c?auto=format&fit=crop&w=1000&q=80",
        "main_alt": "Team collaborating at a whiteboard",
        "cta_label": "View boards",
        "cta_href": "/board",
    },
    {
        "id": "search",
        "heading": "Search that respects your tree",
        "summary": "Ripgrep-backed search across the workspace with sane defaults.",
        "description": "",
        "bg": "https://images.unsplash.com/photo-1451187580459-43490279c0fa?auto=format&fit=crop&w=1400&q=80",
        "main": "https://images.unsplash.com/photo-1504384308090-c894fdcc538d?auto=format&fit=crop&w=1000&q=80",
        "main_alt": "Developer typing on keyboard",
        "cta_label": "Try search",
        "cta_href": "/search",
    },
]


FEATURE_SHOWCASE_CSS = """
<style>
.lenses-fs { --fs-parallax: 12px; --fs-radius: 1.25rem; max-width: 72rem; margin-inline: auto; }
.lenses-fs-lead { font-size: 0.95rem; line-height: 1.55; opacity: 0.88; max-width: 42rem; }
.lenses-fs-grid {
  display: grid; gap: 1.75rem; align-items: start;
}
@media (min-width: 992px) {
  .lenses-fs-grid { grid-template-columns: 1fr 1fr; gap: 2rem; }
  .lenses-fs-col--list { order: 1; }
  .lenses-fs-col--visual { order: 2; }
}
@media (max-width: 991.98px) {
  .lenses-fs-col--visual { order: 1; margin-bottom: 0.5rem; }
  .lenses-fs-col--list { order: 2; }
  .lenses-fs-sticky {
    position: sticky; top: 0; z-index: 5;
    background: linear-gradient(to bottom, rgba(10,14,23,0.97) 0%, rgba(10,14,23,0.92) 85%, transparent 100%);
    padding-bottom: 0.5rem; margin-bottom: 0.5rem;
  }
}
.lenses-fs-sticky { position: sticky; top: 0.75rem; }
@media (min-width: 992px) {
  .lenses-fs-sticky { top: 1rem; }
}
.lenses-fs-visual {
  position: relative; overflow: hidden; border-radius: var(--fs-radius);
  background: #0f172a; min-height: min(42vh, 22rem); aspect-ratio: auto;
  box-shadow: 0 24px 48px -12px rgba(0,0,0,0.55);
  border: 1px solid rgba(255,255,255,0.08);
}
@media (min-width: 992px) {
  .lenses-fs-visual { min-height: 0; aspect-ratio: 4 / 5; max-height: min(100vh - 6rem, 44rem); }
}
.lenses-fs-bg-layer {
  position: absolute; inset: 0; transform: scale(1.06); will-change: transform;
}
.lenses-fs-bg-layer img {
  width: 100%; height: 100%; object-fit: cover; opacity: 0.55;
}
.lenses-fs-bg-layer::after {
  content: ""; position: absolute; inset: 0;
  background: linear-gradient(to top, rgba(2,6,23,0.92) 0%, rgba(15,23,42,0.2) 50%, rgba(2,6,23,0.45) 100%);
}
.lenses-fs-fg-layer {
  position: relative; display: flex; align-items: center; justify-content: center;
  padding: 1.5rem; min-height: min(42vh, 22rem);
}
@media (min-width: 992px) {
  .lenses-fs-fg-layer { min-height: 0; flex: 1; }
}
.lenses-fs-fg-inner {
  position: relative; width: 100%; max-width: 24rem;
  border-radius: 1rem; overflow: hidden;
  box-shadow: 0 24px 64px -12px rgba(0,0,0,0.55);
  border: 1px solid rgba(255,255,255,0.12);
  will-change: transform;
}
.lenses-fs-fg-inner img { width: 100%; aspect-ratio: 4/3; object-fit: cover; display: block; }
.lenses-fs-item-wrap { scroll-margin-top: 6rem; margin-bottom: 1.25rem; }
.lenses-fs-item-wrap:last-child { margin-bottom: 0; }
.lenses-fs-card {
  border-radius: 1rem; border: 1px solid rgba(148,163,184,0.35);
  background: rgba(15,23,42,0.45); transition: border-color 0.25s ease, box-shadow 0.25s ease, background 0.25s ease;
}
.lenses-fs-card:hover { border-color: rgba(148,163,184,0.55); background: rgba(30,41,59,0.45); }
.lenses-fs-card.is-active {
  border-color: rgba(251,191,36,0.45);
  box-shadow: 0 0 0 1px rgba(251,191,36,0.12), 0 16px 40px -12px rgba(0,0,0,0.45);
  background: rgba(30,41,59,0.65);
}
.lenses-fs-card.is-active .lenses-fs-card-title { color: #fef3c7; }
.lenses-fs-card-title { font-size: 1.15rem; font-weight: 600; margin: 0; color: #f8fafc; letter-spacing: -0.02em; }
.lenses-fs-card-sum { font-size: 0.9rem; line-height: 1.55; color: #94a3b8; margin: 0.4rem 0 0; }
.lenses-fs-card-desc { font-size: 0.875rem; line-height: 1.55; color: #64748b; margin: 0.75rem 0 0; }
.lenses-fs-btn {
  display: block; width: 100%; text-align: left; padding: 1rem 1.15rem;
  background: transparent; border: none; color: inherit; cursor: pointer; border-radius: 1rem;
}
.lenses-fs-btn:focus-visible {
  outline: 2px solid rgba(251,191,36,0.85); outline-offset: 2px;
}
.lenses-fs-cta {
  display: block; padding: 0.65rem 1.15rem; border-top: 1px solid rgba(148,163,184,0.25);
  font-size: 0.9rem; font-weight: 500; color: #fbbf24; text-decoration: none;
}
.lenses-fs-cta:hover { color: #fcd34d; text-decoration: underline; }
.lenses-fs-cta:focus-visible { outline: 2px solid rgba(251,191,36,0.85); outline-offset: -2px; }
@media (prefers-reduced-motion: reduce) {
  .lenses-fs-card, .lenses-fs-visual .lenses-fs-fg-inner { transition: none; }
  .lenses-fs-bg-layer, .lenses-fs-fg-inner { transform: none !important; }
}
.lenses-fs-visual.is-transitioning .lenses-fs-fg-inner { opacity: 0.92; }
</style>
"""


FEATURE_SHOWCASE_JS = """
<script>
(function () {
  var root = document.getElementById("lenses-fs-root");
  if (!root) return;
  var panel = document.getElementById("lenses-fs-panel");
  var live = document.getElementById("lenses-fs-live");
  var bgImg = root.querySelector(".lenses-fs-bg");
  var fgImg = root.querySelector(".lenses-fs-fg");
  var bgLayer = root.querySelector(".lenses-fs-bg-layer");
  var fgInner = root.querySelector(".lenses-fs-fg-inner");
  var wraps = root.querySelectorAll(".lenses-fs-item-wrap");
  var n = wraps.length;
  if (!panel || !bgImg || !fgImg || n === 0) return;

  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var parallaxPx = reduceMotion ? 0 : 12;

  function itemData(el) {
    return {
      bg: el.getAttribute("data-bg") || "",
      main: el.getAttribute("data-main") || "",
      mainAlt: el.getAttribute("data-main-alt") || "",
      heading: el.getAttribute("data-heading") || ""
    };
  }

  function applyVisual(d) {
    bgImg.src = d.bg;
    fgImg.src = d.main;
    fgImg.alt = d.mainAlt;
    if (live) live.textContent = d.heading;
  }

  function setActive(index) {
    wraps.forEach(function (w, i) {
      var card = w.querySelector(".lenses-fs-card");
      var btn = w.querySelector(".lenses-fs-btn");
      var on = i === index;
      if (card) card.classList.toggle("is-active", on);
      if (btn) btn.setAttribute("aria-pressed", on ? "true" : "false");
    });
    applyVisual(itemData(wraps[index]));
    if (!reduceMotion && panel) panel.classList.add("is-transitioning");
    setTimeout(function () {
      if (panel) panel.classList.remove("is-transitioning");
    }, 280);
  }

  var ratios = new Array(n).fill(0);
  var thresholds = [];
  for (var t = 0; t <= 20; t++) thresholds.push(t / 20);

  function pickBest() {
    var best = 0, bestR = -1;
    for (var j = 0; j < n; j++) {
      var r = ratios[j] || 0;
      if (r > bestR) { bestR = r; best = j; }
    }
    if (bestR > 0) setActive(best);
  }

  wraps.forEach(function (wrap, i) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) { ratios[i] = e.intersectionRatio; });
      pickBest();
    }, { root: null, rootMargin: "-38% 0px -38% 0px", threshold: thresholds });
    io.observe(wrap);
    var btn = wrap.querySelector(".lenses-fs-btn");
    if (btn) {
      btn.addEventListener("click", function () {
        setActive(i);
        wrap.scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth", block: "nearest" });
      });
    }
  });

  setActive(0);

  function onScrollParallax() {
    if (reduceMotion || parallaxPx === 0 || !bgLayer || !fgInner) return;
    var rect = root.getBoundingClientRect();
    var vh = window.innerHeight || 1;
    var progress = (rect.top + rect.height * 0.5 - vh * 0.5) / (vh + rect.height);
    progress = Math.max(0, Math.min(1, 0.5 - progress));
    var y1 = parallaxPx * (progress - 0.5) * 2;
    var y2 = -y1 * 0.65;
    bgLayer.style.transform = "scale(1.06) translateY(" + y1.toFixed(2) + "px)";
    fgInner.style.transform = "translateY(" + y2.toFixed(2) + "px)";
  }
  if (!reduceMotion) {
    window.addEventListener("scroll", onScrollParallax, { passive: true });
    onScrollParallax();
  }
})();
</script>
"""


def feature_showcase_body_html(items: list[dict[str, str]] | None = None) -> str:
    """Full main-column HTML for the Classic feature showcase page (includes CSS + JS)."""
    rows = items if items is not None else FEATURE_SHOWCASE_ITEMS
    if not rows:
        return '<p class="forge-support">No showcase items configured.</p>'

    first = rows[0]
    list_parts: list[str] = []
    for i, it in enumerate(rows):
        hid = _esc(str(it.get("id", str(i))))
        heading = _esc(str(it.get("heading", "")))
        summary = _esc(str(it.get("summary", "")))
        desc = str(it.get("description", "") or "").strip()
        desc_html = f'<p class="lenses-fs-card-desc">{_esc(desc)}</p>' if desc else ""
        cta_label = _esc(str(it.get("cta_label", "Learn more")))
        cta_href = _esc(str(it.get("cta_href", "#")))
        bg = _esc(str(it.get("bg", "")))
        main_u = _esc(str(it.get("main", "")))
        main_alt = _esc(str(it.get("main_alt", "")))
        pressed = "true" if i == 0 else "false"
        active_cls = " is-active" if i == 0 else ""
        list_parts.append(
            f'<div class="lenses-fs-item-wrap" role="listitem" id="lenses-fs-block-{hid}" '
            f'data-bg="{bg}" data-main="{main_u}" data-main-alt="{main_alt}" data-heading="{heading}">'
            f'<div class="lenses-fs-card{active_cls}">'
            f'<button type="button" class="lenses-fs-btn" aria-pressed="{pressed}" '
            'aria-controls="lenses-fs-panel">'
            f'<h3 class="lenses-fs-card-title">{heading}</h3>'
            f'<p class="lenses-fs-card-sum">{summary}</p>{desc_html}'
            "</button>"
            f'<a class="lenses-fs-cta" href="{cta_href}">{cta_label} →</a>'
            "</div></div>"
        )

    bg0 = _esc(str(first.get("bg", "")))
    main0 = _esc(str(first.get("main", "")))
    main_alt0 = _esc(str(first.get("main_alt", "")))

    return (
        FEATURE_SHOWCASE_CSS
        + f"""
<section class="lenses-fs" id="lenses-fs-root" aria-labelledby="lenses-fs-title">
  <h2 class="h3 text-cyan mb-2" id="lenses-fs-title">Why teams use lenses</h2>
  <p class="lenses-fs-lead forge-support mb-4">
    Scroll the list or select a feature — the preview updates with layered imagery and light motion.
    <span class="d-none d-lg-inline"> On smaller screens the preview stays at the top while you scroll.</span>
  </p>
  <p class="visually-hidden" id="lenses-fs-live" aria-live="polite" aria-atomic="true">{_esc(str(first.get("heading", "")))}</p>
  <div class="lenses-fs-grid">
    <div class="lenses-fs-col lenses-fs-col--list">
      <div role="list" aria-label="Features">
        {"".join(list_parts)}
      </div>
    </div>
    <div class="lenses-fs-col lenses-fs-col--visual">
      <div class="lenses-fs-sticky">
        <div id="lenses-fs-panel" class="lenses-fs-visual">
          <div class="lenses-fs-bg-layer">
            <img class="lenses-fs-bg" src="{bg0}" alt="" width="800" height="1000" decoding="async" />
          </div>
          <div class="lenses-fs-fg-layer">
            <div class="lenses-fs-fg-inner">
              <img class="lenses-fs-fg" src="{main0}" alt="{main_alt0}" width="800" height="600" decoding="async" />
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</section>
"""
        + FEATURE_SHOWCASE_JS
    )


def feature_showcase_items_json() -> str:
    """JSON for tooling/tests — same keys as FEATURE_SHOWCASE_ITEMS rows."""
    return json.dumps(FEATURE_SHOWCASE_ITEMS, indent=2)
