/**
 * VivaWala — Home Page
 */

const DOMAINS = [
  { name: "Python",                       icon: "🐍" },
  { name: "Java",                         icon: "☕" },
  { name: "Web Development",              icon: "🌐" },
  { name: "Machine Learning",             icon: "🤖" },
  { name: "Data Structures & Algorithms", icon: "🌲" },
  { name: "HR Interview",                 icon: "👔" },
  { name: "System Design",               icon: "🏗️" },
  { name: "DevOps & Cloud",               icon: "☁️" },
  { name: "Custom Domain",                icon: "✏️" },
];

let selectedProvider = "groq";
let selectedDomain   = null;
let questionCount    = 7;
let providerData     = {};

document.addEventListener("DOMContentLoaded", () => {
  renderDomains();
  setupStepper();
  document.getElementById("btn-start").addEventListener("click", start);
  document.getElementById("btn-start-hero").addEventListener("click", start);
  checkStatus();
});

/* ── Domains ── */
function renderDomains() {
  const grid = document.getElementById("domain-grid");
  DOMAINS.forEach(({ name, icon }) => {
    const btn = document.createElement("button");
    btn.className = "domain-card";
    btn.innerHTML = `<span class="domain-card__icon">${icon}</span><span>${name}</span>`;
    btn.addEventListener("click", () => {
      document.querySelectorAll(".domain-card").forEach(c => c.classList.remove("active"));
      btn.classList.add("active");
      selectedDomain = name;
      const wrap = document.getElementById("custom-domain-wrap");
      wrap.style.display = name === "Custom Domain" ? "block" : "none";
      if (name === "Custom Domain") document.getElementById("custom-domain-input").focus();
      updateBtn();
    });
    grid.appendChild(btn);
  });
}

/* ── Stepper ── */
function setupStepper() {
  const el = document.getElementById("q-count");
  document.getElementById("q-minus").addEventListener("click", () => {
    if (questionCount > 3) { questionCount--; el.textContent = questionCount; }
  });
  document.getElementById("q-plus").addEventListener("click", () => {
    if (questionCount < 10) { questionCount++; el.textContent = questionCount; }
  });
}

/* ── Start button ── */
function updateBtn() {
  const btn   = document.getElementById("btn-start");
  const hero  = document.getElementById("btn-start-hero");
  const alert = document.getElementById("provider-alert");
  const msg   = document.getElementById("provider-alert-msg");

  let blocked = !selectedDomain;
  let txt = "";

  if (!blocked) {
    if (selectedProvider === "groq" && providerData?.groq?.available === false) {
      const r = providerData.groq.reason || "";
      txt     = r.includes("GROQ_API_KEY")
        ? "Groq API key missing — add GROQ_API_KEY to your .env file and restart."
        : "Groq is unreachable. Check your connection.";
      blocked = true;
    }
    if (selectedProvider === "ollama" && providerData?.ollama?.running === false) {
      txt = "Ollama is offline. Run: ollama serve";
      blocked = true;
    }
  }

  btn.disabled  = blocked;
  hero.disabled = blocked;
  alert.style.display = txt ? "flex" : "none";
  if (txt) msg.textContent = txt;
}

/* ── Status ── */
async function checkStatus() {
  try {
    const r    = await fetch("/api/status");
    const data = await r.json();
    providerData = data.providers || {};

    const groq   = providerData.groq   || {};
    const ollama = providerData.ollama || {};
    const active = data.active_provider || "groq";

    selectedProvider = active;
    const activeProviderTag = document.getElementById("active-provider-tag");
    if (activeProviderTag) {
      activeProviderTag.textContent = active === "groq" ? "Groq ⚡" : "Ollama 🦙";
    }

    // Status pill
    const dot   = document.getElementById("status-dot");
    const label = document.getElementById("status-label");
    const ready = (active === "groq" && groq.available) || (active === "ollama" && ollama.running);
    dot.className   = ready ? "status-dot status-dot--green" : "status-dot status-dot--amber";
    label.textContent = ready ? (active === "groq" ? "Groq ready" : "Ollama ready") : "Check provider";

    updateBtn();
  } catch {
    document.getElementById("status-dot").className   = "status-dot status-dot--red";
    document.getElementById("status-label").textContent = "Backend offline";
  }
}

/* ── Start ── */
async function start() {
  let domain = selectedDomain;
  if (domain === "Custom Domain") {
    const v = document.getElementById("custom-domain-input").value.trim();
    if (!v) { alert("Enter a custom domain."); return; }
    domain = v;
  }
  if (!domain) return;

  const btn  = document.getElementById("btn-start");
  const hero = document.getElementById("btn-start-hero");
  btn.disabled = hero.disabled = true;
  btn.textContent = "Starting…";

  try {
    const resp = await fetch("/api/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ domain, num_questions: questionCount, provider: selectedProvider }),
    });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.error || "Could not start");

    sessionStorage.setItem("nh_session_id",     data.session_id);
    sessionStorage.setItem("nh_domain",          data.domain);
    sessionStorage.setItem("nh_provider",        data.provider);
    sessionStorage.setItem("nh_total_questions", data.total_questions);
    sessionStorage.setItem("nh_first_question",  data.first_question);

    window.location.href = "/interview";
  } catch (err) {
    alert(`Error: ${err.message}`);
    btn.disabled = hero.disabled = false;
    btn.textContent = "Begin interview →";
  }
}
