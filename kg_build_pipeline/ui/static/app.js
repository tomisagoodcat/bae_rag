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
  const extractModeHint = document.getElementById("extract-mode-hint");
  const modalOverlay = document.getElementById("modal-overlay");
  const modalTitle = document.getElementById("modal-title");
  const modalBody = document.getElementById("modal-body");
  const modalClose = document.getElementById("modal-close");

  let stageDefaults = {};
  let stageManifest = [];
  let ws = null;
  let building = false;

  function fmt(value) {
    return value == null || value === "" ? "—" : String(value);
  }

  function appendLog(message, cssClass) {
    if (!cssClass) {
      logPanel.textContent += message + "\n";
    } else {
      const line = document.createElement("div");
      line.className = "log-line " + cssClass;
      line.textContent = message;
      logPanel.appendChild(line);
    }
    logPanel.scrollTop = logPanel.scrollHeight;
  }

  function appendStructuredEvent(event) {
    const formatted = formatStructuredEvent(event);
    if (!formatted) return;
    if (Array.isArray(formatted)) {
      formatted.forEach((item) => appendLog(item.text, item.className));
    } else {
      appendLog(formatted.text, formatted.className);
    }
  }

  function formatStructuredEvent(event) {
    const t = event.type;
    if (t === "schema_extract") {
      const status = String(event.status || "").toUpperCase();
      let cls = "log-info";
      if (status === "OK") cls = "log-ok";
      if (status === "SKIP") cls = "log-warn";
      if (status === "FAIL") cls = "log-hard";
      const reason = event.reason ? " (" + event.reason + ")" : "";
      const triple = event.triple
        ? event.triple[0] + " -[" + event.triple[1] + "]-> " + event.triple[2]
        : "";
      const phase = String(event.phase || "build").toLowerCase();
      const prefix = phase === "reextract"
        ? "[mid_gate] reextract schema | "
        : "[build_kg] ";
      return {
        text: prefix + (event.filename || "") + " | " + status + " | " + triple + reason,
        className: cls,
      };
    }
    if (t === "document_extract_summary") {
      return {
        text: "[build_kg] " + event.filename + " summary: ok=" + event.schemas_ok +
          " skip=" + event.schemas_skipped + " fail=" + event.schemas_failed,
        className: "log-info",
      };
    }
    if (t === "phase_a_coverage") {
      const hist = event.section_role_histogram || {};
      const histS = Object.keys(hist)
        .sort()
        .map((k) => k + "=" + hist[k])
        .join(", ");
      const lines = [
        {
          text: "[build_kg] " + event.filename + " Phase A coverage: ok=" +
            event.ok + " skip=" + event.skip + " fail=" + event.fail +
            " / " + event.expected_total + " expected",
          className: "log-info",
        },
        {
          text: "[build_kg] " + event.filename + " section roles: " + (histS || "—"),
          className: "log-info",
        },
      ];
      const missing = event.missing_triples || [];
      if (missing.length) {
        lines.push({
          text: "[build_kg] " + event.filename + " Phase A missing (" + missing.length + "):",
          className: "log-warn",
        });
        missing.forEach((item) => {
          const t3 = item.triple
            ? item.triple[0] + " -[" + item.triple[1] + "]-> " + item.triple[2]
            : "";
          const allowed = (item.allowed_sections || []).join(",");
          lines.push({
            text: "  - " + t3 + " | " + item.status + " | " + (item.reason || "") +
              " | allowed=[" + (allowed || "—") + "] | chunks=" +
              (item.matching_chunk_count || 0),
            className: "log-warn",
          });
        });
      }
      return lines;
    }
    if (t === "mid_gate_phase") {
      const labels = {
        validate: "SHACL/Cypher validation",
        review: "Qwen reviewer running",
        reextract: "Agent targeted re-extract",
        done: "Quality gate done",
      };
      const label = labels[event.phase] || event.phase;
      return {
        text: "[mid_gate] " + event.filename + " iter " + event.iteration + " | " + label,
        className: "log-phase",
      };
    }
    if (t === "mid_gate_validate") {
      const lines = [
        {
          text: "[mid_gate] " + event.filename + " iter " + event.iteration +
            " | validate: hard=" + event.hard_count + " warn=" + event.warning_count,
          className: "log-info",
        },
      ];
      (event.hard_violations || []).forEach((v) => {
        lines.push({
          text: "  " + (v.rule_id || "?") + " HARD [" + (v.entity_name || v.entity || "") + "]: " + (v.message || ""),
          className: "log-hard",
        });
      });
      (event.warnings || []).forEach((v) => {
        lines.push({
          text: "  " + (v.rule_id || "?") + " WARN [" + (v.entity_name || v.entity || "") + "]: " + (v.message || ""),
          className: "log-warn",
        });
      });
      return lines;
    }
    if (t === "mid_gate_review") {
      const scores = event.scores || {};
      const overall = scores.overall_score != null ? scores.overall_score : event.overall_score;
      return {
        text: "[mid_gate] " + event.filename + " iter " + event.iteration +
          " | reviewer: score=" + overall + " decision=" + event.decision +
          " (" + event.issue_count + " issues)",
        className: "log-info",
      };
    }
    if (t === "mid_gate_reextract") {
      const chunk = event.chunk_resolution || {};
      const chunkS = Object.keys(chunk).map((k) => k + "=" + chunk[k]).join(", ");
      let text = "[mid_gate] " + event.filename + " iter " + event.iteration +
        " | agent re-extract: " + event.reextract_schemas + " schema calls | chunk: " +
        (chunkS || "—");
      if (event.merged_issue_count != null) {
        text += " | merged_issues=" + event.merged_issue_count;
      }
      return { text: text, className: "log-phase" };
    }
    if (t === "mid_gate_reject") {
      const names = event.names || [];
      let preview = names.slice(0, 5).join(", ");
      if (names.length > 5) preview += ", +" + (names.length - 5) + " more";
      return {
        text: "[mid_gate] " + event.filename + " iter " + event.iteration +
          " | pre-reject (" + event.mode + "): " + event.count + " nodes" +
          (preview ? " [" + preview + "]" : ""),
        className: "log-warn",
      };
    }
    if (t === "mid_gate_early_stop") {
      return {
        text: "[mid_gate] " + event.filename + " iter " + event.iteration +
          " | early-stop: " + event.reason + " (hard=" + event.hard_count + ")",
        className: "log-warn",
      };
    }
    return null;
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
    document.querySelectorAll('input[name="extract_mode"]').forEach((el) => {
      el.disabled = active;
    });
    btnSelectAll.disabled = active;
    btnDeselectAll.disabled = active;
    if (!active) {
      syncExtractModeUI();
    }
  }

  function getExtractMode() {
    const el = document.querySelector('input[name="extract_mode"]:checked');
    return el ? el.value : "mid";
  }

  function syncExtractModeUI() {
    const mode = getExtractMode();
    stageManifest.forEach((stage) => {
      const input = stageGrid.querySelector('input[value="' + stage.id + '"]');
      if (!input) return;
      const label = input.closest("label");
      const incompatible = (stage.incompatible_extract_modes || []).includes(mode);
      let reasonEl = label && label.querySelector(".stage-incompatible-reason");

      if (stage.id === "mid_quality_gate" && (mode === "mid" || mode === "mid_then_low")) {
        input.checked = true;
        input.disabled = building || incompatible;
      } else if (stage.id === "low_expand" && (mode === "expand_mid" || mode === "mid_then_low")) {
        input.checked = true;
        input.disabled = building || incompatible;
      } else if (incompatible) {
        input.checked = false;
        input.disabled = true;
        if (label) {
          label.classList.add("stage-incompatible");
          if (!reasonEl) {
            reasonEl = document.createElement("span");
            reasonEl.className = "stage-incompatible-reason";
            label.appendChild(reasonEl);
          }
          reasonEl.textContent = stage.incompatible_reason || "Not available in this mode";
        }
      } else {
        if (label) label.classList.remove("stage-incompatible");
        if (reasonEl) reasonEl.remove();
        input.disabled = building;
      }
    });

    if (extractModeHint) {
      if (mode === "mid") {
        extractModeHint.textContent =
          "Mid mode: schema_tiers=[mid], Mid Quality Gate on. MetaPath and PageRank are disabled.";
      } else if (mode === "expand_mid") {
        extractModeHint.textContent =
          "Extract Low: requires Neo4j mid graph with mid_gate_status=PASS. Runs low_expand then optional post stages.";
      } else if (mode === "mid_then_low") {
        extractModeHint.textContent =
          "Mid+Low: mid extract + gate, then parent-scoped low_expand on PASS documents.";
      } else {
        extractModeHint.textContent =
          "Deprecated Low and All: full potential_schema. Mid gate and hierarchical low_expand are skipped.";
      }
    }
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
    stageManifest = data.stages || [];
    stageGrid.innerHTML = "";
    stageManifest.forEach((stage) => {
      const label = document.createElement("label");
      label.className = "stage-tile" + (stage.destructive ? " destructive" : "");
      label.dataset.stageId = stage.id;
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
    syncExtractModeUI();
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
      case "schema_extract":
      case "document_extract_summary":
      case "phase_a_coverage":
      case "mid_gate_phase":
      case "mid_gate_validate":
      case "mid_gate_review":
      case "mid_gate_reextract":
      case "mid_gate_reject":
      case "mid_gate_early_stop":
        appendStructuredEvent(event);
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
          const midLog = await fetchJson("/api/build/mid-extract-log");
          const logLine = logInfo.filename ? "\nLog saved: " + logInfo.path : "";
          const midLine = midLog.filename ? "\nMid extract log: " + midLog.path : "";
          showModal(
            "success",
            "Build Succeeded",
            buildSuccessMessage(event.summary) + logLine + midLine
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

  document.querySelectorAll('input[name="extract_mode"]').forEach((el) => {
    el.addEventListener("change", syncExtractModeUI);
  });

  btnStart.addEventListener("click", async () => {
    syncExtractModeUI();
    const stages = getSelectedStages();
    const selected_files = getSelectedFiles();
    const extract_mode = getExtractMode();
    if (extract_mode === "mid") {
      stages.mid_quality_gate = true;
      stages.low_expand = false;
      stages.metapath = false;
      stages.pagerank = false;
    } else if (extract_mode === "mid_then_low") {
      stages.mid_quality_gate = true;
      stages.low_expand = true;
    } else if (extract_mode === "expand_mid") {
      stages.clear_neo4j = false;
      stages.build_kg = false;
      stages.mid_quality_gate = false;
      stages.low_expand = true;
    } else {
      stages.mid_quality_gate = false;
      stages.low_expand = false;
    }
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
    logPanel.innerHTML = "";
    papersResult.textContent = "—";
    setProgress(0, 0);
    setBuilding(true);
    appendLog("Extract mode: " + extract_mode);
    try {
      await fetchJson("/api/build", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ stages, selected_files, extract_mode }),
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
