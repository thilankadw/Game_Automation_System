// ROI capture overlay injected by the backend into the game page.
//
// The overlay floats above the live game so the user can keep playing spins
// while still marking rectangular regions for canvas, spin button, balance,
// bet, and win. It deliberately never screenshots the page: rectangles are
// drawn on top of the running game and reported back through the
// `__roiCapture` binding exposed by Playwright.
(function () {
  "use strict";

  if (window.top !== window.self) {
    return;
  }
  if (window.__roiCaptureOverlay) {
    return;
  }
  window.__roiCaptureOverlay = true;

  var ROI_TYPES = [
    { value: "canvas", label: "Canvas", color: "#38bdf8" },
    { value: "spin_button", label: "Spin button", color: "#a3e635" },
    { value: "balance", label: "Balance", color: "#fbbf24" },
    { value: "bet", label: "Bet", color: "#f472b6" },
    { value: "win", label: "Win", color: "#34d399" },
  ];

  var COLORS = {};
  ROI_TYPES.forEach(function (type) {
    COLORS[type.value] = type.color;
  });

  var state = {
    mode: "play",
    activeType: "canvas",
    rects: {},
    roiSets: [],
    selectedSetId: "",
    existingSetId: null,
    sessionId: null,
    busy: false,
  };

  var drag = null;

  var root = document.createElement("div");
  root.id = "__roiCaptureRoot";
  root.style.cssText = [
    "position:fixed",
    "inset:0",
    "z-index:2147483000",
    "pointer-events:none",
    "font-family:ui-sans-serif,system-ui,Segoe UI,sans-serif",
    "font-size:12px",
    "color:#e2e8f0",
  ].join(";");

  var layer = document.createElement("div");
  layer.style.cssText = [
    "position:fixed",
    "inset:0",
    "pointer-events:none",
  ].join(";");

  var panel = document.createElement("div");
  panel.style.cssText = [
    "position:fixed",
    "top:12px",
    "left:12px",
    "width:264px",
    "pointer-events:auto",
    "background:rgba(15,23,42,0.95)",
    "border:1px solid #334155",
    "border-radius:10px",
    "box-shadow:0 12px 32px rgba(0,0,0,0.45)",
    "padding:12px",
  ].join(";");

  var title = document.createElement("div");
  title.textContent = "ROI capture";
  title.style.cssText =
    "font-weight:600;font-size:13px;margin-bottom:8px;color:#f8fafc";

  var modeRow = document.createElement("div");
  modeRow.style.cssText = "display:flex;gap:6px;margin-bottom:8px";

  var playBtn = makeButton("Play spins", "play");
  var drawBtn = makeButton("Draw ROI", "draw");
  modeRow.appendChild(playBtn);
  modeRow.appendChild(drawBtn);

  var typeLabel = document.createElement("label");
  typeLabel.textContent = "Region";
  typeLabel.style.cssText = "display:block;margin-bottom:4px;color:#94a3b8";

  var typeSelect = document.createElement("select");
  typeSelect.style.cssText =
    "width:100%;margin-bottom:8px;padding:5px;border-radius:6px;" +
    "background:#1e293b;color:#e2e8f0;border:1px solid #334155";
  ROI_TYPES.forEach(function (type) {
    var option = document.createElement("option");
    option.value = type.value;
    option.textContent = type.label;
    typeSelect.appendChild(option);
  });

  var hint = document.createElement("div");
  hint.style.cssText = "color:#94a3b8;margin-bottom:8px;line-height:1.4";

  var list = document.createElement("div");
  list.style.cssText = "margin-bottom:8px";

  var setLabel = document.createElement("label");
  setLabel.textContent = "Save into ROI set";
  setLabel.style.cssText = "display:block;margin-bottom:4px;color:#94a3b8";

  var setSelect = document.createElement("select");
  setSelect.style.cssText =
    "width:100%;margin-bottom:8px;padding:5px;border-radius:6px;" +
    "background:#1e293b;color:#e2e8f0;border:1px solid #334155";

  var actionRow = document.createElement("div");
  actionRow.style.cssText = "display:flex;gap:6px";

  var saveBtn = makeButton("Save ROIs", "accent");
  var closeBtn = makeButton("Close", "danger");
  actionRow.appendChild(saveBtn);
  actionRow.appendChild(closeBtn);

  var status = document.createElement("div");
  status.style.cssText = "margin-top:8px;color:#94a3b8;min-height:14px";

  panel.appendChild(title);
  panel.appendChild(modeRow);
  panel.appendChild(typeLabel);
  panel.appendChild(typeSelect);
  panel.appendChild(hint);
  panel.appendChild(list);
  panel.appendChild(setLabel);
  panel.appendChild(setSelect);
  panel.appendChild(actionRow);
  panel.appendChild(status);

  root.appendChild(layer);
  root.appendChild(panel);

  function makeButton(label, variant) {
    var button = document.createElement("button");
    button.type = "button";
    button.textContent = label;
    button.style.cssText = [
      "flex:1",
      "padding:6px 8px",
      "border-radius:6px",
      "border:1px solid #334155",
      "cursor:pointer",
      "font-size:12px",
      "background:#1e293b",
      "color:#e2e8f0",
    ].join(";");
    button.dataset.variant = variant;
    return button;
  }

  function api(action, payload) {
    if (typeof window.__roiCapture !== "function") {
      return Promise.reject(new Error("Capture bridge is unavailable"));
    }
    return window.__roiCapture(action, payload || {});
  }

  function setStatus(message) {
    status.textContent = message || "";
  }

  function applyMode() {
    var drawing = state.mode === "draw";
    layer.style.pointerEvents = drawing ? "auto" : "none";
    layer.style.cursor = drawing ? "crosshair" : "default";
    playBtn.style.background = drawing ? "#1e293b" : "#2563eb";
    drawBtn.style.background = drawing ? "#2563eb" : "#1e293b";
    hint.textContent = drawing
      ? "Drag over the game to mark the selected region."
      : "Clicks pass through to the game so you can play spins.";
  }

  function renderList() {
    list.innerHTML = "";
    ROI_TYPES.forEach(function (type) {
      var rect = state.rects[type.value];
      var row = document.createElement("div");
      row.style.cssText =
        "display:flex;align-items:center;gap:6px;margin-bottom:4px";

      var swatch = document.createElement("span");
      swatch.style.cssText =
        "width:10px;height:10px;border-radius:2px;flex:0 0 auto;" +
        "background:" +
        type.color;

      var text = document.createElement("span");
      text.style.cssText = "flex:1";
      text.textContent = rect
        ? type.label + ": " + rect.x + "," + rect.y +
          " (" + rect.width + "x" + rect.height + ")"
        : type.label + ": not set";

      var clear = document.createElement("button");
      clear.type = "button";
      clear.textContent = "x";
      clear.title = "Clear " + type.label;
      clear.style.cssText =
        "border:none;background:transparent;color:#94a3b8;cursor:pointer";
      clear.addEventListener("click", function () {
        delete state.rects[type.value];
        clearRect(type.value);
        renderList();
      });

      row.appendChild(swatch);
      row.appendChild(text);
      row.appendChild(clear);
      list.appendChild(row);
    });
  }

  function renderSets() {
    setSelect.innerHTML = "";
    if (!state.roiSets.length) {
      var empty = document.createElement("option");
      empty.value = "";
      empty.textContent = "No ROI sets — create one first";
      setSelect.appendChild(empty);
      setSelect.disabled = true;
      return;
    }
    setSelect.disabled = false;
    state.roiSets.forEach(function (roiSet) {
      var option = document.createElement("option");
      option.value = String(roiSet.id);
      option.textContent = roiSet.name;
      setSelect.appendChild(option);
    });
    if (state.selectedSetId) {
      setSelect.value = String(state.selectedSetId);
    } else if (state.existingSetId) {
      setSelect.value = String(state.existingSetId);
    }
    state.selectedSetId = setSelect.value;
  }

  function drawRect(name, rect, temporary) {
    var box = document.createElement("div");
    box.dataset.roiName = name;
    if (temporary) {
      box.dataset.temporary = "true";
    }
    box.style.cssText = [
      "position:fixed",
      "left:" + rect.x + "px",
      "top:" + rect.y + "px",
      "width:" + rect.width + "px",
      "height:" + rect.height + "px",
      "border:2px " + (temporary ? "dashed" : "solid") + " " + COLORS[name],
      "background:" + hexToRgba(COLORS[name], temporary ? 0.08 : 0.18),
      "pointer-events:none",
      "box-sizing:border-box",
    ].join(";");

    var tag = document.createElement("span");
    tag.textContent = name;
    tag.style.cssText = [
      "position:absolute",
      "top:-16px",
      "left:0",
      "padding:0 4px",
      "border-radius:3px",
      "font-size:10px",
      "color:#0f172a",
      "background:" + COLORS[name],
    ].join(";");
    box.appendChild(tag);
    layer.appendChild(box);
    return box;
  }

  function clearRect(name) {
    var nodes = layer.querySelectorAll('[data-roi-name="' + name + '"]');
    Array.prototype.forEach.call(nodes, function (node) {
      node.remove();
    });
  }

  function redrawAll() {
    layer.innerHTML = "";
    ROI_TYPES.forEach(function (type) {
      var rect = state.rects[type.value];
      if (rect) {
        drawRect(type.value, rect, false);
      }
    });
  }

  function hexToRgba(hex, alpha) {
    var value = hex.replace("#", "");
    var r = parseInt(value.substring(0, 2), 16);
    var g = parseInt(value.substring(2, 4), 16);
    var b = parseInt(value.substring(4, 6), 16);
    return "rgba(" + r + "," + g + "," + b + "," + alpha + ")";
  }

  function clamp(value, max) {
    return Math.max(0, Math.min(max, value));
  }

  function onMouseDown(event) {
    if (state.mode !== "draw" || event.button !== 0) {
      return;
    }
    event.preventDefault();
    drag = {
      startX: event.clientX,
      startY: event.clientY,
      box: null,
    };
    layer.style.userSelect = "none";
  }

  function onMouseMove(event) {
    if (!drag) {
      return;
    }
    var x = Math.min(drag.startX, event.clientX);
    var y = Math.min(drag.startY, event.clientY);
    var width = Math.abs(event.clientX - drag.startX);
    var height = Math.abs(event.clientY - drag.startY);
    var rect = { x: x, y: y, width: width, height: height };
    if (!drag.box) {
      drag.box = drawRect(state.activeType, rect, true);
    } else {
      drag.box.style.left = x + "px";
      drag.box.style.top = y + "px";
      drag.box.style.width = width + "px";
      drag.box.style.height = height + "px";
    }
  }

  function onMouseUp(event) {
    if (!drag) {
      return;
    }
    var startX = drag.startX;
    var startY = drag.startY;
    var box = drag.box;
    drag = null;
    layer.style.userSelect = "";

    if (box) {
      box.remove();
    }

    var endX = clamp(event.clientX, window.innerWidth);
    var endY = clamp(event.clientY, window.innerHeight);
    var left = clamp(Math.min(startX, endX), window.innerWidth);
    var top = clamp(Math.min(startY, endY), window.innerHeight);
    var width = Math.abs(endX - startX);
    var height = Math.abs(endY - startY);

    if (width < 4 || height < 4) {
      setStatus("Drag a larger area to record a region.");
      return;
    }

    state.rects[state.activeType] = {
      name: state.activeType,
      x: Math.round(left),
      y: Math.round(top),
      width: Math.round(width),
      height: Math.round(height),
    };
    redrawAll();
    renderList();
    setStatus("");
  }

  function loadRoiSets() {
    setStatus("Loading ROI sets…");
    api("listRoiSets")
      .then(function (result) {
        state.roiSets = result.roiSets || [];
        state.existingSetId = result.existingRoiSetId || null;
        state.selectedSetId = state.existingSetId || "";
        renderSets();
        setStatus(
          state.roiSets.length
            ? ""
            : "No ROI sets yet. Create one in the dashboard first."
        );
      })
      .catch(function (error) {
        setStatus("Could not load ROI sets: " + error.message);
      });
  }

  function saveRois() {
    if (state.busy) {
      return;
    }
    var rois = Object.keys(state.rects).map(function (name) {
      return state.rects[name];
    });
    if (!rois.length) {
      setStatus("Draw at least one region before saving.");
      return;
    }
    if (!setSelect.value) {
      setStatus("Select an ROI set to save into.");
      return;
    }
    state.busy = true;
    setStatus("Saving…");
    api("saveRois", {
      roiSetId: Number(setSelect.value),
      rois: rois,
    })
      .then(function (result) {
        if (result && result.ok) {
          setStatus("Saved " + rois.length + " region(s).");
        } else {
          setStatus("Save failed: " + (result && result.error) || "unknown");
        }
      })
      .catch(function (error) {
        setStatus("Save failed: " + error.message);
      })
      .then(function () {
        state.busy = false;
      });
  }

  function closeOverlay() {
    setStatus("Closing browser session…");
    api("close").catch(function () {
      // The binding disappears when the session tears the page down.
    });
  }

  function wire() {
    playBtn.addEventListener("click", function () {
      state.mode = "play";
      applyMode();
    });
    drawBtn.addEventListener("click", function () {
      state.mode = "draw";
      applyMode();
    });
    typeSelect.addEventListener("change", function () {
      state.activeType = typeSelect.value;
    });
    setSelect.addEventListener("change", function () {
      state.selectedSetId = setSelect.value;
    });
    saveBtn.addEventListener("click", saveRois);
    closeBtn.addEventListener("click", closeOverlay);
    layer.addEventListener("mousedown", onMouseDown, true);
    window.addEventListener("mousemove", onMouseMove, true);
    window.addEventListener("mouseup", onMouseUp, true);
  }

  function mount() {
    if (!document.body) {
      window.requestAnimationFrame(mount);
      return;
    }
    document.body.appendChild(root);
    applyMode();
    renderList();
    wire();
    loadRoiSets();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mount, { once: true });
  } else {
    mount();
  }
})();
