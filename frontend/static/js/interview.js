/**
 * VivaWala — Interview Page
 * Uses Web Speech API (browser-native) for transcription.
 * No audio upload to backend — works on Render / any cloud server.
 */

var S = {
  sessionId:     sessionStorage.getItem("nh_session_id"),
  domain:        sessionStorage.getItem("nh_domain")          || "Unknown",
  provider:      sessionStorage.getItem("nh_provider")        || "groq",
  total:         parseInt(sessionStorage.getItem("nh_total_questions")) || 7,
  firstQuestion: sessionStorage.getItem("nh_first_question")  || "",
  currentQ:      1,
  scores:        [],
  isRecording:   false,
  recognition:   null,   // Web Speech API SpeechRecognition
  transcript:    "",
  interimText:   "",
};

if (!S.sessionId) { window.location.href = "/"; }

function $(id) { return document.getElementById(id); }

var messages    = null;
var micBtn      = null;
var transcriptEl= null;
var placeholder = null;
var btnSubmit   = null;
var statusLine  = null;
var progressEl  = null;
var evalPanel   = null;
var finishModal = null;

/* ══════════════════════════════
   BOOT
   ══════════════════════════════ */
document.addEventListener("DOMContentLoaded", function() {
  messages     = $("iv-messages");
  micBtn       = $("mic-btn");
  transcriptEl = $("iv-transcript");
  placeholder  = $("transcript-placeholder");
  btnSubmit    = $("btn-submit");
  statusLine   = $("iv-status-line");
  progressEl   = $("progress-fill");
  evalPanel    = $("iv-eval");
  finishModal  = $("finish-modal");

  // Header pills
  $("domain-pill").textContent   = S.domain;
  $("progress-pill").textContent = "Q 1 / " + S.total;
  var pp = $("provider-pill");
  if (pp) pp.textContent = S.provider === "groq" ? "⚡ Groq" : "🦙 Ollama";

  // End session
  var endBtn = $("btn-end");
  if (endBtn) {
    endBtn.addEventListener("click", function() {
      if (confirm("End session and go home?")) window.location.href = "/";
    });
  }

  micBtn.addEventListener("click", toggleRecording);
  btnSubmit.addEventListener("click", submitAnswer);

  // Check Web Speech API support
  checkSpeechSupport();

  // Welcome messages
  setTimeout(function() {
    appendAI(
      "Welcome. I'll ask you " + S.total + " questions on <strong>" + S.domain + "</strong>. "
      + "Click the mic button and speak your answer clearly.",
      false
    );
    setTimeout(function() {
      appendQuestion(S.firstQuestion, 1);
    }, 900);
  }, 200);
});

/* ══════════════════════════════
   WEB SPEECH API SETUP
   ══════════════════════════════ */
function checkSpeechSupport() {
  var SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    setStatus("⚠ Your browser doesn't support voice input. Use Chrome or Edge.");
    micBtn.disabled = true;
    micBtn.title    = "Voice not supported — use Chrome or Edge";
    return;
  }
  setStatus("Ready");
}

function createRecognition() {
  var SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) return null;

  var r = new SpeechRecognition();
  r.continuous      = true;   // keep listening until stopped
  r.interimResults  = true;   // show live partial results
  r.lang            = "en-US";
  r.maxAlternatives = 1;

  r.onstart = function() {
    S.isRecording = true;
    micBtn.classList.add("is-recording");
    if (placeholder) placeholder.style.display = "none";
    transcriptEl.textContent = "";
    btnSubmit.disabled = true;
    setStatus("Listening… click mic to stop");
    pulseStatus();
  };

  r.onresult = function(e) {
    var finalText   = "";
    var interimText = "";

    for (var i = e.resultIndex; i < e.results.length; i++) {
      var t = e.results[i][0].transcript;
      if (e.results[i].isFinal) {
        finalText += t + " ";
      } else {
        interimText += t;
      }
    }

    if (finalText) {
      S.transcript += finalText;
    }

    // Show combined final + interim live
    var display = S.transcript + interimText;
    transcriptEl.textContent = display.trim();

    if (S.transcript.trim()) {
      btnSubmit.disabled = false;
    }
  };

  r.onerror = function(e) {
    var msg = e.error;
    if (msg === "not-allowed") {
      setStatus("Microphone access denied — allow mic in browser settings");
    } else if (msg === "no-speech") {
      setStatus("No speech detected — try speaking again");
    } else if (msg === "network") {
      setStatus("Network error — check your connection");
    } else {
      setStatus("Error: " + msg);
    }
    stopRecognition();
  };

  r.onend = function() {
    // Auto-stop when recognition ends
    if (S.isRecording) {
      stopRecognition();
    }
  };

  return r;
}

