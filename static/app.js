const form = document.querySelector("#question-form");
const questionInput = document.querySelector("#question");
const teamSelect = document.querySelector("#team-select");
const sideSelect = document.querySelector("#side-select");
const askButton = document.querySelector("#ask-button");
const loading = document.querySelector("#loading");
const errorBox = document.querySelector("#error");
const results = document.querySelector("#results");

const escapeHtml = (value) => String(value ?? "")
  .replaceAll("&", "&amp;")
  .replaceAll("<", "&lt;")
  .replaceAll(">", "&gt;")
  .replaceAll('"', "&quot;")
  .replaceAll("'", "&#039;");

const setBusy = (busy) => {
  askButton.disabled = busy;
  loading.classList.toggle("hidden", !busy);
  if (busy) {
    results.classList.add("hidden");
    errorBox.classList.add("hidden");
  }
};

document.querySelectorAll(".example-button").forEach((button) => {
  button.addEventListener("click", () => {
    questionInput.value = button.dataset.question;
    teamSelect.value = button.dataset.team;
    sideSelect.value = button.dataset.side || "auto";
    questionInput.focus();
  });
});

const renderStats = (stats) => {
  const items = [
    ["MATCHING PLAYS", stats.sample_size],
    ["PASS RATE", `${Math.round(stats.pass_rate * 100)}%`],
    ["SUCCESS RATE", `${Math.round(stats.success_rate * 100)}%`],
    ["AVG EPA", Number(stats.average_epa).toFixed(3)],
    ["PRESSURE RATE", `${Math.round(stats.pressure_rate * 100)}%`],
  ];
  document.querySelector("#stats").innerHTML = items.map(([label, value]) => `<div class="stat-row"><span>${label}</span><strong>${escapeHtml(value)}</strong></div>`).join("");
};

const renderReport = (payload) => {
  const report = payload.report;
  document.querySelector("#result-question").textContent = payload.question;
  document.querySelector("#summary").textContent = report.executive_summary;
  document.querySelector("#confidence").textContent = String(report.confidence).toUpperCase();
  const badge = document.querySelector("#mode-badge");
  badge.textContent = payload.mode === "claude" ? `● CLAUDE / ${payload.model}` : "● LOCAL SCOUTING";
  badge.classList.toggle("live", payload.mode === "claude");
  renderStats(payload.meta.stats);

  document.querySelector("#tendencies").innerHTML = (report.tendencies || []).map((item) => `
    <article class="tendency-card">
      <div class="tendency-top"><span class="tendency-icon">↳</span><span class="confidence-tag ${escapeHtml(item.confidence)}">${escapeHtml(item.confidence)}</span></div>
      <h4>${escapeHtml(item.title)}</h4><p>${escapeHtml(item.detail)}</p>
    </article>`).join("");

  document.querySelector("#matchup-ideas").innerHTML = (report.matchup_ideas || []).map((idea, index) => `
    <div class="idea-row"><span>0${index + 1}</span><p>${escapeHtml(idea)}</p></div>`).join("");

  document.querySelector("#filter-summary").textContent = payload.meta.filter_labels.join(" · ") + (payload.meta.fallback_used ? " · RELAXED FALLBACK" : "");
  document.querySelector("#evidence-body").innerHTML = (payload.evidence || []).map((item) => `
    <tr><td class="citation">${escapeHtml(item.citation)}</td><td>${escapeHtml(`${item.down} & ${item.distance}`)}</td><td><span class="play-tag ${escapeHtml(item.play_type)}">${escapeHtml(item.play_type)}</span>${item.blitz ? '<span class="blitz-tag">BLITZ</span>' : ''}${item.pressure ? '<span class="pressure-tag">PRESSURE</span>' : ''}</td><td>${escapeHtml(`${item.yards_gained} yds`)}</td><td class="epa ${Number(item.epa) >= 0 ? "positive" : "negative"}">${Number(item.epa) >= 0 ? "+" : ""}${Number(item.epa).toFixed(2)}</td></tr>
    <tr class="desc-row"><td colspan="5">${escapeHtml(item.description)}</td></tr>`).join("");

  document.querySelector("#limitations").innerHTML = (report.limitations || []).map((item) => `<li>${escapeHtml(item)}</li>`).join("");
  results.classList.remove("hidden");
  results.scrollIntoView({ behavior: "smooth", block: "start" });
};

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const question = questionInput.value.trim();
  if (!question) return;
  setBusy(true);
  try {
    const response = await fetch("/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, team: teamSelect.value, side: sideSelect.value }),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "The scouting request failed.");
    renderReport(payload);
  } catch (error) {
    errorBox.textContent = error.message;
    errorBox.classList.remove("hidden");
  } finally {
    setBusy(false);
  }
});
