"""Inject a click bridge so preview iframes do not navigate to Classic Lenses routes in-frame."""

from __future__ import annotations

# Loaded only when parent !== window; posts same-origin navigations to Studio SPA.
_STUDIO_IFRAME_NAV_BRIDGE_JS = r"""
(function () {
  if (window.parent === window) return;
  document.addEventListener(
    "click",
    function (e) {
      if (e.defaultPrevented || e.button !== 0) return;
      if (e.ctrlKey || e.metaKey || e.shiftKey || e.altKey) return;
      var el = e.target && e.target.closest("a[href]");
      if (!el || el.hasAttribute("download")) return;
      var raw = el.getAttribute("href");
      if (!raw || /^\s*#/.test(raw) || /^javascript:/i.test(raw.trim())) return;
      var u;
      try {
        u = new URL(raw, window.location.href);
      } catch (err) {
        return;
      }
      if (u.origin !== window.location.origin) return;
      var p = u.pathname;
      var msg = {
        type: "lenses-studio-same-origin-nav",
        pathname: p,
        search: u.search || "",
        hash: u.hash || "",
      };
      function send() {
        e.preventDefault();
        window.parent.postMessage(msg, window.location.origin);
      }
      if (p === "/" || p === "/projects" || p.startsWith("/projects/")) {
        send();
        return;
      }
      if (
        p === "/tutorials" ||
        p === "/search" ||
        p === "/websites" ||
        p === "/websites/browse" ||
        p.startsWith("/websites/browse/")
      ) {
        send();
        return;
      }
      if (p === "/view/docs" || p.startsWith("/view/docs/")) {
        send();
        return;
      }
      if (p.startsWith("/view/local-site/")) {
        send();
        return;
      }
      if (p === "/docs" || p.startsWith("/docs/")) {
        e.preventDefault();
        var tail = "";
        if (p.startsWith("/docs/")) tail = p.slice("/docs/".length);
        msg.pathname = "/view/docs" + (tail ? "/" + tail : "");
        window.parent.postMessage(msg, window.location.origin);
        return;
      }
      if (p.startsWith("/local-site/")) {
        e.preventDefault();
        msg.pathname = "/view" + p;
        window.parent.postMessage(msg, window.location.origin);
        return;
      }
      if (p === "/studio" || p.startsWith("/studio/")) {
        e.preventDefault();
        var rest = p === "/studio" ? "" : p.slice("/studio/".length);
        msg.pathname = rest ? "/" + rest : "/";
        window.parent.postMessage(msg, window.location.origin);
        return;
      }
    },
    true,
  );
})();
""".strip()


def inject_studio_iframe_nav_bridge(html_bytes: bytes) -> bytes:
    """Append a script before ``</body>`` so embedded previews delegate Lenses routes to the parent shell."""
    try:
        text = html_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return html_bytes
    if "lenses-studio-embed-nav-bridge" in text:
        return html_bytes
    tag = (
        '<script id="lenses-studio-embed-nav-bridge">\n'
        + _STUDIO_IFRAME_NAV_BRIDGE_JS
        + "\n</script>\n"
    )
    low = text.lower()
    idx = low.rfind("</body>")
    if idx >= 0:
        out = text[:idx] + tag + text[idx:]
    else:
        out = text + tag
    return out.encode("utf-8")
