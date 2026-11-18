(() => {
  "use strict";

  const root = document.getElementById("ontology-assessment");
  if (!root) return;

  const loading = document.getElementById("ontology-loading");
  const error = document.getElementById("ontology-error");
  const content = document.getElementById("assessment-content");
  const processList = document.getElementById("process-list");
  const addButton = document.getElementById("add-process");
  const downloadButton = document.getElementById("download-assessment");
  const summary = document.getElementById("assessment-summary");
  const data = {};
  const processes = [];
  let nextId = 1;

  const escapeHtml = (value) =>
    String(value ?? "").replace(/[&<>"']/g, (character) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    })[character]);

  const termDetails = (name, entry) => `
    <details>
      <summary>${escapeHtml(name)}</summary>
      <p>${escapeHtml(entry.definition || "No definition is available.")}</p>
      ${entry.uri ? `<a href="${escapeHtml(entry.uri)}" target="_blank" rel="noopener noreferrer">Ontology source</a>` : ""}
    </details>
  `;

  const getRelatedChecks = (statbarn) => {
    const risks = (statbarn.risks || []).map((name) => ({
      name,
      entry: data.risks[name],
    })).filter(({ entry }) => entry);
    return risks.map(({ name, entry }) => ({
      name,
      entry,
      checks: (entry.checks || []).map((checkName) => ({
        name: checkName,
        entry: data.checks[checkName],
      })).filter(({ entry: check }) => check),
    }));
  };

  const checkId = (riskName, checkName) => `${riskName}::${checkName}`;

  const renderCheck = (process, riskName, checkName, check) => {
    const id = checkId(riskName, checkName);
    const saved = process.checks[id] || { status: "", note: "" };
    const evidence = check.evidence?.length
      ? `<p><strong>Evidence:</strong> ${escapeHtml(check.evidence.join(", "))}</p>`
      : "";
    return `
      <div class="assessment-check">
        <p class="check-label">Check</p>
        ${termDetails(checkName, check)}
        ${evidence}
        <label for="status-${process.id}-${escapeHtml(id)}">Does your process perform this check for the risk of ${escapeHtml(riskName)}?</label>
        <select id="status-${process.id}-${escapeHtml(id)}" data-check-id="${escapeHtml(id)}">
          <option value="" ${saved.status === "" ? "selected" : ""}>Choose a response</option>
          <option value="covered" ${saved.status === "covered" ? "selected" : ""}>Yes – this check is performed</option>
          <option value="gap" ${saved.status === "gap" ? "selected" : ""}>No – not currently performed</option>
          <option value="not_applicable" ${saved.status === "not_applicable" ? "selected" : ""}>Not applicable (explain below)</option>
        </select>
        <label for="note-${process.id}-${escapeHtml(id)}">Notes</label>
        <textarea id="note-${process.id}-${escapeHtml(id)}" data-note-id="${escapeHtml(id)}" placeholder="Describe the procedure, evidence, or reason it is not applicable">${escapeHtml(saved.note)}</textarea>
      </div>
    `;
  };

  const renderProcess = (process) => {
    const query = process.query.trim().toLowerCase();
    const analysisNames = Object.keys(data.analyses)
      .filter((name) => !query || `${name} ${data.analyses[name].definition || ""}`.toLowerCase().includes(query))
      .sort((a, b) => a.localeCompare(b));

    const selectedAnalysis = data.analyses[process.analysis];
    const statbarn = selectedAnalysis && data.statbarns[selectedAnalysis.statbarn];
    let mappedTerms = "";
    if (selectedAnalysis && statbarn) {
      const risks = getRelatedChecks(statbarn);
      mappedTerms = `
        <section class="mapped-ontology" aria-label="Ontology mapping">
          <h4>Mapped StatBarn category</h4>
          ${termDetails(selectedAnalysis.statbarn, statbarn)}
          ${risks.length ? risks.map(({ name, entry, checks }) => `
            <section class="assessment-risk">
              <h5>Potential risk</h5>
              ${termDetails(name, entry)}
              <div class="risk-checks" role="group" aria-label="Checks that assess the risk of ${escapeHtml(name)}">
                <h6>Checks that assess whether the risk of ${escapeHtml(name)} is present</h6>
                ${checks.length ? checks.map(({ name: checkName, entry: check }) => renderCheck(process, name, checkName, check)).join("") : "<p>No checks are listed for this risk in the packaged ontology.</p>"}
              </div>
            </section>
          `).join("") : "<p>No risks are listed for this StatBarn category. Review the process manually; an empty relationship does not establish safety.</p>"}
        </section>
      `;
    } else if (process.analysis) {
      mappedTerms = "<p role=\"alert\">The selected analysis does not map to a known StatBarn category in the packaged JSON files.</p>";
    }

    const status = assessmentStatus(process, statbarn);
    return `
      <article class="assessment-process" data-process-id="${process.id}">
        <div class="process-heading">
          <h3>Manual activity ${process.id}</h3>
          <button type="button" data-remove-process="${process.id}" aria-label="Remove manual activity ${process.id}">Remove activity</button>
          <p class="status">${escapeHtml(status)}</p>
        </div>
        <label for="activity-${process.id}">Describe the manual process or activity</label>
        <textarea id="activity-${process.id}" data-activity placeholder="For example: reviewing frequency tables before release">${escapeHtml(process.activity)}</textarea>
        <label for="analysis-search-${process.id}">Find an analysis term by name or definition</label>
        <input id="analysis-search-${process.id}" data-analysis-search type="search" value="${escapeHtml(process.query)}" placeholder="Search ontology analysis terms">
        <label for="analysis-${process.id}">Select the closest analysis term</label>
        <select id="analysis-${process.id}" data-analysis>
          <option value="">Choose an analysis term</option>
          ${analysisNames.map((name) => `<option value="${escapeHtml(name)}" ${process.analysis === name ? "selected" : ""}>${escapeHtml(name)}</option>`).join("")}
        </select>
        ${selectedAnalysis ? termDetails(process.analysis, selectedAnalysis) : ""}
        ${mappedTerms}
      </article>
    `;
  };

  const assessmentStatus = (process, statbarn) => {
    if (!process.analysis || !statbarn) return "Choose an analysis term to start mapping.";
    if (!process.activity.trim()) return "Add an activity description.";
    const checks = getRelatedChecks(statbarn).flatMap(({ name, checks: related }) =>
      related.map(({ name: checkName }) => process.checks[checkId(name, checkName)]?.status || ""),
    );
    if (!checks.length) return "Mapped; no linked checks are listed. Review this mapping manually.";
    if (checks.includes("gap")) return "Potential gap recorded — review this process.";
    if (checks.some((status) => !status)) return "Assessment incomplete — record a response for each linked check.";
    return "Responses recorded — human review still required.";
  };

  const updateSummary = () => {
    const counts = { incomplete: 0, gaps: 0, reviewed: 0 };
    for (const process of processes) {
      const statbarn = data.statbarns[data.analyses[process.analysis]?.statbarn];
      const status = assessmentStatus(process, statbarn);
      if (status.startsWith("Potential gap")) counts.gaps += 1;
      else if (status.startsWith("Responses recorded")) counts.reviewed += 1;
      else counts.incomplete += 1;
    }
    summary.textContent = `${processes.length} activities: ${counts.reviewed} with responses recorded, ${counts.gaps} with potential gaps, ${counts.incomplete} incomplete or requiring manual review.`;
    downloadButton.disabled = processes.length === 0;
  };

  const render = () => {
    processList.innerHTML = processes.map(renderProcess).join("");
    updateSummary();
  };

  const updateAnalysisOptions = (process, select) => {
    const query = process.query.trim().toLowerCase();
    const names = Object.keys(data.analyses)
      .filter((name) => !query || `${name} ${data.analyses[name].definition || ""}`.toLowerCase().includes(query));
    if (process.analysis && !names.includes(process.analysis)) names.unshift(process.analysis);
    names.sort((a, b) => a.localeCompare(b));
    select.innerHTML = `
      <option value="">Choose an analysis term</option>
      ${names.map((name) => `<option value="${escapeHtml(name)}">${escapeHtml(name)}</option>`).join("")}
    `;
    select.value = process.analysis;
  };

  const updateProcessStatus = (process, article) => {
    const statbarn = data.statbarns[data.analyses[process.analysis]?.statbarn];
    article.querySelector(".status").textContent = assessmentStatus(process, statbarn);
  };

  const saveInputState = (event) => {
    const article = event.target.closest("[data-process-id]");
    if (!article) return;
    const process = processes.find((item) => item.id === Number(article.dataset.processId));
    if (!process) return;

    if (event.target.matches("[data-activity]")) {
      process.activity = event.target.value;
      updateProcessStatus(process, article);
      updateSummary();
    } else if (event.target.matches("[data-analysis-search]")) {
      process.query = event.target.value;
      updateAnalysisOptions(process, article.querySelector("[data-analysis]"));
    } else if (event.target.matches("[data-analysis]")) {
      process.analysis = event.target.value;
      process.checks = {};
      render();
    } else if (event.target.matches("[data-check-id]")) {
      const saved = process.checks[event.target.dataset.checkId] || { status: "", note: "" };
      saved.status = event.target.value;
      process.checks[event.target.dataset.checkId] = saved;
      updateProcessStatus(process, article);
      updateSummary();
    } else if (event.target.matches("[data-note-id]")) {
      const saved = process.checks[event.target.dataset.noteId] || { status: "", note: "" };
      saved.note = event.target.value;
      process.checks[event.target.dataset.noteId] = saved;
    }
  };

  const download = () => {
    const assessment = {
      title: "StatBarn SDC ontology alignment self-assessment",
      disclaimer: "Self-assessment only; not a certification or automated safety decision.",
      source: "Ontology JSON files packaged with ACRO",
      activities: processes.map((process) => {
        const analysis = data.analyses[process.analysis];
        const statbarn = analysis && data.statbarns[analysis.statbarn];
        return {
          activity: process.activity,
          analysis: process.analysis || null,
          analysis_definition: analysis?.definition || null,
          statbarn: analysis?.statbarn || null,
          statbarn_definition: statbarn?.definition || null,
          checks: getRelatedChecks(statbarn || {}).flatMap(({ name: riskName, entry: risk, checks }) =>
            checks.map(({ name, entry }) => ({
              risk: riskName,
              risk_definition: risk.definition,
              check: name,
              check_definition: entry.definition,
              evidence: entry.evidence || [],
              ...(process.checks[checkId(riskName, name)] || { status: "", note: "" }),
            })),
          ),
        };
      }),
    };
    const blob = new Blob([JSON.stringify(assessment, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "ontology-alignment-assessment.json";
    link.click();
    URL.revokeObjectURL(url);
  };

  processList.addEventListener("input", saveInputState);
  processList.addEventListener("change", saveInputState);
  processList.addEventListener("click", (event) => {
    const button = event.target.closest("[data-remove-process]");
    if (!button) return;
    const index = processes.findIndex((process) => process.id === Number(button.dataset.removeProcess));
    if (index >= 0) processes.splice(index, 1);
    render();
  });
  addButton.addEventListener("click", () => {
    processes.push({ id: nextId++, activity: "", query: "", analysis: "", checks: {} });
    render();
    processList.lastElementChild?.querySelector("[data-activity]")?.focus();
  });
  downloadButton.addEventListener("click", download);

  try {
    Object.assign(data, JSON.parse(document.getElementById("ontology-data").textContent));
    loading.hidden = true;
    content.hidden = false;
    processes.push({ id: nextId++, activity: "", query: "", analysis: "", checks: {} });
    render();
  } catch (loadError) {
    loading.hidden = true;
    error.hidden = false;
    error.textContent = `The embedded ontology data could not be read. ${loadError.message}`;
  }
})();
