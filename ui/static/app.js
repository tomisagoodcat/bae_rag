(function () {
  const stageGrid = document.getElementById("stage-grid");
  const btnStart = document.getElementById("btn-start");
  const btnCancel = document.getElementById("btn-cancel");
  const progressFill = document.getElementById("progress-fill");
  const progressText = document.getElementById("progress-text");
  const logPanel = document.getElementById("log-panel");
  const refreshStats = document.getElementById("refresh-stats");
  const papersTotal = document.getElementById("papers-total");
  const papersProgress = document.getElementById("papers-progress");
  const papersResult = document.getElementById("papers-result");
  const papersDir = document.getElementById("papers-dir");
  const papersList = document.getElementById("papers-list");
  const papersSelected = document.getElementById("papers-selected");
  const btnSelectAll = document.getElementById("btn-select-all");
  const btnDeselectAll = document.getElementById("btn-deselect-all");
  const modalOverlay = document.getElementById("modal-overlay");
  const modalTitle = document.getElementById("modal-title");
  const modalBody = document.getElementById("modal-body");
  const modalClose = document.getElementById("modal-close");

  let stageDefaults = {};
  let ws = null;
  let building = false;

  function fmt(value) {
    return value == null || value === "" ? "—" : String(value);
  }

  function appendLog(message) {
    logPanel.textContent += message + "\n";
    logPanel.scrollTop = logPanel.scrollHeight;
  }

  function setProgress(index, total) {
    const pct = total > 0 ? Math.round((index / total) * 100) : 0;
    progressFill.style.width = pct + "%";
    progressText.textContent = index + " / " + total + " stages";
  }

  function setBuilding(active) {
    building = active;
    btnStart.disabled = active;
    btnCancel.disabled = !active;
    stageGrid.querySelectorAll("input").forEach((el) => {
      el.disabled = active;
    });
    papersList.querySelectorAll("input").forEach((el) => {
      el.disabled = active;
    });
    btnSelectAll.disabled = active;
    btnDeselectAll.disabled = active;
  }

  function showModal(kind, title, body) {
    modalOverlay.className = "modal " + kind;
    modalTitle.textContent = title;
    modalBody.textContent = body;
    modalOverlay.classList.remove("hidden");
  }

  function hideModal() {
    modalOverlay.classList.add("hidden");
    refreshNeo4jStats();
    loadDocuments();
  }

  modalClose.addEventListener("click", hideModal);
  modalOverlay.addEventListener("click", (e) => {
    if (e.target === modalOverlay) hideModal();
  });

  async function fetchJson(url, options) {
    const res = await fetch(url, options);
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || res.statusText);
    }
    return res.json();
  }

  async function loadStages() {
    const data = await fetchJson("/api/stages");
    stageDefaults = data.defaults || {};
    stageGrid.innerHTML = "";
    data.stages.forEach((stage) => {
      const label = document.createElement("label");
      label.className = "stage-tile" + (stage.destructive ? " destructive" : "");
      const input = document.createElement("input");
      input.type = "checkbox";
      input.value = stage.id;
      input.checked = !!stageDefaults[stage.id];
      const span = document.createElement("span");
      span.className = "stage-title";
      span.textContent = stage.title;
      label.appendChild(input);
      label.appendChild(span);
      stageGrid.appendChild(label);
    });
  }

  function updateSelectedCount() {
    const inputs = papersList.querySelectorAll("input[type=checkbox]");
    const total = inputs.length;
    let selected = 0;
    inputs.forEach((input) => {
      if (input.checked) selected += 1;
    });
    papersSelected.textContent = "Selected: " + selected + " / " + total;
    papersTotal.textContent = String(selected);
  }

  function getSelectedFiles() {
    const files = [];
    papersList.querySelectorAll("input[type=checkbox]").forEach((input) => {
      if (input.checked) files.push(input.value);
    });
    return files;
  }

  function setAllPapersChecked(checked) {
    papersList.querySelectorAll("input[type=checkbox]").forEach((input) => {
      input.checked = checked;
    });
    updateSelectedCount();
  }

  async function loadDocuments() {
    try {
      const data = await fetchJson("/api/documents");
      const files = data.files || [];
      papersDir.textContent =
        "Source: " + data.markdown_dir + " (total files: " + data.total_files + ")";
      papersList.innerHTML = "";
      if (files.length === 0) {
        const empty = document.createElement("div");
        empty.className = "papers-list-empty";
        empty.textContent = "No markdown papers found in this folder.";
        papersList.appendChild(empty);
      } else {
        files.forEach((filename) => {
          const label = document.createElement("label");
          label.className = "paper-row";
          const input = document.createElement("input");
          input.type = "checkbox";
          input.value = filename;
          input.checked = true;
          input.disabled = building;
          input.addEventListener("change", updateSelectedCount);
          const span = document.createElement("span");
          span.className = "paper-name";
          span.textContent = filename;
          span.title = filename;
          label.appendChild(input);
          label.appendChild(span);
          papersList.appendChild(label);
        });
      }
      updateSelectedCount();
      if (!building) {
        papersProgress.textContent = "—";
      }
    } catch (e) {
      papersTotal.textContent = "—";
      papersDir.textContent = "Could not load documents: " + e.message;
      papersList.innerHTML = "";
      papersSelected.textContent = "Selected: 0 / 0";
    }
  }

  async function refreshNeo4jStats() {
    try {
      const data = await fetchJson("/api/neo4j/stats");
      document.getElementById("neo4j-nodes").textContent = fmt(data.nodes);
      document.getElementById("neo4j-rels").textContent = fmt(data.relationships);
    } catch (e) {
      document.getElementById("neo4j-nodes").textContent = "—";
      document.getElementById("neo4j-rels").textContent = "—";
    }
  }

  function updateBuildResult(summary) {
    const s = summary.summary || summary;
    const buildKg = summary.build_kg || {};
    document.getElementById("res-duration").textContent =
      s.duration_sec != null ? s.duration_sec + "s" : "—";
    document.getElementById("res-stages").textContent =
      (s.stages_completed != null ? s.stages_completed : "—") +
      " / " +
      (s.stages_total != null ? s.stages_total : "—");
    document.getElementById("res-entities").textContent = fmt(s.entities ?? buildKg.schemas_processed);
    document.getElementById("res-relations").textContent = fmt(s.relations ?? buildKg.rel_count);
    document.getElementById("res-documents").textContent = fmt(s.documents ?? buildKg.document_count);
    document.getElementById("res-chunks").textContent = fmt(s.chunks);

    const succeeded = buildKg.succeeded_docs ?? s.succeeded_docs;
    const failedList = buildKg.failed_docs ?? s.failed_docs ?? [];
    const total = buildKg.document_count ?? s.documents;
    if (succeeded != null || total != null) {
      papersResult.textContent =
        "Succeeded: " + fmt(succeeded) + " / Failed: " + failedList.length + " / Total: " + fmt(total);
    }
  }

  function getSelectedStages() {
    const stages = {};
    stageGrid.querySelectorAll("input[type=checkbox]").forEach((input) => {
      stages[input.value] = input.checked;
    });
    return stages;
  }

  function connectWebSocket() {
    const protocol = location.protocol === "https:" ? "wss:" : "ws:";
    ws = new WebSocket(protocol + "//" + location.host + "/ws");
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      handleEvent(data);
    };
    ws.onclose = () => {
      setTimeout(connectWebSocket, 2000);
    };
  }

  async function handleEvent(event) {
    switch (event.type) {
      case "log":
        appendLog(event.message);
        break;
      case "stage_start":
        setProgress(event.index - 1, event.total);
        break;
      case "stage_done":
        setProgress(event.index, event.total);
        break;
      case "document_progress":
        papersProgress.textContent =
          "Processing: " + event.current + " / " + event.total + " — " + event.filename;
        break;
      case "document_done":
        papersProgress.textContent =
          "Processing: " + event.current + " / " + event.total + " — " + event.filename +
          (event.success ? " (ok)" : " (failed)");
        break;
      case "complete":
        setBuilding(false);
        setProgress(event.summary?.summary?.stages_total || 0, event.summary?.summary?.stages_total || 0);
        updateBuildResult(event.summary || {});
        papersProgress.textContent = "—";
        try {
          const logInfo = await fetchJson("/api/build/last-log");
          const logLine = logInfo.filename ? "\nLog saved: " + logInfo.path : "";
          showModal(
            "success",
            "Build Succeeded",
            buildSuccessMessage(event.summary) + logLine
          );
        } catch (_) {
          showModal("success", "Build Succeeded", buildSuccessMessage(event.summary));
        }
        break;
      case "error":
        setBuilding(false);
        papersProgress.textContent = "—";
        try {
          const logInfo = await fetchJson("/api/build/last-log");
          const logLine = logInfo.filename ? "\nLog saved: " + logInfo.path : "";
          showModal(
            "error",
            "Build Failed",
            (event.message || "Unknown error") +
              (event.stage ? "\nStage: " + event.stage : "") +
              logLine
          );
        } catch (_) {
          showModal(
            "error",
            "Build Failed",
            (event.message || "Unknown error") + (event.stage ? "\nStage: " + event.stage : "")
          );
        }
        break;
      case "cancelled":
        setBuilding(false);
        papersProgress.textContent = "—";
        showModal(
          "warning",
          "Build Cancelled",
          "The pipeline was cancelled. Cancellation only takes effect between stages, not during mid-document LLM extraction."
        );
        break;
      default:
        break;
    }
  }

  function buildSuccessMessage(summary) {
    const s = summary.summary || {};
    const buildKg = summary.build_kg || {};
    const lines = [];
    if (s.duration_sec != null) lines.push("Duration: " + s.duration_sec + "s");
    if (buildKg.succeeded_docs != null) {
      lines.push(
        "Papers: " + buildKg.succeeded_docs + " succeeded, " +
        (buildKg.failed_docs || []).length + " failed, " +
        (buildKg.document_count || "—") + " total"
      );
    }
    if (s.nodes != null) lines.push("Neo4j nodes: " + s.nodes);
    if (s.relationships != null) lines.push("Neo4j relationships: " + s.relationships);
    return lines.join("\n") || "Pipeline completed successfully.";
  }

  btnSelectAll.addEventListener("click", () => setAllPapersChecked(true));
  btnDeselectAll.addEventListener("click", () => setAllPapersChecked(false));

  btnStart.addEventListener("click", async () => {
    const stages = getSelectedStages();
    const selected_files = getSelectedFiles();
    if (stages.build_kg && selected_files.length === 0) {
      showModal(
        "warning",
        "No Papers Selected",
        "Select at least one paper when Build Knowledge Graph is enabled."
      );
      return;
    }
    if (stages.clear_neo4j) {
      const ok = confirm(
        "This will delete all data in the current Neo4j database.\n\nAre you sure you want to continue?"
      );
      if (!ok) return;
    }
    logPanel.textContent = "";
    papersResult.textContent = "—";
    setProgress(0, 0);
    setBuilding(true);
    try {
      await fetchJson("/api/build", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ stages, selected_files }),
      });
    } catch (e) {
      setBuilding(false);
      showModal("error", "Build Failed", e.message);
    }
  });

  btnCancel.addEventListener("click", async () => {
    btnCancel.disabled = true;
    try {
      await fetchJson("/api/build/cancel", { method: "POST" });
    } catch (e) {
      appendLog("Cancel request failed: " + e.message);
      btnCancel.disabled = false;
    }
  });

  refreshStats.addEventListener("click", () => {
    refreshNeo4jStats();
    loadDocuments();
  });

  loadStages();
  loadDocuments();
  refreshNeo4jStats();
  connectWebSocket();
})();
