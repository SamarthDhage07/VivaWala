/**
 * VivaWala — Interview Page
 * Cognito-style centered card chat with voice input.
 */

const S = {
  sessionId:     sessionStorage.getItem("nh_session_id"),
  domain:        sessionStorage.getItem("nh_domain")          || "Unknown",
  provider:      sessionStorage.getItem("nh_provider")        || "groq",
  total:         parseInt(sessionStorage.getItem("nh_total_questions")) || 7,
  firstQuestion: sessionStorage.getItem("nh_first_question")  || "",
  currentQ:      1,
  scores:        [],
  isRecording:   false,
  mediaRecorder: null,
  audioChunks:   [],
  audioCtx:      null,
  analyser:      null,
  animFrame:     null,
  transcript:    "",
};

if (!S.sessionId) { window.location.href = "/"; }

const $  = id => document.getElementById(id);
const messages   = $("iv-messages");
const micBtn     = $("mic-btn");
const transcript = $("iv-transcript");
const placeholder= $("transcript-placeholder");
const btnSubmit  = $("btn-submit");
const statusLine = $("iv-status-line");
const progressEl = $("progress-fill");
const evalPanel  = $("iv-eval");
const finishModal= $("finish-modal");

/* ── Boot ── */
document.addEventListener("DOMContentLoaded", () => {
  // Header pills
  $("domain-pill").textContent   = S.domain;
  $("progress-pill").textContent = `Q 1 / ${S.total}`;
  const pp = $("provider-pill");
  pp.textContent = S.provider === "groq" ? "⚡ Groq" : "🦙 Ollama";

  // End session
  $("btn-end").addEventListener("click", () => {
    if (confirm("End session and go home?")) window.location.href = "/";
  });

  micBtn.addEventListener("click", toggleRecording);
  btnSubmit.addEventListener("click", submitAnswer);

  loadSessions();

  // Open messages
  setTimeout(() => {
    appendAI(
      `Welcome. I'll be asking you ${S.total} questions on <strong>${S.domain}</strong>. ` +
      `Click the mic button and speak your answer clearly.`,
      false
    );
    setTimeout(() => appendQuestion(S.firstQuestion, 1), 850);
  }, 150);
});

/* ══════════════════
   CHAT HELPERS
   ══════════════════ */
function appendAI(html, withTyping = true) {
  if (!withTyping) { addBubble("ai", html); return; }
  const typing = typingBubble();
  messages.appendChild(typing);
  scrollBottom();
  setTimeout(() => { typing.remove(); addBubble("ai", html); }, 650 + Math.random() * 250);
}

function appendQuestion(q, num) {
  const typing = typingBubble();
  messages.appendChild(typing);
  scrollBottom();
  setTimeout(() => {
    typing.remove();
    addBubble("ai",
      `<div class="iv-bubble__qnum">Question ${num} of ${S.total}</div>${esc(q)}`
    );
  }, 480 + Math.random() * 200);
}

function appendUser(text) { addBubble("user", esc(text)); }

function addBubble(role, html) {
  const row = document.createElement("div");
  row.className = `iv-msg iv-msg--${role}`;
  const bub = document.createElement("div");
  bub.className = `iv-bubble iv-bubble--${role}`;
  bub.innerHTML = html;
  row.appendChild(bub);
  messages.appendChild(row);
  scrollBottom();
}

function typingBubble() {
  const row = document.createElement("div");
  row.className = "iv-msg iv-msg--ai";
  row.innerHTML = `
    <div class="iv-bubble iv-bubble--ai">
      <div class="iv-typing">
        <div class="iv-dot"></div>
        <div class="iv-dot"></div>
        <div class="iv-dot"></div>
      </div>
    </div>`;
  return row;
}

function scrollBottom() {
  messages.scrollTo({ top: messages.scrollHeight, behavior: "smooth" });
}

function esc(s) {
  return String(s || "")
    .replace(/&/g,"&amp;").replace(/</g,"&lt;")
    .replace(/>/g,"&gt;").replace(/"/g,"&quot;");
}

/* ══════════════════
   VOICE RECORDING
   ══════════════════ */
async function toggleRecording() {
  S.isRecording ? stopRecording() : await startRecording();
}

async function startRecording() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    S.audioChunks = [];

    S.audioCtx  = new AudioContext();
    S.analyser  = S.audioCtx.createAnalyser();
    S.analyser.fftSize = 256;
    S.audioCtx.createMediaStreamSource(stream).connect(S.analyser);

    const mime = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
      ? "audio/webm;codecs=opus" : "audio/webm";
    S.mediaRecorder = new MediaRecorder(stream, { mimeType: mime });
    S.mediaRecorder.addEventListener("dataavailable", e => {
      if (e.data.size > 0) S.audioChunks.push(e.data);
    });
    S.mediaRecorder.addEventListener("stop", onStop);
    S.mediaRecorder.start(100);

    S.isRecording = true;
    micBtn.classList.add("is-recording");
    btnSubmit.disabled = true;

    // Clear transcript
    S.transcript = "";
    if (placeholder) placeholder.style.display = "none";
    transcript.textContent = "";

    setStatus("Recording… click mic to stop");
    pulseStatus();
  } catch {
    setStatus("Microphone access denied");
  }
}

function stopRecording() {
  if (!S.mediaRecorder) return;
  S.mediaRecorder.stop();
  S.mediaRecorder.stream.getTracks().forEach(t => t.stop());
  S.isRecording = false;
  micBtn.classList.remove("is-recording");
  setStatus("Converting speech to text…");
}