/* ══════════════════════════════
   RECORDING CONTROLS
   ══════════════════════════════ */
function toggleRecording() {
  if (S.isRecording) {
    stopRecognition();
  } else {
    startRecognition();
  }
}

function startRecognition() {
  // Clear previous transcript
  S.transcript  = "";
  S.interimText = "";
  if (transcriptEl) transcriptEl.textContent = "";
  if (placeholder)  placeholder.style.display = "none";
  btnSubmit.disabled = true;

  S.recognition = createRecognition();
  if (!S.recognition) {
    setStatus("Voice input not supported. Use Chrome or Edge.");
    return;
  }

  try {
    S.recognition.start();
  } catch(e) {
    setStatus("Could not start microphone: " + e.message);
  }
}

function stopRecognition() {
  S.isRecording = false;
  micBtn.classList.remove("is-recording");

  if (S.recognition) {
    try { S.recognition.stop(); } catch(e) {}
    S.recognition = null;
  }

  var finalText = S.transcript.trim();
  if (finalText) {
    transcriptEl.textContent = finalText;
    btnSubmit.disabled = false;
    setStatus("Ready — click send or re-record");
  } else {
    if (placeholder) placeholder.style.display = "inline";
    transcriptEl.textContent = "";
    setStatus("Nothing captured — try again");
  }
}

/* ══════════════════════════════
   CHAT HELPERS
   ══════════════════════════════ */
function appendAI(html, withTyping) {
  if (withTyping === false) { addBubble("ai", html); return; }
  var typing = typingBubble();
  messages.appendChild(typing);
  scrollBottom();
  setTimeout(function() {
    typing.remove();
    addBubble("ai", html);
  }, 650 + Math.random() * 250);
}

function appendQuestion(q, num) {
  var typing = typingBubble();
  messages.appendChild(typing);
  scrollBottom();
  setTimeout(function() {
    typing.remove();
    addBubble("ai",
      '<div class="iv-bubble__qnum">Question ' + num + ' of ' + S.total + '</div>'
      + esc(q)
    );
  }, 500 + Math.random() * 200);
}

function appendUser(text) { addBubble("user", esc(text)); }

function addBubble(role, html) {
  var row = document.createElement("div");
  row.className = "iv-msg iv-msg--" + role;
  row.style.animation = "msgIn 0.22s ease forwards";
  var bub = document.createElement("div");
  bub.className = "iv-bubble iv-bubble--" + role;
  bub.innerHTML = html;
  row.appendChild(bub);
  messages.appendChild(row);
  scrollBottom();
}

function typingBubble() {
  var row = document.createElement("div");
  row.className = "iv-msg iv-msg--ai";
  row.innerHTML = '<div class="iv-bubble iv-bubble--ai">'
    + '<div class="iv-typing">'
    + '<div class="iv-dot"></div>'
    + '<div class="iv-dot"></div>'
    + '<div class="iv-dot"></div>'
    + '</div></div>';
  return row;
}

function scrollBottom() {
  if (messages) messages.scrollTo({ top: messages.scrollHeight, behavior: "smooth" });
}

