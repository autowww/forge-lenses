/* global fetch */
(function () {
  var root = document.getElementById("lenses-sticker-board-hub");
  if (!root) return;

  var api = root.getAttribute("data-registry-api") || "/api/sticker-board-registry";
  var projectFilter = (root.getAttribute("data-project-filter") || "").trim();
  var sharedAvailable =
    root.getAttribute("data-shared-available") === "true";
  var UNASSIGNED = "_unassigned";

  function postRegistry(action, payload) {
    return fetch(api, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: action, payload: payload || {} }),
    }).then(function (r) {
      return r.json();
    });
  }

  function projectLabel(slug) {
    if (slug === UNASSIGNED) return "Unassigned";
    return slug;
  }

  function flattenBoards(data) {
    var regProjects = data.projects || {};
    var out = [];
    Object.keys(regProjects).forEach(function (proj) {
      var boards = regProjects[proj] || [];
      boards.forEach(function (b) {
        out.push({ board: b, project: proj });
      });
    });
    out.sort(function (a, b) {
      var la = (a.board.label || "").toLowerCase();
      var lb = (b.board.label || "").toLowerCase();
      if (la < lb) return -1;
      if (la > lb) return 1;
      return (a.board.id || "").localeCompare(b.board.id || "");
    });
    return out;
  }

  function boardRow(b, proj, data) {
    var wrap = document.createElement("div");
    wrap.className = "lenses-sticker-hub-card";

    var thumb = document.createElement("div");
    thumb.className = "lenses-sticker-hub-thumb";
    if (b.preview_mtime != null && b.preview_mtime !== "") {
      var im = document.createElement("img");
      im.alt = "";
      im.src =
        "/board-preview/" +
        encodeURIComponent(b.id) +
        ".png?t=" +
        encodeURIComponent(String(b.preview_mtime));
      thumb.appendChild(im);
    } else {
      thumb.className += " lenses-sticker-hub-thumb--empty";
      thumb.textContent = "No preview";
    }
    wrap.appendChild(thumb);

    var main = document.createElement("div");
    main.className = "lenses-sticker-hub-main";

    var titleRow = document.createElement("div");
    titleRow.className = "lenses-sticker-hub-title-row";

    var badge = document.createElement("span");
    badge.className =
      b.storage === "shared"
        ? "lenses-sticker-hub-badge-shared"
        : "lenses-sticker-hub-badge-local";
    badge.textContent = b.storage === "shared" ? "Shared" : "Local only";

    var title = document.createElement("span");
    title.className = "fw-semibold";
    title.textContent = b.label || "Board";

    var pill = document.createElement("span");
    pill.className = "lenses-sticker-hub-project-pill";
    pill.textContent = projectLabel(proj);

    titleRow.appendChild(badge);
    titleRow.appendChild(title);
    titleRow.appendChild(pill);
    main.appendChild(titleRow);

    var idRow = document.createElement("div");
    idRow.className = "lenses-sticker-hub-id-row forge-support small";
    var idStr = b.id || "";
    var idShort =
      idStr.length > 14
        ? idStr.slice(0, 8) + "…" + idStr.slice(-4)
        : idStr;
    idRow.appendChild(document.createTextNode(idShort + " "));

    var copyBtn = document.createElement("button");
    copyBtn.type = "button";
    copyBtn.className = "btn btn-link btn-sm p-0 align-baseline";
    copyBtn.textContent = "Copy id";
    copyBtn.addEventListener("click", function () {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(idStr).catch(function () {});
      }
    });
    idRow.appendChild(copyBtn);
    main.appendChild(idRow);

    var actions = document.createElement("div");
    actions.className = "lenses-sticker-hub-actions";

    var openA = document.createElement("a");
    openA.className = "btn btn-sm btn-forge";
    openA.href = "/board/" + encodeURIComponent(b.id);
    openA.textContent = "Open";

    var renBtn = document.createElement("button");
    renBtn.type = "button";
    renBtn.className = "btn btn-sm btn-outline-secondary";
    renBtn.textContent = "Rename";
    renBtn.addEventListener("click", function () {
      var nl = window.prompt("New label", b.label || "");
      if (nl == null) return;
      nl = nl.trim();
      if (!nl) return;
      postRegistry("rename", { board_id: b.id, label: nl }).then(function (j) {
        if (j.ok) load();
        else window.alert(j.error || "Rename failed");
      });
    });

    var delBtn = document.createElement("button");
    delBtn.type = "button";
    delBtn.className = "btn btn-sm btn-outline-danger";
    delBtn.textContent = "Delete";
    delBtn.addEventListener("click", function () {
      if (
        !window.confirm(
          "Remove this board from the registry? Shared JSON under .lenses-repo is kept for reuse."
        )
      ) {
        return;
      }
      postRegistry("delete", { board_id: b.id }).then(function (j) {
        if (j.ok) load();
        else window.alert(j.error || "Delete failed");
      });
    });

    actions.appendChild(openA);
    actions.appendChild(renBtn);
    actions.appendChild(delBtn);

    var moveWrap = document.createElement("div");
    moveWrap.className = "lenses-sticker-hub-move d-flex flex-wrap gap-1 align-items-center";
    var assignSel = document.createElement("select");
    assignSel.className = "form-select form-select-sm";
    assignSel.style.maxWidth = "12rem";
    var optUn = document.createElement("option");
    optUn.value = UNASSIGNED;
    optUn.textContent = "Unassigned";
    assignSel.appendChild(optUn);
    var ap = data.workspace_projects || [];
    ap.forEach(function (p) {
      var o = document.createElement("option");
      o.value = p;
      o.textContent = p;
      assignSel.appendChild(o);
    });
    assignSel.value = proj;
    var asBtn = document.createElement("button");
    asBtn.type = "button";
    asBtn.className = "btn btn-sm btn-outline-info";
    asBtn.textContent = "Move to project";
    asBtn.addEventListener("click", function () {
      postRegistry("assign", {
        board_id: b.id,
        project: assignSel.value,
      }).then(function (j) {
        if (j.ok) load();
        else window.alert(j.error || "Move failed");
      });
    });
    moveWrap.appendChild(assignSel);
    moveWrap.appendChild(asBtn);
    actions.appendChild(moveWrap);

    wrap.appendChild(main);
    wrap.appendChild(actions);
    return wrap;
  }

  function renderHub(data) {
    root.innerHTML = "";
    var issues = data.validation_issues || [];
    if (issues.length) {
      var warn = document.createElement("p");
      warn.className = "text-warning small";
      warn.textContent = "Validation: " + issues.join("; ");
      root.appendChild(warn);
    }

    var toolbar = document.createElement("div");
    toolbar.className = "lenses-sticker-hub-toolbar";
    var refresh = document.createElement("button");
    refresh.type = "button";
    refresh.className = "btn btn-sm btn-outline-secondary";
    refresh.textContent = "Refresh";
    refresh.addEventListener("click", load);
    toolbar.appendChild(refresh);
    root.appendChild(toolbar);

    var createWrap = document.createElement("div");
    createWrap.className = "forge-card p-3 mb-3";
    createWrap.innerHTML =
      '<h3 class="h6 text-cyan mb-2">Create board</h3>';
    var row = document.createElement("div");
    row.className = "d-flex flex-wrap gap-2 align-items-end";

    var projSel = document.createElement("select");
    projSel.className = "form-select form-select-sm";
    projSel.style.maxWidth = "14rem";
    var projects = data.workspace_projects || [];
    var optU = document.createElement("option");
    optU.value = UNASSIGNED;
    optU.textContent = "Unassigned";
    projSel.appendChild(optU);
    projects.forEach(function (p) {
      var o = document.createElement("option");
      o.value = p;
      o.textContent = p;
      if (projectFilter && p === projectFilter) o.selected = true;
      projSel.appendChild(o);
    });
    if (projectFilter && projects.indexOf(projectFilter) >= 0) {
      projSel.value = projectFilter;
    }

    var labIn = document.createElement("input");
    labIn.type = "text";
    labIn.className = "form-control form-control-sm";
    labIn.placeholder = "Label";
    labIn.style.maxWidth = "16rem";

    var storSel = document.createElement("select");
    storSel.className = "form-select form-select-sm";
    storSel.style.maxWidth = "8rem";
    var oL = document.createElement("option");
    oL.value = "local";
    oL.textContent = "Local";
    storSel.appendChild(oL);
    var oS = document.createElement("option");
    oS.value = "shared";
    oS.textContent = "Shared";
    storSel.appendChild(oS);
    if (!sharedAvailable) {
      oS.disabled = true;
    }

    var createBtn = document.createElement("button");
    createBtn.type = "button";
    createBtn.className = "btn btn-sm btn-forge";
    createBtn.textContent = "Create";
    createBtn.addEventListener("click", function () {
      var label = (labIn.value || "").trim() || "New board";
      var storage = storSel.value;
      if (storage === "shared" && !sharedAvailable) {
        window.alert("Shared boards need a resolved GitHub login.");
        return;
      }
      postRegistry("create", {
        project: projSel.value,
        label: label,
        storage: storage,
      }).then(function (j) {
        if (j.ok && j.board_id) {
          window.location.href = "/board/" + encodeURIComponent(j.board_id);
        } else {
          window.alert(j.error || "Create failed");
        }
      });
    });

    row.appendChild(projSel);
    row.appendChild(labIn);
    row.appendChild(storSel);
    row.appendChild(createBtn);
    createWrap.appendChild(row);
    root.appendChild(createWrap);

    var filterWrap = document.createElement("div");
    filterWrap.className = "d-flex flex-wrap gap-2 align-items-center mb-3";
    var flab = document.createElement("span");
    flab.className = "small text-secondary";
    flab.textContent = "Show boards:";
    filterWrap.appendChild(flab);
    var filterSel = document.createElement("select");
    filterSel.className = "form-select form-select-sm";
    filterSel.style.maxWidth = "16rem";
    var optAll = document.createElement("option");
    optAll.value = "";
    optAll.textContent = "All projects";
    filterSel.appendChild(optAll);
    var optUnF = document.createElement("option");
    optUnF.value = UNASSIGNED;
    optUnF.textContent = "Unassigned only";
    filterSel.appendChild(optUnF);
    projects.forEach(function (p) {
      var o = document.createElement("option");
      o.value = p;
      o.textContent = p;
      filterSel.appendChild(o);
    });
    if (projectFilter && projects.indexOf(projectFilter) >= 0) {
      filterSel.value = projectFilter;
    } else if (projectFilter === UNASSIGNED) {
      filterSel.value = UNASSIGNED;
    }
    filterWrap.appendChild(filterSel);
    root.appendChild(filterWrap);

    var listHost = document.createElement("div");
    listHost.className = "lenses-sticker-hub-list";
    root.appendChild(listHost);

    function applyList() {
      listHost.innerHTML = "";
      var flat = flattenBoards(data);
      var fv = filterSel.value;
      var filtered =
        fv === ""
          ? flat
          : flat.filter(function (item) {
              return item.project === fv;
            });
      if (!filtered.length) {
        var empty = document.createElement("p");
        empty.className = "forge-support small mb-0";
        empty.textContent =
          fv === ""
            ? "No boards yet. Create one above."
            : "No boards in this filter.";
        listHost.appendChild(empty);
        return;
      }
      filtered.forEach(function (item) {
        listHost.appendChild(
          boardRow(item.board, item.project, data)
        );
      });
    }

    filterSel.addEventListener("change", applyList);
    applyList();
  }

  function load() {
    root.textContent = "Loading…";
    fetch(api)
      .then(function (r) {
        return r.json();
      })
      .then(function (data) {
        renderHub(data);
      })
      .catch(function (e) {
        root.textContent = "Failed to load registry: " + e;
      });
  }

  load();
})();
