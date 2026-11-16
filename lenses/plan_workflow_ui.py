"""Client-side UI for the Forge /plan page (3-pane explorer)."""

from __future__ import annotations

# Full Plan tab behavior: tree + center + rail, keyboard nav, URL sync.
FORGE_PLAN_SCRIPT = r"""
(function () {
  var SYN_RM_SUMMARY = "__lenses_roadmap_summary__";
  var WORK_KINDS = { milestone: 1, epic: 1, story: 1, spark: 1 };

  var repoSel = document.getElementById("lenses-plan-repo");
  var wbsSel = document.getElementById("lenses-plan-wbs");
  var rmSel = document.getElementById("lenses-plan-roadmap");
  var treeHost = document.getElementById("lenses-plan-explorer-tree");
  var centerEl = document.getElementById("lenses-plan-explorer-center");
  var railEl = document.getElementById("lenses-plan-explorer-rail");
  var extraGroupsEl = document.getElementById("lenses-plan-extra-groups");
  var summaryEl = document.getElementById("lenses-plan-summary");
  var summaryDetails = document.getElementById("lenses-plan-summary-details");
  var searchEl = document.getElementById("lenses-plan-search");
  var srcFrame = document.getElementById("lenses-plan-source-frame");
  var tabPlan = document.getElementById("lenses-plan-tab-plan");
  var tabToday = document.getElementById("lenses-plan-tab-today");
  var tabSrc = document.getElementById("lenses-plan-tab-source");
  var panelPlan = document.getElementById("lenses-plan-panel-plan");
  var panelToday = document.getElementById("lenses-plan-panel-today");
  var panelSrc = document.getElementById("lenses-plan-panel-source");
  var todayContent = document.getElementById("lenses-today-content");
  var todayPhaseSel = document.getElementById("lenses-today-phase");

  if (!wbsSel || !treeHost || !centerEl || !railEl) return;

  var nodes = null;
  var rootIds = [];
  var sourcesPresent = {};
  var lastSpinePayload = null;
  var summaryHtmlCache = "";
  var selectedId = "";
  var selectedTab = "plan";
  var lastTodayPayload = null;
  var expanded = {};
  var treeFocusIndex = 0;
  var flatTreeItems = [];

  function qs() {
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

  function baseQuery() {
    var repo = repoSel ? repoSel.value : "";
    var wbs = wbsSel ? wbsSel.value : "";
    var rp = rmSel && rmSel.value ? rmSel.value : "";
    var q = "wbs_p=" + encodeURIComponent(wbs) + "&repo=" + encodeURIComponent(repo);
    if (rp) q += "&roadmap_p=" + encodeURIComponent(rp);
    return q;
  }

  function setUrl() {
    var q = new URLSearchParams();
    var repo = repoSel ? repoSel.value : "";
    var wbs = wbsSel ? wbsSel.value : "";
    var rm = rmSel ? rmSel.value : "";
    if (repo) q.set("repo", repo);
    if (wbs) q.set("wbs_p", wbs);
    if (rm) q.set("roadmap_p", rm);
    if (selectedId) q.set("id", selectedId);
    if (selectedTab === "today") q.set("tab", "today");
    else if (selectedTab === "source") q.set("tab", "source");
    var tail = q.toString();
    var path = window.location.pathname + (tail ? "?" + tail : "");
    if (window.history && window.history.replaceState) {
      window.history.replaceState({}, "", path);
    }
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

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/"/g, "&quot;");
  }

  function workChildren(parentId) {
    if (!nodes) return [];
    var out = [];
    Object.keys(nodes).forEach(function (nid) {
      var n = nodes[nid];
      if (!n || n.parent_id !== parentId) return;
      if (!WORK_KINDS[n.kind]) return;
      out.push(nid);
    });
    out.sort();
    return out;
  }

  function sparksForStory(sid) {
    return workChildren(sid).filter(function (cid) {
      return nodes[cid] && nodes[cid].kind === "spark";
    });
  }

  function hasDecisionRefs(n) {
    var x = n && n.extra && n.extra.decision_ref_ids;
    return x && x.length > 0;
  }

  function hasSessionRefs(n) {
    var x = n && n.extra && n.extra.session_ref_ids;
    return x && x.length > 0;
  }

  function storyHasBlocked(sid) {
    return sparksForStory(sid).some(function (sp) {
      return (nodes[sp].blockers || []).length > 0;
    });
  }

  function storyHasDecisions(sid) {
    var st = nodes[sid];
    if (hasDecisionRefs(st)) return true;
    return sparksForStory(sid).some(function (sp) {
      return hasDecisionRefs(nodes[sp]);
    });
  }

  function storyHasVersona(sid) {
    var st = nodes[sid];
    if (hasSessionRefs(st)) return true;
    return sparksForStory(sid).some(function (sp) {
      return hasSessionRefs(nodes[sp]);
    });
  }

  function filterChipsActive() {
    return (
      chipOn("blocked") ||
      chipOn("decisions") ||
      chipOn("versona")
    );
  }

  function chipOn(name) {
    var el = document.getElementById("lenses-filter-" + name);
    return el && el.classList.contains("active");
  }

  function searchQuery() {
    return searchEl && searchEl.value ? searchEl.value.trim().toLowerCase() : "";
  }

  /** Index text for search: id, title, status, phase, blockers, linked docs. */
  function nodeSearchBlob(id) {
    var n = nodes[id];
    if (!n) return "";
    var parts = [id, n.title || "", n.status || ""];
    var ex = n.extra || {};
    if (ex.phase) parts.push(ex.phase);
    if (ex.business_outcome) parts.push(ex.business_outcome);
    (n.blockers || []).forEach(function (b) { parts.push(b); });
    (ex.document_ref_ids || []).forEach(function (d) { parts.push(d); });
    if (ex.path) parts.push(ex.path);
    return parts.join(" ").toLowerCase();
  }

  function selfMatchesFilters(id) {
    var n = nodes[id];
    if (!n) return false;
    var q = searchQuery();
    if (q && nodeSearchBlob(id).indexOf(q) < 0) return false;
    if (!filterChipsActive()) return true;
    if (n.kind === "milestone" || n.kind === "epic") return false;
    if (n.kind === "story") {
      if (chipOn("blocked") && !storyHasBlocked(id)) return false;
      if (chipOn("decisions") && !storyHasDecisions(id)) return false;
      if (chipOn("versona") && !storyHasVersona(id)) return false;
      return true;
    }
    if (n.kind === "spark") {
      var sid = n.parent_id;
      if (!sid || !nodes[sid]) return false;
      if (chipOn("blocked") && !storyHasBlocked(sid)) return false;
      if (chipOn("decisions") && !storyHasDecisions(sid)) return false;
      if (chipOn("versona") && !storyHasVersona(sid)) return false;
      return true;
    }
    return true;
  }

  /* Subtree visible if this node matches search/filters or any descendant does (hide non-matching branches). */
  var visibleMemo = {};

  function subtreeVisible(id) {
    if (visibleMemo.hasOwnProperty(id)) return visibleMemo[id];
    var sm = selfMatchesFilters(id);
    var ch = workChildren(id);
    var childVis = false;
    for (var i = 0; i < ch.length; i++) {
      if (subtreeVisible(ch[i])) {
        childVis = true;
        break;
      }
    }
    visibleMemo[id] = sm || childVis;
    return visibleMemo[id];
  }

  function recomputeVisible() {
    visibleMemo = {};
    if (!nodes || !rootIds) return;
    rootIds.forEach(function (rid) { subtreeVisible(rid); });
  }

  function expandAncestors(id) {
    if (!nodes || !id || id === SYN_RM_SUMMARY) return;
    var cur = nodes[id];
    while (cur && cur.parent_id) {
      expanded[cur.parent_id] = true;
      cur = nodes[cur.parent_id];
    }
  }

  function ensureExpandedPath(id) {
    expandAncestors(id);
    rootIds.forEach(function (r) { expanded[r] = true; });
  }

  function toggleExpanded(id) {
    var open = expanded[id] !== false;
    expanded[id] = !open;
    renderWorkTree();
  }

  function labelForKind(kind) {
    if (kind === "milestone") return "Milestone";
    if (kind === "epic") return "Epic";
    if (kind === "story") return "Story";
    if (kind === "spark") return "Spark";
    return kind || "";
  }

  function renderTreeItem(id, depth) {
    var n = nodes[id];
    if (!n || !subtreeVisible(id)) return null;
    var ch = workChildren(id);
    var hasKids = ch.some(function (cid) { return subtreeVisible(cid); });
    var isOpen = expanded[id] !== false;
    if (depth === 0) isOpen = expanded[id] !== false;

    var li = document.createElement("li");
    li.setAttribute("role", "none");

    var row = document.createElement("div");
    row.className = "lenses-tree-row d-flex align-items-start gap-1 py-1";
    row.style.paddingLeft = depth * 12 + "px";

    var caret = document.createElement("span");
    caret.className = "lenses-tree-caret text-muted user-select-none";
    caret.style.minWidth = "1rem";
    if (hasKids) {
      caret.textContent = isOpen ? "▼" : "▶";
      caret.style.cursor = "pointer";
      caret.setAttribute("aria-hidden", "true");
      caret.onclick = function (e) {
        e.stopPropagation();
        toggleExpanded(id);
      };
    } else {
      caret.textContent = " ";
    }

    var ti = document.createElement("div");
    ti.setAttribute("role", "treeitem");
    ti.setAttribute("aria-expanded", hasKids ? String(isOpen) : undefined);
    ti.tabIndex = -1;
    ti.className = "lenses-tree-item flex-grow-1 rounded px-1";
    ti.dataset.nodeId = id;
    if (selectedId === id) {
      ti.classList.add("lenses-tree-item-active");
      ti.setAttribute("aria-selected", "true");
    } else {
      ti.setAttribute("aria-selected", "false");
    }
    var sparkNote = n.kind === "spark"
      ? " · " + (n.status || "") + (n.extra && n.extra.phase ? " · " + n.extra.phase : "")
      : "";
    ti.textContent = id + " · " + (n.title || "") + sparkNote;

    ti.onclick = function () {
      selectNode(id, true);
    };

    row.appendChild(caret);
    row.appendChild(ti);
    li.appendChild(row);

    if (hasKids && isOpen) {
      var ul = document.createElement("ul");
      ul.setAttribute("role", "group");
      ul.className = "list-unstyled mb-0";
      ch.forEach(function (cid) {
        var sub = renderTreeItem(cid, depth + 1);
        if (sub) ul.appendChild(sub);
      });
      li.appendChild(ul);
    }

    return li;
  }

  function renderWorkTree() {
    treeHost.innerHTML = "";
    recomputeVisible();
    if (!nodes || !rootIds.length) {
      treeHost.innerHTML =
        '<p class="lenses-plan-empty-title">No work hierarchy</p>' +
        '<p class="forge-support small mb-0">Parse WBS.md or pick another requirements file.</p>';
      return;
    }
    var tree = document.createElement("ul");
    tree.setAttribute("role", "tree");
    tree.className = "list-unstyled mb-0";
    tree.id = "lenses-work-tree-ul";
    rootIds.forEach(function (rid) {
      if (!subtreeVisible(rid)) return;
      var li = renderTreeItem(rid, 0);
      if (li) tree.appendChild(li);
    });
    treeHost.appendChild(tree);
    refreshFlatTreeItems();
    if (flatTreeItems.length) {
      var ae = document.activeElement;
      var keep = ae && treeHost.contains(ae) && ae.getAttribute("role") === "treeitem";
      if (!keep) {
        for (var fi = 0; fi < flatTreeItems.length; fi++) {
          flatTreeItems[fi].tabIndex = fi === 0 ? 0 : -1;
        }
      }
    }
  }

  function renderExtraGroups() {
    if (!extraGroupsEl || !nodes) return;
    extraGroupsEl.innerHTML = "";
    var rp = rmSel && rmSel.value;
    if (rp) {
      var rmBtn = document.createElement("button");
      rmBtn.type = "button";
      rmBtn.className = "btn btn-sm btn-outline-secondary w-100 mb-2";
      rmBtn.textContent = "Roadmap summary (metrics)";
      rmBtn.onclick = function () {
        if (!summaryHtmlCache && rmSel && rmSel.value) {
          fetch("/roadmaps/summary?p=" + encodeURIComponent(rmSel.value))
            .then(function (x) { return x.text(); })
            .then(function (html) {
              summaryHtmlCache = html;
              if (summaryEl) summaryEl.innerHTML = html;
              selectNode(SYN_RM_SUMMARY, true);
            })
            .catch(function () { selectNode(SYN_RM_SUMMARY, true); });
        } else {
          selectNode(SYN_RM_SUMMARY, true);
        }
      };
      extraGroupsEl.appendChild(rmBtn);
    }

    var docs = Object.keys(nodes).filter(function (nid) {
      return nodes[nid].kind === "documentRef";
    }).sort();
    if (docs.length) {
      var h = document.createElement("p");
      h.className = "small text-muted mb-1 mt-2";
      h.textContent = "Product docs";
      extraGroupsEl.appendChild(h);
      docs.forEach(function (did) {
        var b = document.createElement("button");
        b.type = "button";
        b.className = "btn btn-link btn-sm p-0 d-block text-start";
        b.textContent = nodes[did].title || did;
        b.onclick = function () { selectNode(did, true); };
        extraGroupsEl.appendChild(b);
      });
    }

    var ev = Object.keys(nodes).filter(function (nid) {
      var k = nodes[nid].kind;
      return k === "decisionRef" || k === "sessionRef";
    }).sort();
    if (ev.length) {
      var h2 = document.createElement("p");
      h2.className = "small text-muted mb-1 mt-2";
      h2.textContent = "Operational evidence";
      extraGroupsEl.appendChild(h2);
      ev.forEach(function (eid) {
        var b = document.createElement("button");
        b.type = "button";
        b.className = "btn btn-link btn-sm p-0 d-block text-start";
        b.textContent = (nodes[eid].kind === "decisionRef" ? "Decision · " : "Session · ") +
          (nodes[eid].title || eid).slice(0, 80);
        b.onclick = function () { selectNode(eid, true); };
        extraGroupsEl.appendChild(b);
      });
    }
  }

  function refreshFlatTreeItems() {
    flatTreeItems = treeHost.querySelectorAll('[role="treeitem"]');
  }

  function focusTreeItem(idx) {
    refreshFlatTreeItems();
    if (!flatTreeItems.length) return;
    if (idx < 0) idx = 0;
    if (idx >= flatTreeItems.length) idx = flatTreeItems.length - 1;
    treeFocusIndex = idx;
    for (var i = 0; i < flatTreeItems.length; i++) {
      flatTreeItems[i].tabIndex = i === idx ? 0 : -1;
    }
    flatTreeItems[idx].focus();
  }

  function onTreeKeydown(e) {
    var k = e.key;
    if (k !== "ArrowDown" && k !== "ArrowUp" && k !== "ArrowRight" && k !== "ArrowLeft" &&
        k !== "Enter" && k !== " " && k !== "Home" && k !== "End") return;
    refreshFlatTreeItems();
    if (!flatTreeItems.length) return;
    e.preventDefault();
    var cur = document.activeElement;
    var ix = -1;
    for (var i = 0; i < flatTreeItems.length; i++) {
      if (flatTreeItems[i] === cur) { ix = i; break; }
    }
    if (ix < 0) ix = 0;
    if (k === "ArrowDown") focusTreeItem(ix + 1);
    else if (k === "ArrowUp") focusTreeItem(ix - 1);
    else if (k === "Home") focusTreeItem(0);
    else if (k === "End") focusTreeItem(flatTreeItems.length - 1);
    else if (k === "Enter" || k === " ") {
      var id = flatTreeItems[ix].dataset.nodeId;
      if (id) selectNode(id, true);
    } else if (k === "ArrowRight") {
      var nid = flatTreeItems[ix].dataset.nodeId;
      if (nid && workChildren(nid).some(function (cid) { return subtreeVisible(cid); }) && expanded[nid] === false) {
        expanded[nid] = true;
        renderWorkTree();
        refreshFlatTreeItems();
        focusTreeItem(ix);
      }
    } else if (k === "ArrowLeft") {
      var nid2 = flatTreeItems[ix].dataset.nodeId;
      if (nid2 && workChildren(nid2).length && expanded[nid2] !== false) {
        expanded[nid2] = false;
        renderWorkTree();
        refreshFlatTreeItems();
        focusTreeItem(ix);
      }
    }
  }

  if (treeHost) {
    treeHost.addEventListener("keydown", onTreeKeydown);
  }

  var centerPane = document.querySelector(".lenses-plan-pane-center");
  var railPane = document.querySelector(".lenses-plan-pane-right");
  var explorerRow = document.getElementById("lenses-plan-explorer-row");
  var railToggle = document.getElementById("lenses-plan-rail-toggle");
  var RAIL_SS_KEY = "lenses-plan-rail-open";
  var storyLayoutMode = false;

  function readRailPref() {
    try {
      var v = sessionStorage.getItem(RAIL_SS_KEY);
      if (v === "1") return true;
      if (v === "0") return false;
    } catch (e) {}
    return window.matchMedia("(min-width: 992px)").matches;
  }
  var userRailOpen = readRailPref();

  function updateRailToggleUi() {
    if (!railToggle) return;
    if (storyLayoutMode) {
      railToggle.setAttribute("aria-expanded", "false");
      railToggle.textContent = "Detail (story view)";
      railToggle.disabled = true;
      return;
    }
    railToggle.disabled = false;
    railToggle.setAttribute("aria-expanded", userRailOpen ? "true" : "false");
    railToggle.textContent = userRailOpen ? "Hide detail" : "Show detail";
  }

  function applyRailCollapsedClass() {
    if (!explorerRow) return;
    if (storyLayoutMode) {
      explorerRow.classList.remove("lenses-plan-rail-collapsed");
      return;
    }
    explorerRow.classList.toggle("lenses-plan-rail-collapsed", !userRailOpen);
    updateRailToggleUi();
  }

  if (railToggle) {
    railToggle.addEventListener("click", function () {
      if (storyLayoutMode) return;
      userRailOpen = !userRailOpen;
      try {
        sessionStorage.setItem(RAIL_SS_KEY, userRailOpen ? "1" : "0");
      } catch (e) {}
      applyRailCollapsedClass();
    });
  }

  function setStoryLayoutMode(on) {
    storyLayoutMode = !!on;
    if (!centerPane || !railPane) return;
    if (on) {
      centerPane.classList.remove("col-lg-5");
      centerPane.classList.add("col-lg-9");
      railPane.classList.add("d-none");
      if (explorerRow) explorerRow.classList.add("lenses-plan-story-mode");
    } else {
      centerPane.classList.remove("col-lg-9");
      centerPane.classList.add("col-lg-5");
      railPane.classList.remove("d-none");
      if (explorerRow) explorerRow.classList.remove("lenses-plan-story-mode");
    }
    applyRailCollapsedClass();
    updateRailToggleUi();
  }

  function wireStoryTabs(host) {
    if (!host) return;
    var tabs = host.querySelectorAll("[data-lenses-story-tab]");
    var panels = host.querySelectorAll("[data-lenses-story-panel]");
    function activate(name) {
      var i = 0;
      var ti = 0;
      tabs.forEach(function (b) {
        var n = b.getAttribute("data-lenses-story-tab");
        var sel = n === name;
        b.classList.toggle("active", sel);
        b.setAttribute("aria-selected", sel ? "true" : "false");
        b.tabIndex = sel ? 0 : -1;
        if (sel) ti = i;
        i++;
      });
      panels.forEach(function (p) {
        var show = p.getAttribute("data-lenses-story-panel") === name;
        p.classList.toggle("d-none", !show);
        p.hidden = !show;
      });
    }
    tabs.forEach(function (btn, idx) {
      btn.addEventListener("click", function () {
        activate(btn.getAttribute("data-lenses-story-tab") || "");
      });
      btn.addEventListener("keydown", function (e) {
        var k = e.key;
        var len = tabs.length;
        if (k !== "ArrowRight" && k !== "ArrowLeft" && k !== "Home" && k !== "End") return;
        e.preventDefault();
        var next = idx;
        if (k === "ArrowRight") next = (idx + 1) % len;
        else if (k === "ArrowLeft") next = (idx - 1 + len) % len;
        else if (k === "Home") next = 0;
        else if (k === "End") next = len - 1;
        tabs[next].focus();
        activate(tabs[next].getAttribute("data-lenses-story-tab") || "");
      });
    });
  }

  function renderStoryCockpit(data) {
    var def = data.definition;
    var sv = data.story_view;
    var roadmapRel = data.roadmap_rel || "";
    if (!def) {
      centerEl.innerHTML =
        '<p class="lenses-plan-empty-title text-warning">No definition</p>' +
        '<p class="forge-support small mb-0">Select a story or spark in the work tree, or check WBS coverage for this id.</p>';
      return;
    }
    if (!sv) {
      var fb = [
        "<h3 class=\\"h6 text-cyan\\">" + esc(def.id || "") + " · " + esc(def.title || "") + "</h3>",
        '<p class="text-muted small mb-2">Structured story view unavailable — showing raw fields.</p>'
      ];
      if (def.acceptance_summary) fb.push('<p class="small">' + esc(def.acceptance_summary) + "</p>");
      centerEl.innerHTML = fb.join("");
      return;
    }
    var slots = (sv.slots) || {};
    var slotSection = function (key, label, forgeLab, slotObj) {
      if (!slotObj || !slotObj.text) return "";
      var inh = slotObj.inherited_from_milestone
        ? ' <span class="badge bg-secondary">Milestone</span>'
        : "";
      var provLines = [];
      (slotObj.sources || []).forEach(function (s) {
        var h = s.href || "";
        var cap = "WBS column «" + esc(s.header || "") + "»";
        if (h) {
          provLines.push(
            '<p class="forge-support small mb-0 mt-1 lenses-plan-canonical-line"><a href="' +
              esc(h) +
              '" class="link-info text-decoration-underline">Canonical: ' +
              cap +
              "</a></p>"
          );
        } else {
          provLines.push('<p class="forge-support small mb-0 mt-1">Source: ' + cap + "</p>");
        }
      });
      var prov = provLines.join("");
      return (
        '<section class="mb-3 lenses-plan-cockpit-section"><h4 class="h6 text-cyan mb-0">' +
        esc(label) +
        "</h4>" +
        '<p class="text-muted small mb-2 mb-md-1">' +
        esc(forgeLab) +
        inh +
        "</p>" +
        '<div class="small lenses-plan-slot-body">' +
        esc(slotObj.text).replace(/\\n/g, "<br/>") +
        "</div>" +
        prov +
        "</section>"
      );
    };
    var slotOrder = [
      ["problem", "Problem / rationale", "WBS semantic slot"],
      ["rationale", "Rationale", "WBS semantic slot"],
      ["user_visible_outcome", "User-visible outcome", "Outcome or milestone inheritance"],
      ["acceptance", "Acceptance criteria", "WBS acceptance row"],
      ["acceptance_route", "Acceptance route", "WBS column"],
      ["dependencies", "Dependencies", "WBS column"],
      ["constraints", "Constraints", "WBS column"],
      ["blockers", "Blockers", "WBS column"],
      ["evidence_of_done", "Evidence of done", "WBS column"],
      ["notes_unstructured", "Notes", "Unstructured cells"]
    ];
    var defParts = [];
    slotOrder.forEach(function (triple) {
      var k = triple[0];
      var lab = triple[1];
      var fl = triple[2];
      if (slots[k]) defParts.push(slotSection(k, lab, fl, slots[k]));
    });
    if (sv.milestone_outcome && sv.milestone_outcome.text) {
      var mo = sv.milestone_outcome;
      var mh = "";
      var ms0 = (mo.sources && mo.sources[0]) || {};
      if (ms0.href) {
        mh =
          '<p class="forge-support small mb-0 mt-2"><a href="' +
          esc(ms0.href) +
          '" class="link-info">Open milestone prose in WBS</a></p>';
      } else {
        mh = '<p class="forge-support small mb-0 mt-2">Source: milestone prose in WBS</p>';
      }
      defParts.push(
        '<section class="mb-3"><h4 class="h6 text-cyan mb-0">Milestone context</h4>' +
          '<p class="text-muted small mb-2">Milestone narrative · <span class="forge-support">WBS theme</span></p>' +
          '<div class="small">' +
          esc(mo.text).replace(/\\n/g, "<br/>") +
          "</div>" +
          mh +
          "</section>"
      );
    }
    if (sv.phase_affinity && sv.phase_affinity.length) {
      defParts.push(
        '<section class="mb-3"><h4 class="h6 text-cyan mb-0">Phase affinity</h4>' +
          '<p class="text-muted small mb-1">From task <span class="forge-support">phase</span> column</p>' +
          '<p class="small mb-0">' +
          esc(sv.phase_affinity.join(", ")) +
          "</p></section>"
      );
    }
    var defHtml = defParts.length
      ? defParts.join("")
      : '<p class="lenses-plan-empty-title">No structured fields</p>' +
        '<p class="forge-support small mb-0">Add columns to the story row in WBS or open the raw WBS from the Source tab.</p>';

    var prod = (sv.product_context) || [];
    var prodHtml = "";
    if (prod.length) {
      prodHtml = '<p class="text-muted small mb-2">Linked docs · <span class="forge-support">product graph</span></p><ul class="small mb-0">';
      prod.forEach(function (p) {
        var href = p.view_href || "#";
        prodHtml += '<li><a href="' + esc(href) + '">' + esc(p.title || p.path || p.id) + "</a>";
        if (p.path) prodHtml += ' <code class="ms-1">' + esc(p.path) + "</code>";
        prodHtml += "</li>";
      });
      prodHtml += "</ul>";
    } else {
      prodHtml =
        '<p class="lenses-plan-empty-title">No product links</p>' +
        '<p class="forge-support small mb-0">No linked product docs in the work graph yet.</p>';
    }

    var ex = (sv.execution) || {};
    var sparks = ex.sparks || [];
    var selSp = ex.selected_spark_id || "";
    var src = (sv.sources) || {};
    var execHtml = "";
    execHtml +=
      '<p class="text-muted small mb-2">Tasks & status · <span class="forge-support">Sparks & Charge</span></p>';
    if (src.charge) {
      execHtml +=
        '<p class="small mb-3"><a class="btn btn-sm btn-outline-info" href="' +
        esc(src.charge) +
        '">Open Charge file</a></p>';
    }
    if (sparks.length) {
      execHtml += '<ul class="small list-unstyled mb-3">';
      sparks.forEach(function (sp) {
        var hi = selSp && sp.id === selSp ? " border-info" : "";
        execHtml +=
          '<li class="mb-2 border-start border-secondary ps-2' +
          hi +
          '"><code>' +
          esc(sp.id) +
          "</code> — " +
          esc(sp.title || "") +
          (sp.phase ? " · " + esc(sp.phase) : "") +
          ((sp.blockers || []).length
            ? '<br/><span class="text-warning">Blockers: ' + esc((sp.blockers || []).join(", ")) + "</span>"
            : "") +
          "</li>";
      });
      execHtml += "</ul>";
    } else {
      execHtml += '<p class="forge-support small mb-3">No task rows in WBS for this story.</p>';
    }
    if (ex.charge_rows && ex.charge_rows.length) {
      execHtml +=
        '<p class="small fw-semibold mb-1">Charge rows <span class="text-muted fw-normal">(matching sparks)</span></p><ul class="small mb-0">';
      ex.charge_rows.forEach(function (c) {
        execHtml += "<li><code>" + esc(c.spark_id) + "</code> — " + esc(c.status || "") + "</li>";
      });
      execHtml += "</ul>";
    } else {
      execHtml += '<p class="forge-support small mb-0">No matching rows in forge/charge.md for this item.</p>';
    }

    var dec = (sv.decisions) || {};
    var decHtml = "";
    decHtml +=
      '<p class="text-muted small mb-2">Decisions & sessions · <span class="forge-support">Ember & Versona</span></p>';
    if (dec.graph_decisions && dec.graph_decisions.length) {
      decHtml += '<p class="small fw-semibold mb-1">Linked decisions (graph)</p><ul class="small">';
      dec.graph_decisions.forEach(function (d) {
        decHtml += '<li><a href="' + esc(d.view_href || "#") + '">' + esc(d.title || d.id) + "</a></li>";
      });
      decHtml += "</ul>";
    }
    if (dec.ember_scans && dec.ember_scans.length) {
      decHtml += '<p class="small fw-semibold mb-1">Ember log scans</p>';
      dec.ember_scans.forEach(function (e) {
        decHtml +=
          '<p class="small mb-1"><a href="' +
          esc(e.view_href || "#") +
          '">' +
          esc(e.file_rel || "") +
          "</a></p>" +
          '<pre class="small text-muted mb-2" style="max-height:6rem;overflow:auto">' +
          esc(e.snippet || "") +
          "</pre>";
      });
    }
    if (dec.graph_sessions && dec.graph_sessions.length) {
      decHtml += '<p class="small fw-semibold mb-1">Linked sessions (graph)</p><ul class="small">';
      dec.graph_sessions.forEach(function (s) {
        decHtml +=
          '<li><a href="' + esc(s.view_href || "#") + '">' + esc(s.session_id || s.title || s.id) + "</a></li>";
      });
      decHtml += "</ul>";
    }
    if (dec.versona_sessions && dec.versona_sessions.length) {
      decHtml += '<p class="small fw-semibold mb-1">Versona sessions</p><ul class="small mb-0">';
      dec.versona_sessions.forEach(function (s) {
        decHtml += '<li><a href="' + esc(s.view_href || "#") + '">' + esc(s.session_id || "") + "</a></li>";
      });
      decHtml += "</ul>";
    }
    var hasDec =
      (dec.graph_decisions && dec.graph_decisions.length) ||
      (dec.ember_scans && dec.ember_scans.length) ||
      (dec.graph_sessions && dec.graph_sessions.length) ||
      (dec.versona_sessions && dec.versona_sessions.length);
    if (!hasDec) {
      decHtml =
        '<p class="lenses-plan-empty-title">No linked evidence</p>' +
        '<p class="forge-support small mb-0">No decisions or sessions linked for this story in the graph or logs.</p>';
    }

    var srcHtml = "";
    if (src.wbs_view) {
      srcHtml +=
        '<p class="small mb-2"><a href="' +
        esc(src.wbs_view) +
        '">Open requirements / WBS</a> <span class="text-muted">· canonical</span></p>';
    }
    if (src.charge) {
      srcHtml +=
        '<p class="small mb-2"><a href="' +
        esc(src.charge) +
        '">Open Charge</a> <span class="text-muted">· forge/charge.md</span></p>';
    }
    if (roadmapRel && sv.roadmap_hits && sv.roadmap_hits.length) {
      var rCanon =
        "/roadmaps/preview?p=" + encodeURIComponent(roadmapRel);
      srcHtml +=
        '<p class="forge-support small mb-2">Canonical roadmap file: <a href="' +
        esc(rCanon) +
        '" class="link-info">' +
        esc(roadmapRel) +
        "</a></p>";
    }
    if (sv.roadmap_hits && sv.roadmap_hits.length) {
      srcHtml +=
        '<p class="small fw-semibold mb-1">Matching sections <span class="text-muted fw-normal">(excerpts)</span></p><ul class="small mb-2">';
      sv.roadmap_hits.forEach(function (rh) {
        srcHtml +=
          '<li><a href="' +
          esc(rh.preview_href || "#") +
          '" target="_blank" rel="noopener">' +
          esc(rh.title || rh.section_id) +
          "</a>" +
          '<div class="text-muted small">' +
          esc(rh.excerpt || "").slice(0, 240) +
          "</div></li>";
      });
      srcHtml += "</ul>";
    }
    if (src.journal && src.journal.length) {
      srcHtml += '<p class="small fw-semibold mb-1">Journal</p>';
      src.journal.forEach(function (j) {
        srcHtml +=
          '<p class="small mb-1"><a href="' +
          esc(j.view_href || "#") +
          '">' +
          esc(j.file_rel || "") +
          "</a></p>" +
          '<pre class="small text-muted mb-2" style="max-height:5rem;overflow:auto">' +
          esc((j.snippet || "").slice(0, 600)) +
          "</pre>";
      });
    }
    if (!srcHtml) {
      srcHtml =
        '<p class="lenses-plan-empty-title">No source links</p>' +
        '<p class="forge-support small mb-0">Add WBS, Charge, or roadmap under the selected repo.</p>';
    }

    var title = esc((def.id || "") + " · " + (def.title || ""));
    var tabs =
      '<div class="lenses-story-cockpit">' +
      '<h3 class="h6 text-cyan mb-1">' +
      title +
      "</h3>" +
      '<p class="text-muted small mb-3">Story cockpit · <span class="forge-support">synthesized from WBS + logs</span></p>' +
      '<ul class="nav nav-tabs flex-wrap mb-2" role="tablist" aria-label="Story cockpit tabs">' +
      '<li class="nav-item" role="presentation">' +
      '<button type="button" class="nav-link active" role="tab" aria-selected="true" tabindex="0" ' +
      'id="lens-cockpit-tab-def" aria-controls="lens-cockpit-panel-def" data-lenses-story-tab="def">' +
      'Definition <span class="forge-support fw-normal">· WBS</span></button></li>' +
      '<li class="nav-item" role="presentation">' +
      '<button type="button" class="nav-link" role="tab" aria-selected="false" tabindex="-1" ' +
      'id="lens-cockpit-tab-prod" aria-controls="lens-cockpit-panel-prod" data-lenses-story-tab="prod">' +
      'Product <span class="forge-support fw-normal">· docs</span></button></li>' +
      '<li class="nav-item" role="presentation">' +
      '<button type="button" class="nav-link" role="tab" aria-selected="false" tabindex="-1" ' +
      'id="lens-cockpit-tab-exe" aria-controls="lens-cockpit-panel-exe" data-lenses-story-tab="exe">' +
      'Execution <span class="forge-support fw-normal">· Sparks & Charge</span></button></li>' +
      '<li class="nav-item" role="presentation">' +
      '<button type="button" class="nav-link" role="tab" aria-selected="false" tabindex="-1" ' +
      'id="lens-cockpit-tab-dec" aria-controls="lens-cockpit-panel-dec" data-lenses-story-tab="dec">' +
      'Decisions <span class="forge-support fw-normal">· Ember & Versona</span></button></li>' +
      '<li class="nav-item" role="presentation">' +
      '<button type="button" class="nav-link" role="tab" aria-selected="false" tabindex="-1" ' +
      'id="lens-cockpit-tab-src" aria-controls="lens-cockpit-panel-src" data-lenses-story-tab="src">' +
      'Source <span class="forge-support fw-normal">· files</span></button></li>' +
      "</ul>" +
      '<div id="lens-cockpit-panel-def" role="tabpanel" aria-labelledby="lens-cockpit-tab-def" data-lenses-story-panel="def">' +
      defHtml +
      "</div>" +
      '<div id="lens-cockpit-panel-prod" class="d-none" role="tabpanel" aria-labelledby="lens-cockpit-tab-prod" hidden data-lenses-story-panel="prod">' +
      prodHtml +
      "</div>" +
      '<div id="lens-cockpit-panel-exe" class="d-none" role="tabpanel" aria-labelledby="lens-cockpit-tab-exe" hidden data-lenses-story-panel="exe">' +
      execHtml +
      "</div>" +
      '<div id="lens-cockpit-panel-dec" class="d-none" role="tabpanel" aria-labelledby="lens-cockpit-tab-dec" hidden data-lenses-story-panel="dec">' +
      decHtml +
      "</div>" +
      '<div id="lens-cockpit-panel-src" class="d-none" role="tabpanel" aria-labelledby="lens-cockpit-tab-src" hidden data-lenses-story-panel="src">' +
      srcHtml +
      "</div>" +
      "</div>";
    centerEl.innerHTML = tabs;
    wireStoryTabs(centerEl.querySelector(".lenses-story-cockpit"));
  }

  function loadStoryHub(id) {
    if (!id || !wbsSel.value) return;
    var repo = repoSel ? repoSel.value : "";
    var rp = rmSel && rmSel.value ? rmSel.value : "";
    var u = "/api/story-hub?id=" + encodeURIComponent(id) + "&wbs_p=" + encodeURIComponent(wbsSel.value) +
      "&repo=" + encodeURIComponent(repo);
    if (rp) u += "&roadmap_p=" + encodeURIComponent(rp);
    fetch(u)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (selectedId !== id) return;
        if (!data.ok) {
          centerEl.innerHTML = '<p class="text-warning small mb-0">Story hub could not be loaded.</p>';
          railEl.innerHTML = '<p class="forge-support small mb-0">Could not load detail.</p>';
          return;
        }
        renderStoryCockpit(data);
        railEl.innerHTML = '<p class="forge-support small text-muted mb-0">Story cockpit is in the center panel.</p>';
        setUrl();
      })
      .catch(function () {
        if (selectedId !== id) return;
        centerEl.innerHTML = '<p class="text-warning small mb-0">Failed to load story hub.</p>';
        railEl.innerHTML = '<p class="forge-support small mb-0">Load failed.</p>';
      });
  }

  function renderCenter() {
    if (!centerEl) return;
    if (selectedId === SYN_RM_SUMMARY) {
      setStoryLayoutMode(false);
      centerEl.innerHTML = '<div class="lenses-plan-roadmap-summary-in-center">' +
        (summaryHtmlCache || "<p class=\\"forge-support small\\">No roadmap summary.</p>") + "</div>";
      return;
    }
    if (!selectedId || !nodes || !nodes[selectedId]) {
      setStoryLayoutMode(false);
      centerEl.innerHTML = '<p class="forge-support text-muted mb-0">Select an item in the tree.</p>';
      return;
    }
    var n = nodes[selectedId];
    if (n.kind === "story" || n.kind === "spark") {
      setStoryLayoutMode(true);
      centerEl.innerHTML = '<p class="forge-support mb-0">Loading story cockpit…</p>';
      return;
    }
    setStoryLayoutMode(false);
    var h = [];

    if (n.kind === "milestone") {
      h.push("<h3 class=\\"h6 text-cyan\\">" + esc(n.id) + " · " + esc(n.title) + "</h3>");
      var bo = n.extra && n.extra.business_outcome;
      if (bo) {
        h.push('<div class="small mb-3 lenses-plan-md-muted">' + esc(bo).replace(/\\n/g, "<br/>") + "</div>");
      }
      h.push('<p class="small fw-semibold mb-1">Epics</p><ul class="small">');
      workChildren(selectedId).forEach(function (cid) {
        var c = nodes[cid];
        if (!c || c.kind !== "epic") return;
        h.push('<li><button type="button" class="btn btn-link btn-sm p-0 text-start lenses-plan-center-jump" data-jump="' + esc(cid) + '">' +
          esc(cid) + " · " + esc(c.title) + "</button></li>");
      });
      h.push("</ul>");
      centerEl.innerHTML = h.join("");
    } else if (n.kind === "epic") {
      h.push("<h3 class=\\"h6 text-cyan\\">" + esc(n.id) + " · " + esc(n.title) + "</h3>");
      h.push('<p class="small fw-semibold mb-1">Stories</p><ul class="small">');
      workChildren(selectedId).forEach(function (cid) {
        var c = nodes[cid];
        if (!c || c.kind !== "story") return;
        h.push('<li><button type="button" class="btn btn-link btn-sm p-0 text-start lenses-plan-center-jump" data-jump="' + esc(cid) + '">' +
          esc(cid) + " · " + esc(c.title) + "</button></li>");
      });
      h.push("</ul>");
      centerEl.innerHTML = h.join("");
    } else if (n.kind === "documentRef") {
      var pr = (n.provenance && n.provenance[0]) || {};
      var href = pr.view_href || "#";
      h.push("<h3 class=\\"h6 text-cyan\\">Product doc</h3>");
      h.push('<p class="small mb-0"><a href="' + esc(href) + '">' + esc(n.title || n.id) + "</a></p>");
      centerEl.innerHTML = h.join("");
    } else if (n.kind === "decisionRef" || n.kind === "sessionRef") {
      h.push("<h3 class=\\"h6 text-cyan\\">" + esc(labelForKind(n.kind)) + "</h3>");
      h.push("<p class=\\"small\\">" + esc(n.title || "") + "</p>");
      if (n.provenance && n.provenance[0] && n.provenance[0].view_href) {
        h.push('<p class="small"><a href="' + esc(n.provenance[0].view_href) + '">Open</a></p>');
      }
      centerEl.innerHTML = h.join("");
    } else {
      centerEl.innerHTML = "<p class=\\"small\\">" + esc(n.kind) + " · " + esc(n.title) + "</p>";
    }

    centerEl.querySelectorAll(".lenses-plan-center-jump").forEach(function (btn) {
      btn.onclick = function () {
        var j = btn.getAttribute("data-jump");
        if (j) selectNode(j, true);
      };
    });
  }

  function loadRailSelector(id) {
    railEl.innerHTML = '<p class="forge-support mb-0">Loading…</p>';
    fetch("/api/forge-work-model?" + baseQuery() + "&node_id=" + encodeURIComponent(id))
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (!data.ok) {
          railEl.innerHTML = '<p class="text-warning small mb-0">Detail not available.</p>';
          return;
        }
        var s = data.summary || {};
        var parts = [];
        parts.push('<section class="mb-3"><h4 class="h6 text-cyan">Summary</h4>');
        parts.push("<p class=\\"small mb-1\\"><strong>ID</strong> · " + esc(s.id) + "</p>");
        parts.push("<p class=\\"small mb-1\\"><strong>Kind</strong> · " + esc(s.kind || "") + "</p>");
        parts.push("<p class=\\"small mb-0\\"><strong>Title</strong> · " + esc(s.title || "") + "</p></section>");
        if (data.ancestors && data.ancestors.length) {
          parts.push('<section class="mb-3"><h4 class="h6 text-cyan">Ancestors</h4><ol class="small mb-0">');
          data.ancestors.forEach(function (a) {
            parts.push("<li>" + esc(a.id) + " · " + esc(a.title || "") + "</li>");
          });
          parts.push("</ol></section>");
        }
        if (data.children && data.children.length) {
          parts.push('<section class="mb-3"><h4 class="h6 text-cyan">Children</h4><ul class="small mb-0">');
          data.children.forEach(function (c) {
            parts.push("<li>" + esc(c.id) + " · " + esc(c.title || "") + "</li>");
          });
          parts.push("</ul></section>");
        }
        var rex = data.related_execution || {};
        if ((rex.charge || []).length) {
          parts.push("<section class=\\"mb-3\\"><h4 class=\\"h6 text-cyan\\">Execution</h4><ul class=\\"small\\">");
          (rex.charge || []).forEach(function (row) {
            var line = row.spark_id || row.status || "";
            parts.push("<li><code>" + esc(String(line)) + "</code></li>");
          });
          parts.push("</ul></section>");
        }
        var ev = data.related_evidence || {};
        if ((ev.decisions || []).length || (ev.sessions || []).length) {
          parts.push('<section class="mb-3"><h4 class="h6 text-cyan">Evidence</h4><ul class="small mb-0">');
          (ev.decisions || []).forEach(function (d) {
            parts.push("<li>" + esc(d.title || d.id) + "</li>");
          });
          (ev.sessions || []).forEach(function (d) {
            parts.push("<li>" + esc(d.title || d.id) + "</li>");
          });
          parts.push("</ul></section>");
        }
        railEl.innerHTML = parts.join("");
      })
      .catch(function () {
        railEl.innerHTML = '<p class="text-warning small mb-0">Failed to load detail.</p>';
      });
  }

  function selectNode(id, userAction) {
    selectedId = id || "";
    if (id && id !== SYN_RM_SUMMARY) ensureExpandedPath(id);
    renderWorkTree();
    renderExtraGroups();
    renderCenter();
    if (selectedId === SYN_RM_SUMMARY) {
      railEl.innerHTML = '<p class="forge-support small mb-0">Roadmap charts and tables (same as summary strip).</p>';
      setUrl();
      return;
    }
    if (!selectedId || !nodes || !nodes[selectedId]) {
      railEl.innerHTML = '<p class="forge-support text-muted mb-0">Select a work item.</p>';
      setUrl();
      return;
    }
    var nk = nodes[selectedId].kind;
    if (nk === "story" || nk === "spark") {
      railEl.innerHTML = '<p class="forge-support mb-0">Loading…</p>';
      loadStoryHub(selectedId);
    } else {
      loadRailSelector(selectedId);
    }
    setUrl();
    if (userAction) {
      refreshFlatTreeItems();
      var sel = '[data-node-id="' + String(selectedId).replace(/\\/g, "\\\\").replace(/"/g, '\\"') + '"]';
      var ti = treeHost.querySelector(sel);
      if (ti) ti.focus();
    }
  }

  function loadSpine() {
    var repo = repoSel ? repoSel.value : "";
    var wbs = wbsSel ? wbsSel.value : "";
    if (!wbs) {
      setStoryLayoutMode(false);
      treeHost.innerHTML =
        '<p class="lenses-plan-empty-title text-warning">Pick a WBS file</p>' +
        '<p class="forge-support small mb-0">Choose <strong>Requirements / WBS</strong> above to load the plan.</p>';
      if (summaryEl) summaryEl.innerHTML = "";
      centerEl.innerHTML = "";
      railEl.innerHTML = "";
      nodes = null;
      rootIds = [];
      lastSpinePayload = null;
      summaryHtmlCache = "";
      selectedId = "";
      return;
    }
    if (summaryEl) summaryEl.innerHTML = '<p class="forge-support small mb-0">Loading…</p>';
    summaryHtmlCache = "";
    var rp = rmSel && rmSel.value ? rmSel.value : "";
    var uSpine = "/api/plan-spine?wbs_p=" + encodeURIComponent(wbs) + "&repo=" + encodeURIComponent(repo) +
      (rp ? "&roadmap_p=" + encodeURIComponent(rp) : "");
    var uModel = "/api/forge-work-model?wbs_p=" + encodeURIComponent(wbs) + "&repo=" + encodeURIComponent(repo) +
      (rp ? "&roadmap_p=" + encodeURIComponent(rp) : "");

    Promise.all([
      fetch(uSpine).then(function (r) { return r.json(); }),
      fetch(uModel).then(function (r) { return r.json(); })
    ])
      .then(function (pair) {
        var data = pair[0];
        var wm = pair[1];
        if (!data.ok) {
          treeHost.innerHTML = '<p class="text-warning small">Could not load plan.</p>';
          return;
        }
        lastSpinePayload = data;
        if (rp && summaryEl) {
          fetch("/roadmaps/summary?p=" + encodeURIComponent(rp))
            .then(function (x) { return x.text(); })
            .then(function (html) {
              summaryHtmlCache = html;
              summaryEl.innerHTML = html;
              if (summaryDetails) summaryDetails.open = false;
            })
            .catch(function () {
              summaryEl.innerHTML = "";
              summaryHtmlCache = "";
            });
        } else if (summaryEl) {
          summaryEl.innerHTML = '<p class="forge-support small mb-0">No roadmap selected — work hierarchy comes from WBS only.</p>';
          summaryHtmlCache = "";
        }

        if (!wm || !wm.ok) {
          nodes = null;
          rootIds = [];
          expanded = {};
          renderWorkTree();
          renderExtraGroups();
          return;
        }
        nodes = wm.nodes || {};
        rootIds = wm.root_ids || [];
        sourcesPresent = wm.sources_present || {};
        expanded = {};
        rootIds.forEach(function (r) { expanded[r] = true; });
        renderWorkTree();
        renderExtraGroups();
        var q0 = qs();
        if (q0.id) {
          if (q0.id === SYN_RM_SUMMARY || nodes[q0.id]) {
            selectNode(q0.id, false);
          } else {
            selectedId = "";
            renderCenter();
            railEl.innerHTML = '<p class="forge-support text-muted mb-0">Details for the selected item.</p>';
          }
        } else {
          centerEl.innerHTML = '<p class="forge-support text-muted mb-0">Select an item in the tree.</p>';
          railEl.innerHTML = '<p class="forge-support text-muted mb-0">Details for the selected item.</p>';
        }
        setUrl();
        if (selectedTab === "today") loadTodayView();
      })
      .catch(function () {
        if (summaryEl) summaryEl.innerHTML = '<p class="text-warning small">Plan load failed.</p>';
        treeHost.innerHTML = '<p class="text-warning small">Plan load failed.</p>';
      });
  }

  function wireFilterChip(id) {
    var el = document.getElementById(id);
    if (!el) return;
    el.addEventListener("click", function () {
      el.classList.toggle("active");
      renderWorkTree();
    });
  }

  if (repoSel) {
    repoSel.addEventListener("change", function () {
      filterSelect(wbsSel, repoSel.value);
      filterSelect(rmSel, repoSel.value);
    });
  }
  if (wbsSel) wbsSel.addEventListener("change", loadSpine);
  if (rmSel) rmSel.addEventListener("change", loadSpine);

  wireFilterChip("lenses-filter-blocked");
  wireFilterChip("lenses-filter-decisions");
  wireFilterChip("lenses-filter-versona");

  if (searchEl) {
    searchEl.addEventListener("input", function () {
      renderWorkTree();
    });
  }

  function syncSourceFrame() {
    if (!srcFrame || !rmSel || !rmSel.value) {
      if (srcFrame) srcFrame.src = "about:blank";
      return;
    }
    fetch("/api/roadmap-outline?p=" + encodeURIComponent(rmSel.value))
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var sec = (data.sections && data.sections[0]) ? data.sections[0].id : "";
        if (sec) {
          srcFrame.src = "/roadmaps/preview?p=" + encodeURIComponent(rmSel.value) + "&section=" + encodeURIComponent(sec);
        }
      })
      .catch(function () { srcFrame.src = "about:blank"; });
  }

  function todayChipOn(name) {
    var el = document.getElementById("lenses-today-filter-" + name);
    return el && el.classList.contains("active");
  }

  function todayPhaseOk(row) {
    var v = todayPhaseSel && todayPhaseSel.value ? todayPhaseSel.value : "";
    if (!v) return true;
    return (row.phase_prefix || "") === v;
  }

  function todayChipOk(row) {
    var f = row.flags || {};
    var anyC =
      todayChipOn("blocked") || todayChipOn("banked") || todayChipOn("done");
    if (!anyC) return true;
    return (
      (todayChipOn("blocked") && f.blocked) ||
      (todayChipOn("banked") && f.banked) ||
      (todayChipOn("done") && f.done)
    );
  }

  function filterTodayRows(rows) {
    return (rows || []).filter(function (r) {
      return todayPhaseOk(r) && todayChipOk(r);
    });
  }

  function breadcrumbHtml(bc) {
    if (!bc || !bc.length) return "";
    var parts = [];
    for (var i = 0; i < bc.length; i++) {
      var x = bc[i];
      parts.push(
        '<span class="text-muted">' + esc(x.kind || "") + "</span> " +
        '<code class="small">' + esc(x.id || "") + "</code> " + esc(x.title || "")
      );
    }
    return '<div class="text-muted mb-1" style="font-size:0.8rem">' + parts.join(" · ") + "</div>";
  }

  function sparkRowTable(rows) {
    if (!rows || !rows.length) {
      return '<p class="forge-support small mb-0">No rows for this filter.</p>';
    }
    var h =
      '<table class="table table-sm table-bordered mb-0"><thead><tr>' +
      "<th>Work item</th><th>Owner</th><th>Blocker</th><th>Next action</th><th>Gaps</th>" +
      "</tr></thead><tbody>";
    rows.forEach(function (r) {
      var gaps = (r.gaps || []).join("; ");
      h +=
        "<tr><td>" +
        breadcrumbHtml(r.breadcrumb) +
        '<a href="' + esc(r.plan_href || "#") + '"><strong>' + esc(r.title || r.spark_id) + "</strong></a>" +
        '<div class="small text-muted mt-1">Spark <code>' + esc(r.spark_id) + "</code></div></td><td>" +
        esc(r.owner || "") +
        "</td><td>" +
        esc(r.blocker || "") +
        "</td><td>" +
        esc(r.next_action || "") +
        "</td><td>" +
        esc(gaps) +
        "</td></tr>";
    });
    h += "</tbody></table>";
    return h;
  }

  function versonaTable(sessions) {
    if (!sessions || !sessions.length) {
      return '<p class="text-muted mb-0">None pending.</p>';
    }
    var h =
      '<table class="table table-sm table-bordered mb-0"><thead><tr>' +
      "<th>Session</th><th>Refs</th><th>Open</th>" +
      "</tr></thead><tbody>";
    sessions.forEach(function (s) {
      var links = (s.plan_links || [])
        .map(function (pl) {
          return '<a href="' + esc(pl.plan_href || "#") + '"><code>' + esc(pl.id) + "</code></a>";
        })
        .join(" ");
      h +=
        "<tr><td>" +
        esc(s.session_id || "") +
        '</td><td class="small">' +
        esc((s.work_item_refs || []).join(", ")) +
        "</td><td>" +
        (s.view_href
          ? '<a href="' + esc(s.view_href) + '">Session file</a>'
          : "") +
        " " +
        links +
        "</td></tr>";
    });
    h += "</tbody></table>";
    return h;
  }

  function renderTodayPayload(data) {
    if (!todayContent) return;
    lastTodayPayload = data;
    var ch = data.charge || {};
    var note = (data.notes && data.notes.recently_resolved_scope) || "";
    var headBits = [];
    if (ch.view_href) {
      headBits.push('<a href="' + esc(ch.view_href) + '">Open Charge</a>');
    }
    if (ch.hat) headBits.push("Hat: <strong>" + esc(ch.hat) + "</strong>");
    if (ch.date) headBits.push(esc(ch.date));
    var head = headBits.length
      ? '<p class="small mb-2">' + headBits.join(" · ") + "</p>"
      : "";
    var sec = data.sections || {};
    var fr = filterTodayRows;
    var html = head;
    html +=
      '<section class="mb-4"><h3 class="h6 lenses-today-section-title mb-2">In progress ' +
      '<span class="text-muted small fw-normal">(Active Sparks)</span></h3>' +
      sparkRowTable(fr(sec.active || [])) +
      "</section>";
    html +=
      '<section class="mb-4"><h3 class="h6 lenses-today-section-title mb-2">Blocked ' +
      '<span class="text-muted small fw-normal">(Sparks)</span></h3>' +
      sparkRowTable(fr(sec.blocked || [])) +
      "</section>";
    html +=
      '<section class="mb-4"><h3 class="h6 lenses-today-section-title mb-2">Banked ' +
      '<span class="text-muted small fw-normal">(parked)</span></h3>' +
      sparkRowTable(fr(sec.banked || [])) +
      "</section>";
    html +=
      '<section class="mb-4"><h3 class="h6 lenses-today-section-title mb-2">Pending discipline sessions ' +
      '<span class="text-muted small fw-normal">(Versona)</span></h3>' +
      versonaTable(sec.pending_versona || []) +
      "</section>";
    html +=
      '<section class="mb-2"><h3 class="h6 lenses-today-section-title mb-2">Recently done ' +
      '<span class="text-muted small fw-normal">(Charge status)</span></h3>' +
      (note ? '<p class="small text-muted mb-2">' + esc(note) + "</p>" : "") +
      sparkRowTable(fr(sec.recently_resolved || [])) +
      "</section>";
    todayContent.innerHTML = html;
  }

  function fillTodayPhaseSelect(prefixes) {
    if (!todayPhaseSel) return;
    var cur = todayPhaseSel.value || "";
    todayPhaseSel.innerHTML = '<option value="">All</option>';
    (prefixes || []).forEach(function (p) {
      var o = document.createElement("option");
      o.value = p;
      o.textContent = p;
      todayPhaseSel.appendChild(o);
    });
    if (cur && [].some.call(todayPhaseSel.options, function (opt) { return opt.value === cur; })) {
      todayPhaseSel.value = cur;
    }
  }

  function loadTodayView() {
    if (!todayContent || !wbsSel || !wbsSel.value) {
      if (todayContent) {
        todayContent.innerHTML = '<p class="text-muted small mb-0">Select a WBS file.</p>';
      }
      return;
    }
    todayContent.innerHTML = '<p class="forge-support small mb-0">Loading Today…</p>';
    var repo = repoSel ? repoSel.value : "";
    var rp = rmSel && rmSel.value ? rmSel.value : "";
    var u =
      "/api/today-charge?wbs_p=" + encodeURIComponent(wbsSel.value) +
      "&repo=" + encodeURIComponent(repo);
    if (rp) u += "&roadmap_p=" + encodeURIComponent(rp);
    fetch(u)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (!data.ok) {
          todayContent.innerHTML =
            '<p class="text-warning small mb-0">Could not load Today view.</p>';
          return;
        }
        fillTodayPhaseSelect(data.phase_prefixes || []);
        renderTodayPayload(data);
      })
      .catch(function () {
        if (todayContent) {
          todayContent.innerHTML =
            '<p class="text-warning small mb-0">Failed to load Today view.</p>';
        }
      });
  }

  function showTab(which) {
    selectedTab = which || "plan";
    function setMainTabUi(active) {
      var tabs = [tabPlan, tabToday, tabSrc];
      var names = ["plan", "today", "source"];
      var panels = [panelPlan, panelToday, panelSrc];
      for (var i = 0; i < 3; i++) {
        var on = names[i] === active;
        if (tabs[i]) {
          tabs[i].classList.toggle("active", on);
          tabs[i].setAttribute("aria-selected", on ? "true" : "false");
          tabs[i].tabIndex = on ? 0 : -1;
        }
        if (panels[i]) {
          panels[i].classList.toggle("d-none", !on);
          panels[i].hidden = !on;
        }
      }
    }
    if (which === "source") {
      setMainTabUi("source");
      syncSourceFrame();
    } else if (which === "today") {
      setMainTabUi("today");
      loadTodayView();
    } else {
      setMainTabUi("plan");
    }
    setUrl();
  }

  function wireMainTabKeydown(btn, name, prevFn, nextFn) {
    if (!btn) return;
    btn.addEventListener("keydown", function (e) {
      var k = e.key;
      if (k === "ArrowRight" || k === "ArrowLeft") {
        e.preventDefault();
        if (k === "ArrowRight") nextFn();
        else prevFn();
      }
    });
  }
  if (tabPlan) {
    tabPlan.addEventListener("click", function () { showTab("plan"); });
    wireMainTabKeydown(tabPlan, "plan", function () { showTab("source"); }, function () { showTab("today"); });
  }
  if (tabToday) {
    tabToday.addEventListener("click", function () { showTab("today"); });
    wireMainTabKeydown(tabToday, "today", function () { showTab("plan"); }, function () { showTab("source"); });
  }
  if (tabSrc) {
    tabSrc.addEventListener("click", function () { showTab("source"); });
    wireMainTabKeydown(tabSrc, "source", function () { showTab("today"); }, function () { showTab("plan"); });
  }

  if (todayPhaseSel) {
    todayPhaseSel.addEventListener("change", function () {
      if (lastTodayPayload) renderTodayPayload(lastTodayPayload);
    });
  }
  ["blocked", "banked", "done"].forEach(function (name) {
    var el = document.getElementById("lenses-today-filter-" + name);
    if (el) {
      el.addEventListener("click", function () {
        el.classList.toggle("active");
        if (lastTodayPayload) renderTodayPayload(lastTodayPayload);
      });
    }
  });

  var q0 = qs();
  if (repoSel && q0.repo) repoSel.value = q0.repo;
  if (repoSel) filterSelect(wbsSel, repoSel.value);
  if (repoSel) filterSelect(rmSel, repoSel.value);
  if (wbsSel && q0.wbs_p) wbsSel.value = q0.wbs_p;
  if (rmSel && q0.roadmap_p) rmSel.value = q0.roadmap_p;
  if (q0.tab === "today") showTab("today");
  else if (q0.tab === "source") showTab("source");
  else showTab("plan");
  applyRailCollapsedClass();
  if (wbsSel && wbsSel.value) loadSpine();
})();
"""