async function onStop() {
  if (S.audioCtx) { await S.audioCtx.close(); S.audioCtx = null; }
  if (!S.audioChunks.length) { setStatus("No audio captured"); return; }

  const blob = new Blob(S.audioChunks, { type: "audio/webm" });
  const b64  = await toBase64(blob);

  try {
    const resp = await fetch("/api/transcribe", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ audio: b64, mime_type: "audio/webm" }),
    });
    const data = await resp.json();

    if (data.text?.trim()) {
      S.transcript = data.text.trim();
      if (placeholder) placeholder.style.display = "none";
      transcript.textContent = S.transcript;
      btnSubmit.disabled = false;
      setStatus("Ready — click send or re-record");
    } else {
      if (placeholder) placeholder.style.display = "inline";
      transcript.textContent = "";
      setStatus(data.error || "Could not hear you — try again");
    }
  } catch {
    setStatus("Transcription failed — is the server running?");
  }
}

/* ══════════════════
   SUBMIT ANSWER
   ══════════════════ */
async function submitAnswer() {
  const answer = S.transcript.trim();
  if (!answer) return;

  appendUser(answer);

  // Clear transcript area
  S.transcript = "";
  transcript.textContent = "";
  if (placeholder) { placeholder.style.display = "inline"; }
  btnSubmit.disabled = true;
  micBtn.disabled    = true;
  setStatus("Evaluating…");

  try {
    const resp = await fetch("/api/answer", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: S.sessionId, answer }),
    });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.error || "Evaluation failed");

    const ev = data.evaluation;
    updateEvalPanel(ev);
    S.scores.push(ev.score);
    updateStats();
    updateProgress(data.question_number, S.total);

    // Feedback bubble
    appendAI(
      `<strong>${ev.score}/10</strong> — ${esc(ev.verdict)}<br/>` +
      `<span style="color:var(--ink3);font-size:0.85em;">${esc(ev.feedback)}</span>` +
      (ev.follow_up ? `<br/><em style="color:var(--ink4);font-size:0.82em;">↳ ${esc(ev.follow_up)}</em>` : ""),
      true
    );

    micBtn.disabled = false;

    if (data.finished) {
      setStatus("Interview complete — generating report…");
      setTimeout(finishUp, 1500);
    } else {
      S.currentQ = data.next_question_number;
      $("progress-pill").textContent = `Q ${S.currentQ} / ${S.total}`;
      setStatus("Ready");
      setTimeout(() => appendQuestion(data.next_question, S.currentQ), 1200);
    }
  } catch (err) {
    micBtn.disabled = false;
    setStatus(`Error: ${err.message}`);
    appendAI(`⚠ ${err.message}`, false);
  }
}

/* ══════════════════
   FINISH
   ══════════════════ */
async function finishUp() {
  finishModal.style.display = "flex";
  try {
    const resp = await fetch("/api/finish", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: S.sessionId }),
    });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.error);
    window.location.href = `/results/${S.sessionId}`;
  } catch (err) {
    finishModal.style.display = "none";
    appendAI(`⚠ Could not generate report: ${err.message}`, false);
  }
}

/* ══════════════════
   EVAL PANEL
   ══════════════════ */
function updateEvalPanel(ev) {
  const score = ev.score ?? 0;

  // Show panel
  evalPanel.classList.add("visible");
  $("iv-await").style.display = "none";
  $("iv-score").style.display = "block";

  $("score-num").textContent   = score;
  $("score-bar").style.width   = `${score * 10}%`;
  $("score-verdict").textContent = ev.verdict || "";

  // Feedback
  $("ev-feedback").style.display = "flex";
  $("feedback-text").textContent  = ev.feedback || "";

  // S&W
  const s = ev.strengths  || [];
  const w = ev.weaknesses || [];
  if (s.length || w.length) {
    $("ev-sw").style.display  = "flex";
    $("strengths-list").innerHTML  = s.map(x => `<li class="strength">${esc(x)}</li>`).join("");
    $("weaknesses-list").innerHTML = w.map(x => `<li class="weakness">${esc(x)}</li>`).join("");
  }

  // Hint
  if (ev.ideal_answer_hints) {
    $("iv-hint").style.display = "block";
    $("hint-text").textContent  = ev.ideal_answer_hints;
  }
}

function updateStats() {
  const avg = S.scores.reduce((a, b) => a + b, 0) / S.scores.length;
  $("stat-avg").textContent = avg.toFixed(1);
  $("stat-q").textContent   = S.scores.length;
  if (S.scores.length >= 2) {
    const d = S.scores[S.scores.length - 1] - S.scores[S.scores.length - 2];
    $("stat-trend").textContent = d > 0 ? "↑" : d < 0 ? "↓" : "→";
  }
}

function updateProgress(current, total) {
  if (progressEl) progressEl.style.width = `${(current / total) * 100}%`;
}

/* ══════════════════
   STATUS LINE
   ══════════════════ */
function setStatus(text) {
  statusLine.textContent = text;
  statusLine.style.opacity = "1";
}
function pulseStatus() {
  let t = 0;
  const dots = ["Recording ·", "Recording ··", "Recording ···"];
  const id = setInterval(() => {
    if (!S.isRecording) { clearInterval(id); return; }
    statusLine.textContent = dots[t++ % 3];
  }, 450);
}

/* ══════════════════
   SIDEBAR
   ══════════════════ */
async function loadSessions() {
  try {
    const resp = await fetch("/api/sessions");
    const list = await resp.json();
    // no sidebar in this layout — sessions accessible from results
  } catch {}
}

/* ══════════════════
   UTILS
   ══════════════════ */
function toBase64(blob) {
  return new Promise((res, rej) => {
    const r = new FileReader();
    r.onload  = () => res(r.result);
    r.onerror = rej;
    r.readAsDataURL(blob);
  });
}
