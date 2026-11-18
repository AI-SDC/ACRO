(() => {
  "use strict";

  const stage = document.getElementById("wizard-stage");
  const progress = document.getElementById("wizard-progress");
  const progressText = document.getElementById("wizard-progress-text");
  const data = JSON.parse(document.getElementById("ontology-data").textContent);

  const statbarnNames = Object.keys(data.statbarns).sort((a, b) => a.localeCompare(b));
  // Steps: 0 = introduction, 1..N = statbarns, N+1 = summary.
  const summaryStep = statbarnNames.length + 1;
  const answers = {};
  statbarnNames.forEach((name) => { answers[name] = { applies: "", checks: {} }; });
  let step = 0;

  const escapeHtml = (value) =>
    String(value ?? "").replace(/[&<>"']/g, (c) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    })[c]);

  const termDetails = (name, entry) => `
    <details>
      <summary>${escapeHtml(name)}</summary>
      <p>${escapeHtml(entry.definition || "No definition is available.")}</p>
      ${entry.uri ? `<a href="${escapeHtml(entry.uri)}" target="_blank" rel="noopener noreferrer">Ontology source</a>` : ""}
    </details>`;

  const risksFor = (statbarnName) =>
    (data.statbarns[statbarnName].risks || [])
      .filter((risk) => data.risks[risk])
      .map((risk) => ({
        name: risk,
        entry: data.risks[risk],
        checks: (data.risks[risk].checks || [])
          .filter((check) => data.checks[check])
          .map((check) => ({ name: check, entry: data.checks[check] })),
      }));

  const analysesFor = (statbarnName) =>
    Object.keys(data.analyses)
      .filter((name) => data.analyses[name].statbarn === statbarnName)
      .sort((a, b) => a.localeCompare(b));

  const checkKey = (risk, check) => `${risk}::${check}`;

  const statusLabels = {
    covered: "Yes – performed",
    gap: "No – not performed",
    not_applicable: "Not applicable",
    "": "Not answered",
  };

  const renderCheck = (statbarnName, riskName, check) => {
    const key = checkKey(riskName, check.name);
    const saved = answers[statbarnName].checks[key] || { status: "", note: "" };
    const id = `${statbarnName}-${key}`.replace(/[^A-Za-z0-9_-]/g, "_");
    const evidence = check.entry.evidence?.length
      ? `<p><strong>Evidence:</strong> ${escapeHtml(check.entry.evidence.join(", "))}</p>` : "";
    const option = (value, text) =>
      `<option value="${value}" ${saved.status === value ? "selected" : ""}>${text}</option>`;
    return `
      <div class="assessment-check">
        <p class="check-label">Check</p>
        ${termDetails(check.name, check.entry)}
        ${evidence}
        <label for="status-${id}">Does your process perform this check for the risk of ${escapeHtml(riskName)}?</label>
        <select id="status-${id}" data-check-key="${escapeHtml(key)}">
          ${option("", "Choose a response")}
          ${option("covered", "Yes – this check is performed")}
          ${option("gap", "No – not currently performed")}
          ${option("not_applicable", "Not applicable (explain below)")}
        </select>
        <label for="note-${id}">Notes</label>
        <textarea id="note-${id}" data-note-key="${escapeHtml(key)}" placeholder="Describe the procedure, evidence, or why it is not applicable">${escapeHtml(saved.note)}</textarea>
      </div>`;
  };

  const renderIntro = () => `
    <h2>Before you start</h2>
    <p>This guided self-assessment walks you through each of the ${statbarnNames.length} output categories
    (<em>statbarns</em>) in the StatBarn SDC ontology, one at a time. For each one you will:</p>
    <ol>
      <li>say whether your manual process produces outputs of that type;</li>
      <li>if it does, see the <strong>risks</strong> the ontology associates with it, and the <strong>checks</strong> that assess whether each risk is present;</li>
      <li>record whether your process performs each check.</li>
    </ol>
    <p>You can go back at any time, and a summary at the end shows gaps and unanswered categories.</p>
    <div class="notice"><p>This is a guide for human assessment, not a certification or safety decision.
    Ontology links describe potential relationships and may not cover every local risk or procedure.
    Everything you enter stays in this browser; use the download button on the summary to save a copy.</p></div>
    <div class="nav"><button type="button" data-next class="primary">Start assessment</button></div>`;

  const renderStatbarn = () => {
    const name = statbarnNames[step - 1];
    const entry = data.statbarns[name];
    const state = answers[name];
    const examples = analysesFor(name);
    const shown = examples.slice(0, 8);
    const radio = (value, text) => `
      <label class="choice"><input type="radio" name="applies" value="${value}" ${state.applies === value ? "checked" : ""}> ${text}</label>`;
    let detail = "";
    if (state.applies === "yes") {
      const risks = risksFor(name);
      detail = risks.length ? `
        <p>The ontology associates this category with the following potential risks. Under each risk are the checks that assess whether that risk is present.</p>
        ${risks.map((risk) => `
          <section class="assessment-risk">
            <h5>Potential risk</h5>
            ${termDetails(risk.name, risk.entry)}
            <div class="risk-checks" role="group" aria-label="Checks that assess the risk of ${escapeHtml(risk.name)}">
              <h6>Checks that assess whether the risk of ${escapeHtml(risk.name)} is present</h6>
              ${risk.checks.length ? risk.checks.map((check) => renderCheck(name, risk.name, check)).join("")
                : "<p>No checks are listed for this risk in the packaged ontology.</p>"}
            </div>
          </section>`).join("")}`
        : `<p>No risks are listed for this category in the packaged ontology. This does not establish that its outputs are safe; review the process manually.</p>`;
    }
    return `
      <p class="step-kicker">Category ${step} of ${statbarnNames.length}</p>
      <h2>${escapeHtml(name)}</h2>
      <p>${escapeHtml(entry.definition || "No definition is available.")}</p>
      ${entry.uri ? `<p><a href="${escapeHtml(entry.uri)}" target="_blank" rel="noopener noreferrer">Ontology source</a></p>` : ""}
      ${examples.length ? `<p class="examples"><strong>Example analyses:</strong> ${shown.map(escapeHtml).join(", ")}${examples.length > shown.length ? ` and ${examples.length - shown.length} more` : ""}</p>` : ""}
      <fieldset>
        <legend>Does your manual process handle output requests of this type?</legend>
        ${radio("yes", "Yes")}
        ${radio("no", "No")}
        ${radio("unsure", "Not sure – flag for review")}
      </fieldset>
      ${detail}
      ${navButtons()}`;
  };

  const navButtons = () => `
    <div class="nav">
      <button type="button" data-back>Back</button>
      <button type="button" data-next class="primary">${step === statbarnNames.length ? "Review summary" : "Next"}</button>
      <button type="button" data-summary>Skip to summary</button>
    </div>`;

  const checkRows = (name) => risksFor(name).flatMap((risk) =>
    risk.checks.map((check) => ({
      risk,
      check,
      ...(answers[name].checks[checkKey(risk.name, check.name)] || { status: "", note: "" }),
    })));

  const renderSummary = () => {
    const yes = statbarnNames.filter((n) => answers[n].applies === "yes");
    const unsure = statbarnNames.filter((n) => answers[n].applies === "unsure");
    const unanswered = statbarnNames.filter((n) => !answers[n].applies);
    const no = statbarnNames.filter((n) => answers[n].applies === "no");
    let gaps = 0;
    let unansweredChecks = 0;
    const sections = yes.map((name) => {
      const rows = checkRows(name);
      gaps += rows.filter((r) => r.status === "gap").length;
      unansweredChecks += rows.filter((r) => !r.status).length;
      return `
        <section class="summary-block">
          <h3>${escapeHtml(name)} <button type="button" class="link" data-goto="${statbarnNames.indexOf(name) + 1}">edit</button></h3>
          ${rows.length ? `<table>
            <thead><tr><th>Risk</th><th>Check</th><th>Response</th><th>Notes</th></tr></thead>
            <tbody>${rows.map((r) => `
              <tr class="${r.status === "gap" ? "is-gap" : ""}">
                <td>${escapeHtml(r.risk.name)}</td><td>${escapeHtml(r.check.name)}</td>
                <td>${escapeHtml(statusLabels[r.status])}</td><td>${escapeHtml(r.note)}</td>
              </tr>`).join("")}</tbody></table>`
            : "<p>No checks listed in the ontology for this category; review manually.</p>"}
        </section>`;
    }).join("");
    const jumpList = (names) => names.map((n) =>
      `<button type="button" class="link" data-goto="${statbarnNames.indexOf(n) + 1}">${escapeHtml(n)}</button>`).join(", ");
    return `
      <h2>Summary</h2>
      <ul>
        <li><strong>${yes.length}</strong> categories apply to your process; <strong>${gaps}</strong> checks recorded as not performed, <strong>${unansweredChecks}</strong> checks not yet answered.</li>
        <li><strong>${no.length}</strong> categories do not apply.</li>
        <li><strong>${unsure.length}</strong> flagged as not sure${unsure.length ? `: ${jumpList(unsure)}` : ""}.</li>
        <li><strong>${unanswered.length}</strong> not yet answered${unanswered.length ? `: ${jumpList(unanswered)}` : ""}.</li>
      </ul>
      <div class="notice"><p>Responses indicate where your process may differ from the ontology; they are not a compliance decision. Human review is still required.</p></div>
      ${sections || "<p>No categories have been marked as applying to your process yet.</p>"}
      <div class="nav">
        <button type="button" data-back>Back</button>
        <button type="button" data-download class="primary">Download assessment JSON</button>
      </div>`;
  };

  const download = () => {
    const assessment = {
      title: "StatBarn SDC ontology alignment self-assessment (guided)",
      disclaimer: "Self-assessment only; not a certification or automated safety decision.",
      source: "Ontology JSON files packaged with ACRO",
      statbarns: statbarnNames.map((name) => ({
        statbarn: name,
        definition: data.statbarns[name].definition,
        produced_by_process: answers[name].applies || null,
        checks: answers[name].applies === "yes" ? checkRows(name).map((r) => ({
          risk: r.risk.name,
          risk_definition: r.risk.entry.definition,
          check: r.check.name,
          check_definition: r.check.entry.definition,
          evidence: r.check.entry.evidence || [],
          status: r.status,
          note: r.note,
        })) : [],
      })),
    };
    const blob = new Blob([JSON.stringify(assessment, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "ontology-alignment-guided-assessment.json";
    link.click();
    URL.revokeObjectURL(url);
  };

  const render = (focusSelector) => {
    stage.innerHTML = step === 0 ? renderIntro() : step === summaryStep ? renderSummary() : renderStatbarn();
    const done = Math.min(step, statbarnNames.length);
    progress.max = statbarnNames.length;
    progress.value = done;
    progressText.textContent = step === 0 ? "Introduction"
      : step === summaryStep ? "Summary" : `Category ${step} of ${statbarnNames.length}`;
    const target = focusSelector ? stage.querySelector(focusSelector) : stage.querySelector("h2");
    if (target) {
      if (!target.matches("input,select,textarea,button")) target.tabIndex = -1;
      target.focus();
    }
  };

  const go = (next) => {
    step = Math.max(0, Math.min(summaryStep, next));
    render();
    window.scrollTo(0, 0);
  };

  stage.addEventListener("click", (event) => {
    const t = event.target.closest("button");
    if (!t) return;
    if (t.matches("[data-next]")) go(step + 1);
    else if (t.matches("[data-back]")) go(step - 1);
    else if (t.matches("[data-summary]")) go(summaryStep);
    else if (t.matches("[data-goto]")) go(Number(t.dataset.goto));
    else if (t.matches("[data-download]")) download();
  });

  stage.addEventListener("change", (event) => {
    const t = event.target;
    const name = statbarnNames[step - 1];
    if (!name) return;
    if (t.matches("input[name=applies]")) {
      answers[name].applies = t.value;
      render("input[name=applies]:checked");
    } else if (t.matches("[data-check-key]")) {
      const saved = answers[name].checks[t.dataset.checkKey] || { status: "", note: "" };
      saved.status = t.value;
      answers[name].checks[t.dataset.checkKey] = saved;
    }
  });

  stage.addEventListener("input", (event) => {
    const t = event.target;
    const name = statbarnNames[step - 1];
    if (name && t.matches("[data-note-key]")) {
      const saved = answers[name].checks[t.dataset.noteKey] || { status: "", note: "" };
      saved.note = t.value;
      answers[name].checks[t.dataset.noteKey] = saved;
    }
  });

  render();
})();
