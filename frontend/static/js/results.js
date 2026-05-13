/**
 * VivaWala — Results Page
 */

document.addEventListener("DOMContentLoaded", loadResults);

async function loadResults() {
  try {
    const resp = await fetch(`/api/session/${SESSION_ID}`);
    if (!resp.ok) throw new Error("Session not found");
    const data = await resp.json();

    $("results-loading").style.display = "none";
    $("results-main").style.display    = "flex";

    renderNav(data);
    renderHero(data);
    renderGraph(data);
    renderTimeline(data);
    renderSummary(data);
    renderAccordion(data);
    setupDownloads();
  } catch (err) {
    $("results-loading").innerHTML = `
      <div class="spinner" style="width:36px;height:36px;border-top-color:var(--red);"></div>
      <div class="results-loading__label" style="color:var(--red);">${err.message}</div>
    `;
  }
}

function renderNav(d) {
  $("r-domain").textContent = d.domain || "—";
  $("r-date").textContent   = d.started_at ? new Date(d.started_at).toLocaleDateString() : "—";
  if (d.provider) {
    const el = $("r-provider");
    el.style.display = "inline-flex";
    el.textContent   = d.provider === "groq" ? "⚡ Groq" : "🦙 Ollama";
  }
}

function renderHero(d) {
  const a     = d.analytics || {};
  const score = a.average_score || 0;
  $("r-grade").textContent       = a.grade       || "—";
  $("r-grade").style.color       = score >= 7 ? "var(--green)" : score >= 5 ? "var(--amber)" : "var(--red)";
  $("r-score").textContent       = score.toFixed(1);
  $("r-questions").textContent   = a.total_questions  ?? "—";
  $("r-highest").textContent     = a.max_score        ?? "—";
  $("r-trend").textContent       = cap(a.trend        || "—");
  $("r-consistency").textContent = cap(a.consistency  || "—");
}

function renderGraph(d) {
  const img = $("dashboard-img"), fb = $("graph-fallback");
  if (d.graphs_available) {
    img.src = `/api/graph/${SESSION_ID}/dashboard`;
    img.style.display = "block";
    img.onerror = () => { img.style.display = "none"; fb.style.display = "block"; };
  } else {
    fb.style.display = "block";
  }
}

function renderTimeline(d) {
  const qa = d.qa_history || [];
  const el = $("scores-timeline");
  if (!el || !qa.length) return;
  el.innerHTML = qa.map(item => {
    const s   = item.score ?? 0;
    const cls = s >= 7 ? "score-pill--high" : s >= 5 ? "score-pill--mid" : "score-pill--low";
    return `<div class="timeline-item">
      <span class="timeline-q">Q${item.question_number}</span>
      <span class="timeline-question">${esc(item.question)}</span>
      <span class="score-pill ${cls}">${s}/10</span>
    </div>`;
  }).join("");
}

function renderSummary(d) {
  const el = $("summary-card");
  if (el) el.textContent = d.final_summary || "No summary available.";
}

function renderAccordion(d) {
  const qa = d.qa_history || [];
  const el = $("qa-accordion");
  if (!el || !qa.length) return;
  el.innerHTML = qa.map((item, i) => {
    const s   = item.score ?? 0;
    const cls = s >= 7 ? "score-pill--high" : s >= 5 ? "score-pill--mid" : "score-pill--low";
    const st  = (item.strengths  || []).map(x => `<span class="r-tag r-tag--green">${esc(x)}</span>`).join("");
    const wk  = (item.weaknesses || []).map(x => `<span class="r-tag r-tag--red">${esc(x)}</span>`).join("");
    return `<div class="acc-item" id="acc-${i}">
      <div class="acc-header" onclick="toggle(${i})">
        <span class="acc-num">Q${item.question_number}</span>
        <span class="acc-q">${esc(item.question)}</span>
        <span class="score-pill ${cls}">${s}/10</span>
        <span class="acc-chevron">▼</span>
      </div>
      <div class="acc-body">
        <div class="acc-answer">${item.answer ? esc(item.answer) : "<em>No answer</em>"}</div>
        <div class="acc-feedback">${esc(item.feedback || "")}</div>
        ${st || wk ? `<div class="tag-row">${st}${wk}</div>` : ""}
        ${item.ideal_answer_hints ? `<div class="acc-hint">💡 ${esc(item.ideal_answer_hints)}</div>` : ""}
      </div>
    </div>`;
  }).join("");
}

function toggle(i) { $(`acc-${i}`)?.classList.toggle("open"); }

function setupDownloads() {
  $("dl-json")?.addEventListener("click",   () => open(`/api/report/${SESSION_ID}/json`));
  $("dl-txt")?.addEventListener("click",    () => open(`/api/report/${SESSION_ID}/txt`));
  $("dl-report")?.addEventListener("click", () => open(`/api/report/${SESSION_ID}/report`));
}

const $ = id => document.getElementById(id);
function esc(s) {
  return String(s||"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
}
function cap(s) { return s ? s[0].toUpperCase()+s.slice(1) : "—"; }
