"""Client-side UI for /timeline (selectors + Plan deep links from Gantt bars)."""

from __future__ import annotations

FORGE_TIMELINE_SCRIPT = r"""
(function () {
  var repoSel = document.getElementById("lenses-timeline-repo");
  var wbsSel = document.getElementById("lenses-timeline-wbs");
  var rmSel = document.getElementById("lenses-timeline-roadmap");

  if (!wbsSel || !repoSel) return;

  function qsParse() {
    var o = {};
    var s = window.location.search.replace(/^\?/, "");
    if (!s) return o;
    s.split("&").forEach(function (pair) {
      var i = pair.indexOf("=");
      if (i < 0) return;
      var k = decodeURIComponent(pair.slice(0, i).replace(/\+/g, " "));
      var v = decodeURIComponent(pair.slice(i + 1).replace(/\+/g, " "));
      o[k] = v;
    });
    return o;
  }

  function filterSelect(sel, repo) {
    if (!sel) return;
    var i, opt;
    for (i = 0; i < sel.options.length; i++) {
      opt = sel.options[i];
      var dr = opt.getAttribute("data-repo") || "";
      if (!opt.value || !repo) {
        opt.hidden = false;
        continue;
      }
      opt.hidden = dr !== repo;
    }
  }

  function baseQuery() {
    var repo = repoSel ? repoSel.value : "";
    var wbs = wbsSel ? wbsSel.value : "";
    var rp = rmSel && rmSel.value ? rmSel.value : "";
    var q = "wbs_p=" + encodeURIComponent(wbs) + "&repo=" + encodeURIComponent(repo);
    if (rp) q += "&roadmap_p=" + encodeURIComponent(rp);
    return q;
  }

  function navigateTimeline() {
    var q = baseQuery();
    var path = "/timeline" + (q ? "?" + q : "");
    window.location.href = path;
  }

  function planUrlWithId(nodeId) {
    var q = baseQuery();
    if (nodeId) q += "&id=" + encodeURIComponent(nodeId);
    return "/plan?" + q;
  }

  if (repoSel) {
    repoSel.addEventListener("change", function () {
      filterSelect(wbsSel, repoSel.value);
      filterSelect(rmSel, repoSel.value);
      navigateTimeline();
    });
  }
  if (wbsSel) wbsSel.addEventListener("change", navigateTimeline);
  if (rmSel) rmSel.addEventListener("change", navigateTimeline);

  var q0 = qsParse();
  if (repoSel && q0.repo) repoSel.value = q0.repo;
  if (repoSel) filterSelect(wbsSel, repoSel.value);
  if (repoSel) filterSelect(rmSel, repoSel.value);
  if (wbsSel && q0.wbs_p) wbsSel.value = q0.wbs_p;
  if (rmSel && q0.roadmap_p) rmSel.value = q0.roadmap_p;

  document.addEventListener("click", function (ev) {
    var t = ev.target;
    if (!t || !t.closest) return;
    var bar = t.closest(".lenses-gantt-bar[data-lenses-node-id]");
    if (!bar) return;
    var id = bar.getAttribute("data-lenses-node-id");
    if (!id) return;
    ev.preventDefault();
    window.location.href = planUrlWithId(id);
  }, false);
})();
"""
