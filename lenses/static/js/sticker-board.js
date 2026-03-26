/* global fetch */
(function () {
  var root = document.getElementById("lenses-sticker-board");
  if (!root) return;

  var api = root.getAttribute("data-api") || "/api/sticker-board";
  var sharedAvailable =
    root.getAttribute("data-shared-available") === "true";
  var state = null;
  var saveTimer = null;
  var statusEl = null;
  var sharedLoginWarn = false;

  function uid() {
    if (typeof crypto !== "undefined" && crypto.randomUUID) {
      return crypto.randomUUID();
    }
    return (
      "s-" +
      Date.now() +
      "-" +
      Math.random().toString(36).slice(2, 10)
    );
  }

  function previewText(body) {
    var t = (body || "").replace(/\s+/g, " ").trim();
    if (t.length > 160) return t.slice(0, 159) + "…";
    return t || "—";
  }

  function setStatus(msg) {
    if (statusEl) statusEl.textContent = msg || "";
  }

  function scheduleSave() {
    if (saveTimer) clearTimeout(saveTimer);
    saveTimer = setTimeout(doSave, 650);
  }

  function doSave() {
    saveTimer = null;
    setStatus("Saving…");
    var payload = JSON.parse(JSON.stringify(state));
    delete payload.shared_board_login_required;
    fetch(api, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    })
      .then(function (r) {
        return r.json();
      })
      .then(function (j) {
        if (j.ok) setStatus("Saved");
        else setStatus("Save failed: " + (j.error || JSON.stringify(j)));
      })
      .catch(function (e) {
        setStatus("Save error: " + e);
      });
  }

  function stickerById(id) {
    for (var i = 0; i < state.stickers.length; i++) {
      if (state.stickers[i].id === id) return state.stickers[i];
    }
    return null;
  }

  function sortStickersInColumn(colId) {
    var arr = state.stickers.filter(function (s) {
      return s.column_id === colId;
    });
    arr.sort(function (a, b) {
      return a.order - b.order;
    });
    return arr;
  }

  function deleteSticker(st) {
    if (!window.confirm("Delete this sticker?")) return;
    state.stickers = state.stickers.filter(function (s) {
      return s.id !== st.id;
    });
    closeModal();
    scheduleSave();
    render();
  }

  function closeModal() {
    var m = document.querySelector(".lenses-sticker-modal-backdrop");
    if (m) m.remove();
  }

  function openEditor(st) {
    closeModal();
    var back = document.createElement("div");
    back.className = "lenses-sticker-modal-backdrop";
    var box = document.createElement("div");
    box.className = "lenses-sticker-modal";
    box.addEventListener("click", function (e) {
      e.stopPropagation();
    });

    var h = document.createElement("h2");
    h.className = "h5 text-cyan mt-0";
    h.textContent = "Edit sticker";
    box.appendChild(h);

    var titleLab = document.createElement("label");
    titleLab.className = "form-label small";
    titleLab.textContent = "Title";
    box.appendChild(titleLab);
    var titleIn = document.createElement("input");
    titleIn.type = "text";
    titleIn.className = "form-control form-control-sm mb-2";
    titleIn.value = st.title || "";
    box.appendChild(titleIn);

    var bodyLab = document.createElement("label");
    bodyLab.className = "form-label small";
    bodyLab.textContent = "Details";
    box.appendChild(bodyLab);
    var bodyIn = document.createElement("textarea");
    bodyIn.className = "form-control form-control-sm mb-3";
    bodyIn.rows = 6;
    bodyIn.value = st.body || "";
    box.appendChild(bodyIn);

    var row = document.createElement("div");
    row.className = "d-flex flex-wrap gap-2 justify-content-between";
    var left = document.createElement("div");
    left.className = "d-flex flex-wrap gap-2";
    var saveBtn = document.createElement("button");
    saveBtn.type = "button";
    saveBtn.className = "btn btn-sm btn-forge";
    saveBtn.textContent = "Apply";
    saveBtn.addEventListener("click", function () {
      st.title = titleIn.value.trim() || "Untitled";
      st.body = bodyIn.value;
      closeModal();
      scheduleSave();
      render();
    });
    left.appendChild(saveBtn);
    var cancelBtn = document.createElement("button");
    cancelBtn.type = "button";
    cancelBtn.className = "btn btn-sm btn-outline-secondary";
    cancelBtn.textContent = "Cancel";
    cancelBtn.addEventListener("click", closeModal);
    left.appendChild(cancelBtn);
    row.appendChild(left);
    var delBtn = document.createElement("button");
    delBtn.type = "button";
    delBtn.className = "btn btn-sm btn-outline-danger";
    delBtn.textContent = "Delete";
    delBtn.addEventListener("click", function () {
      deleteSticker(st);
    });
    row.appendChild(delBtn);
    box.appendChild(row);

    back.appendChild(box);
    back.addEventListener("click", closeModal);
    document.body.appendChild(back);
    titleIn.focus();
  }

  function attachCardActions(card, st) {
    var actions = document.createElement("div");
    actions.className = "lenses-sticker-card-actions";
    var editBtn = document.createElement("button");
    editBtn.type = "button";
    editBtn.className = "btn btn-sm btn-outline-info";
    editBtn.setAttribute("aria-label", "Edit");
    editBtn.textContent = "✎";
    editBtn.addEventListener("click", function (e) {
      e.preventDefault();
      e.stopPropagation();
      openEditor(st);
    });
    var delBtn = document.createElement("button");
    delBtn.type = "button";
    delBtn.className = "btn btn-sm btn-outline-danger";
    delBtn.setAttribute("aria-label", "Delete");
    delBtn.textContent = "×";
    delBtn.addEventListener("click", function (e) {
      e.preventDefault();
      e.stopPropagation();
      deleteSticker(st);
    });
    actions.appendChild(editBtn);
    actions.appendChild(delBtn);
    card.appendChild(actions);
  }

  function renderCardFace(st, dblclick) {
    var card = document.createElement("div");
    card.className = "lenses-sticker-card";
    if (state.board_storage === "shared") {
      var scopeEl = document.createElement("div");
      scopeEl.className = "lenses-sticker-scope text-cyan";
      scopeEl.textContent = st.scope === "local" ? "Local" : "Shared";
      card.appendChild(scopeEl);
    }
    var t = document.createElement("div");
    t.className = "lenses-sticker-card-title";
    t.textContent = st.title || "Untitled";
    card.appendChild(t);
    var p = document.createElement("div");
    p.className = "lenses-sticker-card-preview forge-support";
    p.textContent = previewText(st.body);
    card.appendChild(p);
    attachCardActions(card, st);
    card.addEventListener("dblclick", function (e) {
      if (e.target.closest && e.target.closest(".lenses-sticker-card-actions")) return;
      e.preventDefault();
      e.stopPropagation();
      dblclick();
    });
    return card;
  }

  function newStickerBase(scope) {
    var col = null;
    if (state.template === "kanban" && state.columns[0]) {
      col = state.columns[0].id;
    }
    var maxOrder = 0;
    if (col) {
      state.stickers.forEach(function (s) {
        if (s.column_id === col && s.order > maxOrder) maxOrder = s.order;
      });
    }
    var nx = 24 + (state.stickers.length % 6) * 16;
    var ny = 24 + Math.floor(state.stickers.length / 6) * 88;
    var st = {
      id: uid(),
      title: "New sticker",
      body: "",
      column_id: col,
      order: col ? maxOrder + 1 : 0,
      x: nx,
      y: ny,
    };
    if (state.board_storage === "shared") {
      st.scope = scope || "shared";
    }
    return st;
  }

  function addSticker(scope) {
    var st = newStickerBase(scope);
    state.stickers.push(st);
    scheduleSave();
    render();
    openEditor(st);
  }

  function applyTemplate(tmpl) {
    if (state.stickers.length > 0) {
      if (
        !window.confirm(
          "Replace the board? This removes all stickers and columns."
        )
      ) {
        return;
      }
    }
    state.version = 2;
    state.stickers = [];
    state.template = tmpl;
    if (tmpl === "kanban") {
      state.columns = [
        { id: "todo", title: "To do" },
        { id: "doing", title: "Doing" },
        { id: "done", title: "Done" },
      ];
    } else {
      state.columns = [];
    }
    if (!state.board_storage) state.board_storage = "local";
    scheduleSave();
    render();
  }

  function setBoardStorage(bs) {
    if (bs === "shared") {
      if (state.board_storage === "shared") return;
      if (!sharedAvailable) {
        window.alert(
          "Shared board needs a resolved GitHub login (registry, single .lenses-repo/<login>/, or gh)."
        );
        return;
      }
      if (
        !window.confirm(
          "Switch to shared board? Existing stickers become shared (tracked under .lenses-repo) unless you edit scope when adding new ones."
        )
      ) {
        return;
      }
      state.board_storage = "shared";
      state.version = 2;
      state.stickers.forEach(function (s) {
        s.scope = "shared";
      });
      scheduleSave();
      render();
      return;
    }
    if (state.board_storage === "local") {
      render();
      return;
    }
    if (
      !window.confirm(
        "Switch to local board? All stickers are merged into your local-only file; shared/repo copy is not deleted."
      )
    ) {
      return;
    }
    state.board_storage = "local";
    state.version = 2;
    state.stickers.forEach(function (s) {
      delete s.scope;
    });
    scheduleSave();
    render();
  }

  function renderKanban(container) {
    var row = document.createElement("div");
    row.className = "lenses-sticker-kanban";
    state.columns.forEach(function (col) {
      var colEl = document.createElement("div");
      colEl.className = "lenses-sticker-column";
      var h = document.createElement("h3");
      h.textContent = col.title;
      colEl.appendChild(h);
      var body = document.createElement("div");
      body.className = "lenses-sticker-column-body";
      body.setAttribute("data-column-id", col.id);
      body.addEventListener("dragover", function (e) {
        e.preventDefault();
        body.classList.add("lenses-drag-over");
      });
      body.addEventListener("dragleave", function () {
        body.classList.remove("lenses-drag-over");
      });
      body.addEventListener("drop", function (e) {
        e.preventDefault();
        body.classList.remove("lenses-drag-over");
        var sid = e.dataTransfer.getData("text/plain");
        var st = stickerById(sid);
        if (!st) return;
        st.column_id = col.id;
        var siblings = sortStickersInColumn(col.id).filter(function (s) {
          return s.id !== sid;
        });
        st.order = siblings.length;
        scheduleSave();
        render();
      });

      sortStickersInColumn(col.id).forEach(function (st) {
        var card = renderCardFace(st, function () {
          openEditor(st);
        });
        card.setAttribute("draggable", "true");
        card.setAttribute("data-sticker-id", st.id);
        card.addEventListener("dragstart", function (e) {
          e.dataTransfer.setData("text/plain", st.id);
          e.dataTransfer.effectAllowed = "move";
        });
        card.addEventListener("dragend", function () {
          scheduleSave();
        });
        body.appendChild(card);
      });
      colEl.appendChild(body);
      row.appendChild(colEl);
    });
    container.appendChild(row);
  }

  function renderFreeform(container) {
    var canvas = document.createElement("div");
    canvas.className = "lenses-sticker-canvas";

    state.stickers.forEach(function (st) {
      var wrap = document.createElement("div");
      wrap.className = "lenses-sticker-float";
      wrap.style.left = (st.x || 0) + "px";
      wrap.style.top = (st.y || 0) + "px";

      var drag = { active: false, pid: null, sx: 0, sy: 0, ox: 0, oy: 0 };

      wrap.addEventListener("pointerdown", function (e) {
        if (e.button !== 0) return;
        if (e.target.closest && e.target.closest("button")) return;
        drag.active = true;
        drag.pid = e.pointerId;
        drag.sx = e.clientX;
        drag.sy = e.clientY;
        drag.ox = st.x || 0;
        drag.oy = st.y || 0;
        wrap.setPointerCapture(e.pointerId);
      });
      wrap.addEventListener("pointermove", function (e) {
        if (!drag.active || e.pointerId !== drag.pid) return;
        var dx = e.clientX - drag.sx;
        var dy = e.clientY - drag.sy;
        st.x = Math.max(0, drag.ox + dx);
        st.y = Math.max(0, drag.oy + dy);
        wrap.style.left = st.x + "px";
        wrap.style.top = st.y + "px";
      });
      wrap.addEventListener("pointerup", function (e) {
        if (!drag.active || e.pointerId !== drag.pid) return;
        drag.active = false;
        drag.pid = null;
        try {
          wrap.releasePointerCapture(e.pointerId);
        } catch (err) {
          /* ignore */
        }
        scheduleSave();
      });
      wrap.addEventListener("pointercancel", function (e) {
        drag.active = false;
        drag.pid = null;
        try {
          wrap.releasePointerCapture(e.pointerId);
        } catch (err2) {
          /* ignore */
        }
      });

      var card = renderCardFace(st, function () {
        openEditor(st);
      });
      wrap.appendChild(card);
      canvas.appendChild(wrap);
    });

    container.appendChild(canvas);
  }

  function renderToolbar(container) {
    var tb = document.createElement("div");
    tb.className = "lenses-sticker-toolbar";

    var bsLab = document.createElement("span");
    bsLab.className = "forge-support small me-1";
    bsLab.textContent = "Board:";
    tb.appendChild(bsLab);

    var locBtn = document.createElement("button");
    locBtn.type = "button";
    locBtn.className =
      "btn btn-sm " +
      (state.board_storage !== "shared" ? "btn-forge" : "btn-outline-secondary");
    locBtn.textContent = "Local";
    locBtn.addEventListener("click", function () {
      setBoardStorage("local");
    });
    tb.appendChild(locBtn);

    var shrBtn = document.createElement("button");
    shrBtn.type = "button";
    shrBtn.className =
      "btn btn-sm " +
      (state.board_storage === "shared" ? "btn-forge" : "btn-outline-secondary");
    shrBtn.textContent = "Shared";
    shrBtn.disabled = !sharedAvailable;
    shrBtn.title = sharedAvailable
      ? "Store shared stickers under .lenses-repo"
      : "Configure GitHub login for shared board";
    shrBtn.addEventListener("click", function () {
      setBoardStorage("shared");
    });
    tb.appendChild(shrBtn);

    if (state.board_storage === "shared") {
      var addLoc = document.createElement("button");
      addLoc.type = "button";
      addLoc.className = "btn btn-sm btn-outline-warning";
      addLoc.textContent = "Add local";
      addLoc.addEventListener("click", function () {
        addSticker("local");
      });
      tb.appendChild(addLoc);
      var addShr = document.createElement("button");
      addShr.type = "button";
      addShr.className = "btn btn-sm btn-outline-info";
      addShr.textContent = "Add shared";
      addShr.addEventListener("click", function () {
        addSticker("shared");
      });
      tb.appendChild(addShr);
    } else {
      var addBtn = document.createElement("button");
      addBtn.type = "button";
      addBtn.className = "btn btn-sm btn-forge";
      addBtn.textContent = "Add sticker";
      addBtn.addEventListener("click", function () {
        addSticker(null);
      });
      tb.appendChild(addBtn);
    }

    var saveBtn = document.createElement("button");
    saveBtn.type = "button";
    saveBtn.className = "btn btn-sm btn-outline-info";
    saveBtn.textContent = "Save now";
    saveBtn.addEventListener("click", function () {
      if (saveTimer) clearTimeout(saveTimer);
      saveTimer = null;
      doSave();
    });
    tb.appendChild(saveBtn);

    var kBtn = document.createElement("button");
    kBtn.type = "button";
    kBtn.className = "btn btn-sm btn-outline-secondary";
    kBtn.textContent = "Kanban template";
    kBtn.addEventListener("click", function () {
      applyTemplate("kanban");
    });
    tb.appendChild(kBtn);

    var fBtn = document.createElement("button");
    fBtn.type = "button";
    fBtn.className = "btn btn-sm btn-outline-secondary";
    fBtn.textContent = "Freeform template";
    fBtn.addEventListener("click", function () {
      applyTemplate("freeform");
    });
    tb.appendChild(fBtn);

    var mode = document.createElement("span");
    mode.className = "forge-support small ms-1";
    mode.textContent =
      state.template === "kanban" ? "· Kanban" : "· Freeform";
    tb.appendChild(mode);

    if (sharedLoginWarn) {
      var w = document.createElement("span");
      w.className = "text-warning small ms-2";
      w.textContent =
        "Shared board data needs login — configure registry or .lenses-repo.";
      tb.appendChild(w);
    }

    statusEl = document.createElement("span");
    statusEl.className = "lenses-sticker-status ms-2";
    tb.appendChild(statusEl);

    container.appendChild(tb);
  }

  function render() {
    root.innerHTML = "";
    renderToolbar(root);
    var main = document.createElement("div");
    if (state.template === "kanban") renderKanban(main);
    else renderFreeform(main);
    root.appendChild(main);
  }

  function hydrateState(j) {
    sharedLoginWarn = Boolean(j.shared_board_login_required);
    delete j.shared_board_login_required;
    state = j;
    var v = state.version;
    if (v === 1 || v == null) {
      state.version = 2;
      state.board_storage = state.board_storage || "local";
    }
    if (!state.board_storage) state.board_storage = "local";
    if (state.board_storage !== "shared" && state.board_storage !== "local") {
      state.board_storage = "local";
    }
    if (!state.stickers) state.stickers = [];
    if (!state.columns) state.columns = [];
    if (state.template !== "kanban" && state.template !== "freeform") {
      state.template = "freeform";
    }
    if (state.board_storage === "local") {
      state.stickers.forEach(function (s) {
        delete s.scope;
      });
    } else {
      state.stickers.forEach(function (s) {
        if (s.scope !== "local") s.scope = "shared";
      });
    }
  }

  function load() {
    fetch(api)
      .then(function (r) {
        return r.json();
      })
      .then(function (j) {
        hydrateState(j);
        render();
      })
      .catch(function (e) {
        root.textContent = "Failed to load board: " + e;
      });
  }

  load();
})();
