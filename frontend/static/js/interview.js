/**
 * VivaWala - Interview Page
 * Records microphone audio and sends it to the Python backend for STT.
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
  audioContext:  null,
  audioStream:   null,
  sourceNode:    null,
  processorNode: null,
  audioSamples:  [],
  sampleRate:    0,
  transcript:    "",
};

if (!S.sessionId) { window.location.href = "/"; }

function $(id) { return document.getElementById(id); }

var messages     = null;
var micBtn       = null;
var transcriptEl = null;
var placeholder  = null;
var btnSubmit    = null;
var statusLine   = null;
var progressEl   = null;
var evalPanel    = null;
var finishModal  = null;

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

  $("domain-pill").textContent   = S.domain;
  $("progress-pill").textContent = "Q 1 / " + S.total;
  var pp = $("provider-pill");
  if (pp) pp.textContent = S.provider === "groq" ? "Groq" : "Ollama";

  var endBtn = $("btn-end");
  if (endBtn) {
    endBtn.addEventListener("click", function() {
      if (confirm("End session and go home?")) window.location.href = "/";
    });
  }

  micBtn.addEventListener("click", toggleRecording);
  btnSubmit.addEventListener("click", submitAnswer);
  checkRecordingSupport();

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

function checkRecordingSupport() {
  var AudioContext = window.AudioContext || window.webkitAudioContext;
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia || !AudioContext) {
    setStatus("Voice recording is not supported in this browser.");
    micBtn.disabled = true;
    micBtn.title = "Voice recording not supported";
    return;
  }
  setStatus("Ready - Python STT");
}

function toggleRecording() {
  if (S.isRecording) {
    stopRecording();
  } else {
    startRecording();
  }
}

function startRecording() {
  S.transcript = "";
  S.audioSamples = [];
  S.sampleRate = 0;
  if (transcriptEl) transcriptEl.textContent = "";
  if (placeholder) placeholder.style.display = "none";
  btnSubmit.disabled = true;

  navigator.mediaDevices.getUserMedia({ audio: true })
    .then(function(stream) {
      var AudioContext = window.AudioContext || window.webkitAudioContext;
      S.audioStream = stream;
      S.audioContext = new AudioContext();
      S.sampleRate = S.audioContext.sampleRate;
      S.sourceNode = S.audioContext.createMediaStreamSource(stream);
      S.processorNode = S.audioContext.createScriptProcessor(4096, 1, 1);

      S.processorNode.onaudioprocess = function(e) {
        if (!S.isRecording) return;
        var input = e.inputBuffer.getChannelData(0);
        S.audioSamples.push(new Float32Array(input));
      };

      S.sourceNode.connect(S.processorNode);
      S.processorNode.connect(S.audioContext.destination);

      S.isRecording = true;
      micBtn.classList.add("is-recording");
      setStatus("Recording audio for Python STT... click mic to stop");
      pulseStatus();
    })
    .catch(function(e) {
      if (placeholder) placeholder.style.display = "inline";
      setStatus("Microphone access denied or unavailable: " + e.message);
    });
}

function stopRecording() {
  S.isRecording = false;
  micBtn.classList.remove("is-recording");
  btnSubmit.disabled = true;
  transcribeRecording();
}

function stopAudioStream() {
  if (S.processorNode) {
    try { S.processorNode.disconnect(); } catch(e) {}
    S.processorNode.onaudioprocess = null;
    S.processorNode = null;
  }
  if (S.sourceNode) {
    try { S.sourceNode.disconnect(); } catch(e) {}
    S.sourceNode = null;
  }
  if (S.audioContext) {
    try { S.audioContext.close(); } catch(e) {}
    S.audioContext = null;
  }
  if (S.audioStream) {
    S.audioStream.getTracks().forEach(function(track) { track.stop(); });
    S.audioStream = null;
  }
}

function transcribeRecording() {
  stopAudioStream();

  if (!S.audioSamples.length) {
    if (placeholder) placeholder.style.display = "inline";
    transcriptEl.textContent = "";
    setStatus("Nothing recorded - try again");
    return;
  }

  setStatus("Transcribing with Python...");
  transcriptEl.textContent = "Transcribing...";

  var blob = encodeWav(S.audioSamples, S.sampleRate || 44100);
  S.audioSamples = [];
  S.sampleRate = 0;

  blobToBase64(blob)
    .then(function(audioBase64) {
      return fetch("/api/transcribe", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          audio: audioBase64,
          mime_type: "audio/wav",
        }),
      });
    })
    .then(function(r) {
      return r.json().then(function(d) { return { ok: r.ok, data: d }; });
    })
    .then(function(res) {
      if (!res.ok || res.data.error) {
        throw new Error(res.data.error || "Transcription failed");
      }

      var finalText = (res.data.text || "").trim();
      S.transcript = finalText;

      if (finalText) {
        transcriptEl.textContent = finalText;
        btnSubmit.disabled = false;
        setStatus("Ready - transcribed by " + (res.data.engine || "Python"));
      } else {
        if (placeholder) placeholder.style.display = "inline";
        transcriptEl.textContent = "";
        setStatus("No speech detected - try again");
      }
    })
    .catch(function(err) {
      if (placeholder) placeholder.style.display = "inline";
      transcriptEl.textContent = "";
      setStatus("Transcription error: " + err.message);
    });
}

function encodeWav(samples, sampleRate) {
  var merged = mergeSamples(samples);
  var buffer = new ArrayBuffer(44 + merged.length * 2);
  var view = new DataView(buffer);

  writeString(view, 0, "RIFF");
  view.setUint32(4, 36 + merged.length * 2, true);
  writeString(view, 8, "WAVE");
  writeString(view, 12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  writeString(view, 36, "data");
  view.setUint32(40, merged.length * 2, true);

  var offset = 44;
  for (var i = 0; i < merged.length; i++, offset += 2) {
    var sample = Math.max(-1, Math.min(1, merged[i]));
    view.setInt16(offset, sample < 0 ? sample * 0x8000 : sample * 0x7fff, true);
  }

  return new Blob([view], { type: "audio/wav" });
}

function mergeSamples(samples) {
  var length = samples.reduce(function(total, chunk) { return total + chunk.length; }, 0);
  var merged = new Float32Array(length);
  var offset = 0;
  samples.forEach(function(chunk) {
    merged.set(chunk, offset);
    offset += chunk.length;
  });
  return merged;
}

function writeString(view, offset, value) {
  for (var i = 0; i < value.length; i++) {
    view.setUint8(offset + i, value.charCodeAt(i));
  }
}

function blobToBase64(blob) {
  return new Promise(function(resolve, reject) {
    var reader = new FileReader();
    reader.onloadend = function() { resolve(reader.result); };
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });
}

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
    .replace(/&/g, "&amp;").replace(/</g, "&lt;")
    .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function submitAnswer() {
  var answer = S.transcript.trim();
  if (!answer) return;

  appendUser(answer);

  S.transcript = "";
  if (transcriptEl) transcriptEl.textContent = "";
  if (placeholder) placeholder.style.display = "inline";
  btnSubmit.disabled = true;
  micBtn.disabled = true;
  setStatus("Evaluating...");

  fetch("/api/answer", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: S.sessionId, answer: answer }),
  })
  .then(function(r) {
    return r.json().then(function(d) { return { ok: r.ok, data: d }; });
  })
  .then(function(res) {
    if (!res.ok) throw new Error(res.data.error || "Evaluation failed");
    var data = res.data;
    var ev = data.evaluation;

    updateEvalPanel(ev);
    S.scores.push(ev.score);
    updateStats();
    updateProgress(data.question_number, S.total);

    appendAI(
      "<strong>" + ev.score + "/10</strong> - " + esc(ev.verdict) + "<br/>"
      + '<span style="color:var(--ink3);font-size:0.85em;">' + esc(ev.feedback) + "</span>"
      + (ev.follow_up
        ? '<br/><em style="color:var(--ink4);font-size:0.82em;">Follow-up: ' + esc(ev.follow_up) + "</em>"
        : ""),
      true
    );

    micBtn.disabled = false;

    if (data.finished) {
      setStatus("Interview complete - generating report...");
      setTimeout(finishUp, 1500);
    } else {
      S.currentQ = data.next_question_number;
      $("progress-pill").textContent = "Q " + S.currentQ + " / " + S.total;
      setStatus("Ready - Python STT");
      setTimeout(function() {
        appendQuestion(data.next_question, S.currentQ);
      }, 1200);
    }
  })
  .catch(function(err) {
    micBtn.disabled = false;
    setStatus("Error: " + err.message);
    appendAI("Warning: " + err.message, false);
  });
}

function finishUp() {
  if (finishModal) finishModal.style.display = "flex";
  fetch("/api/finish", {
    method: "POST",
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
    appendAI("Warning: Could not generate report: " + err.message, false);
  });
}

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
  if (numEl) numEl.textContent = score;
  if (barEl) barEl.style.width = (score * 10) + "%";
  if (vrdEl) vrdEl.textContent = ev.verdict || "";

  var fbSec = $("ev-feedback");
  var fbTxt = $("feedback-text");
  if (fbSec) fbSec.style.display = "flex";
  if (fbTxt) fbTxt.textContent = ev.feedback || "";

  var s = ev.strengths || [];
  var w = ev.weaknesses || [];
  if (s.length || w.length) {
    var swSec = $("ev-sw");
    var slEl = $("strengths-list");
    var wlEl = $("weaknesses-list");
    if (swSec) swSec.style.display = "flex";
    if (slEl) slEl.innerHTML = s.map(function(x) { return '<li class="strength">' + esc(x) + "</li>"; }).join("");
    if (wlEl) wlEl.innerHTML = w.map(function(x) { return '<li class="weakness">' + esc(x) + "</li>"; }).join("");
  }

  if (ev.ideal_answer_hints) {
    var hintBox = $("iv-hint");
    var hintTxt = $("hint-text");
    if (hintBox) hintBox.style.display = "block";
    if (hintTxt) hintTxt.textContent = ev.ideal_answer_hints;
  }
}

function updateStats() {
  var scores = S.scores;
  var avg = scores.reduce(function(a, b) { return a + b; }, 0) / scores.length;
  var avgEl = $("stat-avg");
  var qEl = $("stat-q");
  var trEl = $("stat-trend");
  if (avgEl) avgEl.textContent = avg.toFixed(1);
  if (qEl) qEl.textContent = scores.length;
  if (trEl && scores.length >= 2) {
    var d = scores[scores.length - 1] - scores[scores.length - 2];
    trEl.textContent = d > 0 ? "up" : d < 0 ? "down" : "same";
  }
}

function updateProgress(current, total) {
  if (progressEl) progressEl.style.width = ((current / total) * 100) + "%";
}

function setStatus(text) {
  if (statusLine) {
    statusLine.textContent = text;
    statusLine.style.opacity = "1";
  }
}

var pulseInterval = null;
function pulseStatus() {
  if (pulseInterval) clearInterval(pulseInterval);
  var dots = ["Recording for Python STT .", "Recording for Python STT ..", "Recording for Python STT ..."];
  var i = 0;
  pulseInterval = setInterval(function() {
    if (!S.isRecording) { clearInterval(pulseInterval); return; }
    setStatus(dots[i++ % 3]);
  }, 500);
}

var style = document.createElement("style");
style.textContent = "@keyframes msgIn { from { opacity:0; transform:translateY(6px); } to { opacity:1; transform:translateY(0); } }";
document.head.appendChild(style);