function esc(s) {
  return String(s || "")
    .replace(/&/g,"&amp;").replace(/</g,"&lt;")
    .replace(/>/g,"&gt;").replace(/"/g,"&quot;");
}

/* ══════════════════════════════
   SUBMIT ANSWER
   ══════════════════════════════ */
function submitAnswer() {
  var answer = S.transcript.trim();
  if (!answer) return;

  appendUser(answer);

  // Clear transcript
  S.transcript = "";
  if (transcriptEl) transcriptEl.textContent = "";
  if (placeholder)  { placeholder.style.display = "inline"; }
  btnSubmit.disabled = true;
  micBtn.disabled    = true;
  setStatus("Evaluating…");

  fetch("/api/answer", {
    method:  "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: S.sessionId, answer: answer }),
  })
  .then(function(r) {
    return r.json().then(function(d) { return { ok: r.ok, data: d }; });
  })
  .then(function(res) {
    if (!res.ok) throw new Error(res.data.error || "Evaluation failed");
    var data = res.data;
    var ev   = data.evaluation;

    updateEvalPanel(ev);
    S.scores.push(ev.score);
    updateStats();
    updateProgress(data.question_number, S.total);

    appendAI(
      "<strong>" + ev.score + "/10</strong> — " + esc(ev.verdict) + "<br/>"
      + '<span style="color:var(--ink3);font-size:0.85em;">' + esc(ev.feedback) + "</span>"
      + (ev.follow_up
        ? '<br/><em style="color:var(--ink4);font-size:0.82em;">↳ ' + esc(ev.follow_up) + "</em>"
        : ""),
      true
    );

    micBtn.disabled = false;

    if (data.finished) {
      setStatus("Interview complete — generating report…");
      setTimeout(finishUp, 1500);
    } else {
      S.currentQ = data.next_question_number;
      $("progress-pill").textContent = "Q " + S.currentQ + " / " + S.total;
      setStatus("Ready");
      setTimeout(function() {
        appendQuestion(data.next_question, S.currentQ);
      }, 1200);
    }
  })
  .catch(function(err) {
    micBtn.disabled = false;
    setStatus("Error: " + err.message);
    appendAI("⚠ " + err.message, false);
  });
}

/* ══════════════════════════════
   FINISH
   ══════════════════════════════ */
function finishUp() {
  if (finishModal) finishModal.style.display = "flex";
  fetch("/api/finish", {
    method:  "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: S.sessionId }),
  })
  .then(function(r) { return r.json().then(function(d) { return { ok: r.ok, data: d }; }); })
  .then(function(res) {
    if (!res.ok) throw new Error(res.data.error);
    window.location.href = "/results/" + S.sessionId;
  })
  .catch(function(err) {
    if (finishModal) finishModal.style.display = "none";
    appendAI("⚠ Could not generate report: " + err.message, false);
  });
}

/* ══════════════════════════════
   EVAL PANEL
   ══════════════════════════════ */
function updateEvalPanel(ev) {
  var score = ev.score || 0;

  if (evalPanel) evalPanel.classList.add("visible");
  var awaitEl = $("iv-await");
  var scoreEl = $("iv-score");
  if (awaitEl) awaitEl.style.display = "none";
  if (scoreEl) scoreEl.style.display = "block";

  var numEl = $("score-num");
  var barEl = $("score-bar");
  var vrdEl = $("score-verdict");
  if (numEl) numEl.textContent  = score;
  if (barEl) barEl.style.width  = (score * 10) + "%";
  if (vrdEl) vrdEl.textContent  = ev.verdict || "";

  var fbSec = $("ev-feedback");
  var fbTxt = $("feedback-text");
  if (fbSec) fbSec.style.display = "flex";
  if (fbTxt) fbTxt.textContent   = ev.feedback || "";

  var s = ev.strengths  || [];
  var w = ev.weaknesses || [];
  if (s.length || w.length) {
    var swSec = $("ev-sw");
    var slEl  = $("strengths-list");
    var wlEl  = $("weaknesses-list");
    if (swSec) swSec.style.display = "flex";
    if (slEl)  slEl.innerHTML  = s.map(function(x) { return '<li class="strength">' + esc(x) + "</li>"; }).join("");
    if (wlEl)  wlEl.innerHTML  = w.map(function(x) { return '<li class="weakness">' + esc(x) + "</li>"; }).join("");
  }

  if (ev.ideal_answer_hints) {
    var hintBox = $("iv-hint");
    var hintTxt = $("hint-text");
    if (hintBox) hintBox.style.display = "block";
    if (hintTxt) hintTxt.textContent   = ev.ideal_answer_hints;
  }
}

function updateStats() {
  var scores = S.scores;
  var avg    = scores.reduce(function(a, b) { return a + b; }, 0) / scores.length;
  var avgEl  = $("stat-avg");
  var qEl    = $("stat-q");
  var trEl   = $("stat-trend");
  if (avgEl) avgEl.textContent = avg.toFixed(1);
  if (qEl)   qEl.textContent   = scores.length;
  if (trEl && scores.length >= 2) {
    var d = scores[scores.length - 1] - scores[scores.length - 2];
    trEl.textContent = d > 0 ? "↑" : d < 0 ? "↓" : "→";
  }
}

function updateProgress(current, total) {
  if (progressEl) progressEl.style.width = ((current / total) * 100) + "%";
}

/* ══════════════════════════════
   STATUS LINE
   ══════════════════════════════ */
function setStatus(text) {
  if (statusLine) {
    statusLine.textContent = text;
    statusLine.style.opacity = "1";
  }
}

var pulseInterval = null;
function pulseStatus() {
  if (pulseInterval) clearInterval(pulseInterval);
  var dots = ["Listening ·", "Listening ··", "Listening ···"];
  var i = 0;
  pulseInterval = setInterval(function() {
    if (!S.isRecording) { clearInterval(pulseInterval); return; }
    setStatus(dots[i++ % 3]);
  }, 500);
}

/* Fade-up animation */
var style = document.createElement("style");
style.textContent = "@keyframes msgIn { from { opacity:0; transform:translateY(6px); } to { opacity:1; transform:translateY(0); } }";
document.head.appendChild(style);
