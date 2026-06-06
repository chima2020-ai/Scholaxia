const API = "https://scholaxia.onrender.com";
const token = localStorage.getItem("sia_token") || "";
const userName = localStorage.getItem("sia_name") || "";

// ── State ──────────────────────────────────────────────────────────────────
let allExams = [];
let currentExam = null;     // full exam data with questions
let currentSession = null;  // { session_id, exam_id, duration_minutes }
let answers = {};           // { question_id: "A"|"B"|"C"|"D" }
let currentQ = 0;
let timerInterval = null;
let secondsLeft = 0;
let isOffline = !navigator.onLine;
let lastResult = null;
let lastReviewData = null;

// ── Init ───────────────────────────────────────────────────────────────────
window.onload = () => {
  if (!token) { window.location.href = "auth.html"; return; }
  const name = firstName(userName);
  document.getElementById("header-user").textContent = name;

  window.addEventListener("online",  () => { isOffline = false; document.getElementById("offline-banner").style.display = "none"; loadExams(); });
  window.addEventListener("offline", () => { isOffline = true;  document.getElementById("offline-banner").style.display = "block"; loadExams(); });

  if (isOffline) document.getElementById("offline-banner").style.display = "block";
  loadExams();
};

// ── Screen helpers ─────────────────────────────────────────────────────────
function showScreen(id) {
  document.querySelectorAll(".screen").forEach(s => s.classList.remove("active"));
  document.getElementById(id).classList.add("active");
}

// ── Load exam list ─────────────────────────────────────────────────────────
async function loadExams() {
  const grid = document.getElementById("exams-grid");

  if (isOffline) {
    const cached = getOfflineExams();
    if (!cached.length) {
      grid.innerHTML = `<div class="empty-state">No downloaded exams available offline.</div>`;
    } else {
      allExams = cached;
      renderExamGrid(cached);
    }
    return;
  }

  grid.innerHTML = `<div class="loading-state">Loading exams…</div>`;
  try {
    const res = await fetch(`${API}/api/v1/cbt/exams`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (res.status === 401) { window.location.href = "auth.html"; return; }
    const data = await res.json();
    allExams = data;
    renderExamGrid(data);
  } catch (e) {
    // Fallback to offline cache
    const cached = getOfflineExams();
    if (cached.length) {
      allExams = cached;
      renderExamGrid(cached);
      document.getElementById("offline-banner").style.display = "block";
    } else {
      grid.innerHTML = `<div class="empty-state">Could not load exams. Check your connection.</div>`;
    }
  }
}

function filterExams() {
  const type = document.getElementById("filter-type").value;
  const subj = document.getElementById("filter-subject").value.toLowerCase();
  const filtered = allExams.filter(e => {
    if (type && e.exam_type !== type) return false;
    if (subj && !e.subject.toLowerCase().includes(subj)) return false;
    return true;
  });
  renderExamGrid(filtered);
}

function renderExamGrid(exams) {
  const grid = document.getElementById("exams-grid");
  if (!exams.length) {
    grid.innerHTML = `<div class="empty-state">No exams found for this filter.</div>`;
    return;
  }
  const offlineIds = getOfflineExams().map(e => e.id);
  grid.innerHTML = exams.map(e => {
    const isLocal = offlineIds.includes(e.id);
    return `
      <div class="exam-card ${isLocal ? "offline-available" : ""}" onclick="startExam('${e.id}')">
        <div class="exam-badge badge-${e.exam_type}">${e.exam_type}</div>
        <h3>${escHtml(e.title)}</h3>
        <p>${escHtml(e.subject)}</p>
        <div class="exam-card-footer">
          <div class="info">${e.total_questions} questions · ${e.duration_minutes} min</div>
          <div style="display:flex;gap:8px">
            ${!isLocal ? `<button class="btn-download" onclick="event.stopPropagation();downloadForOffline('${e.id}','${escHtml(e.title)}')" title="Download for offline">📥</button>` : ""}
            <button class="btn-start">Start</button>
          </div>
        </div>
      </div>
    `;
  }).join("");
}

// ── Offline storage ────────────────────────────────────────────────────────
function getOfflineExams() {
  try { return JSON.parse(localStorage.getItem("cbt_offline_exams") || "[]"); } catch { return []; }
}

function saveOfflineExam(examData) {
  const exams = getOfflineExams();
  const idx = exams.findIndex(e => e.id === examData.id);
  if (idx >= 0) exams[idx] = examData; else exams.push(examData);
  localStorage.setItem("cbt_offline_exams", JSON.stringify(exams));
}

async function downloadForOffline(examId, title) {
  try {
    const res = await fetch(`${API}/api/v1/cbt/exams/${examId}/download`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) { alert("Download failed."); return; }
    const data = await res.json();
    saveOfflineExam(data);
    alert(`"${title}" saved for offline use.`);
    loadExams(); // refresh grid
  } catch (e) {
    alert("Download failed. Check your connection.");
  }
}

// ── Start Exam ─────────────────────────────────────────────────────────────
async function startExam(examId) {
  // Try to get full exam data (with questions) — prefer offline cache
  const offlineExams = getOfflineExams();
  const cached = offlineExams.find(e => e.id === examId);

  if (isOffline) {
    if (!cached) { alert("This exam is not downloaded. Connect to the internet to download it."); return; }
    currentExam = cached;
    currentSession = { session_id: `offline-${Date.now()}`, exam_id: examId, duration_minutes: cached.duration_minutes, offline: true };
  } else {
    // Start server session first
    try {
      const sessionRes = await fetch(`${API}/api/v1/cbt/sessions/${examId}/start`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (sessionRes.status === 401) { window.location.href = "auth.html"; return; }
      if (!sessionRes.ok) { const d = await sessionRes.json(); alert(d.detail || "Could not start exam."); return; }
      const sessionData = await sessionRes.json();
      currentSession = { ...sessionData, offline: false };

      // Use cached questions if available to reduce loading time
      if (cached && cached.questions) {
        currentExam = { ...cached, ...sessionData };
      } else {
        // Download exam data for this session
        const examRes = await fetch(`${API}/api/v1/cbt/exams/${examId}/download`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        currentExam = await examRes.json();
        saveOfflineExam(currentExam); // cache for future offline use
      }
    } catch (e) {
      if (cached) {
        // fallback to offline
        currentExam = cached;
        currentSession = { session_id: `offline-${Date.now()}`, exam_id: examId, duration_minutes: cached.duration_minutes, offline: true };
      } else {
        alert("Network error. Download this exam for offline use first.");
        return;
      }
    }
  }

  answers = {};
  currentQ = 0;
  beginExam();
}

function beginExam() {
  const questions = currentExam.questions;
  const dur = currentSession.duration_minutes || currentExam.duration_minutes;

  // Build question nav
  document.getElementById("exam-title-sm").textContent = currentExam.title;
  document.getElementById("exam-title-top").textContent = currentExam.title;

  const nav = document.getElementById("q-nav");
  nav.innerHTML = questions.map((_, i) => `
    <button class="q-dot" id="qdot-${i}" onclick="goToQuestion(${i})">${i + 1}</button>
  `).join("");

  // Start timer
  secondsLeft = dur * 60;
  updateTimer();
  clearInterval(timerInterval);
  timerInterval = setInterval(() => {
    secondsLeft--;
    updateTimer();
    if (secondsLeft <= 0) { clearInterval(timerInterval); submitExam(true); }
  }, 1000);

  showQuestion(0);
  showScreen("screen-exam");
}

// ── Timer ──────────────────────────────────────────────────────────────────
function updateTimer() {
  const m = Math.floor(secondsLeft / 60);
  const s = secondsLeft % 60;
  const timerEl = document.getElementById("exam-timer");
  timerEl.textContent = `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  timerEl.className = "exam-timer";
  if (secondsLeft <= 300) timerEl.classList.add("warning");
  if (secondsLeft <= 60) { timerEl.classList.remove("warning"); timerEl.classList.add("danger"); }
}

// ── Show Question ──────────────────────────────────────────────────────────
function showQuestion(idx) {
  const questions = currentExam.questions;
  const q = questions[idx];
  currentQ = idx;

  document.getElementById("q-number").textContent = `Question ${idx + 1}`;
  document.getElementById("q-text").textContent = q.question_text;
  document.getElementById("q-counter").textContent = `Q ${idx + 1} / ${questions.length}`;

  // Image
  const imgWrap = document.getElementById("q-image-wrap");
  if (q.image_url) {
    document.getElementById("q-image").src = q.image_url;
    imgWrap.style.display = "block";
  } else {
    imgWrap.style.display = "none";
  }

  // Options
  const optList = document.getElementById("options-list");
  const opts = [
    { key: "A", text: q.option_a },
    { key: "B", text: q.option_b },
    { key: "C", text: q.option_c },
    { key: "D", text: q.option_d },
  ];
  optList.innerHTML = opts.map(o => `
    <button class="option-btn ${answers[q.id] === o.key ? "selected" : ""}" onclick="selectAnswer('${q.id}','${o.key}',this)">
      <span class="option-label">${o.key}</span>
      <span>${escHtml(o.text)}</span>
    </button>
  `).join("");

  // Nav buttons
  document.getElementById("btn-prev").disabled = idx === 0;
  document.getElementById("btn-next").disabled = idx === questions.length - 1;

  // Update nav dots
  document.querySelectorAll(".q-dot").forEach((dot, i) => {
    dot.classList.toggle("current", i === idx);
    dot.classList.toggle("answered", !!answers[questions[i].id] && i !== idx);
  });

  updateProgress();
}

function selectAnswer(qId, option, btn) {
  answers[qId] = option;
  // Update option highlights
  document.querySelectorAll(".option-btn").forEach(b => b.classList.remove("selected"));
  btn.classList.add("selected");
  // Update nav dot
  const idx = currentExam.questions.findIndex(q => q.id === qId);
  const dot = document.getElementById(`qdot-${idx}`);
  if (dot) { dot.classList.add("answered"); dot.classList.remove("current"); }
  updateProgress();
}

function updateProgress() {
  const total = currentExam.questions.length;
  const answered = Object.keys(answers).length;
  document.getElementById("progress-text").textContent = `${answered} / ${total} answered`;
}

function goToQuestion(idx) { showQuestion(idx); }
function prevQuestion() { if (currentQ > 0) showQuestion(currentQ - 1); }
function nextQuestion() { if (currentQ < currentExam.questions.length - 1) showQuestion(currentQ + 1); }

// ── Submit ─────────────────────────────────────────────────────────────────
function confirmSubmit() {
  const total = currentExam.questions.length;
  const answered = Object.keys(answers).length;
  document.getElementById("modal-answered").textContent = answered;
  document.getElementById("modal-total").textContent = total;
  document.getElementById("modal-confirm").style.display = "flex";
}

function closeModal() {
  document.getElementById("modal-confirm").style.display = "none";
}

async function submitExam(autoSubmit = false) {
  closeModal();
  clearInterval(timerInterval);

  if (currentSession.offline) {
    // Score locally
    scoreLocally(autoSubmit);
    return;
  }

  try {
    const res = await fetch(`${API}/api/v1/cbt/sessions/submit`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      body: JSON.stringify({
        session_id: currentSession.session_id,
        answers,
        is_auto_submit: autoSubmit,
      }),
    });
    if (!res.ok) throw new Error("submit failed");
    const result = await res.json();
    lastResult = result;
    // Also fetch review data
    try {
      const rv = await fetch(`${API}/api/v1/cbt/sessions/${currentSession.session_id}/review`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (rv.ok) lastReviewData = await rv.json();
    } catch {}
    showResults(result);
  } catch {
    // Fallback: score locally if server unreachable
    scoreLocally(autoSubmit);
  }
}

function scoreLocally(autoSubmit) {
  const questions = currentExam.questions;
  let correct = 0;
  let wrong = 0;
  const weakTopics = new Set();

  questions.forEach(q => {
    const chosen = answers[q.id];
    if (chosen && chosen.toUpperCase() === (q.correct_option || "").toUpperCase()) {
      correct++;
    } else {
      wrong++;
      if (q.topic) weakTopics.add(q.topic);
    }
  });

  const total = correct + wrong;
  const percentage = total > 0 ? parseFloat(((correct / total) * 100).toFixed(1)) : 0;

  lastResult = { score: correct, percentage, total_correct: correct, total_wrong: wrong, weak_topics: [...weakTopics] };

  // Build review data locally (includes correct answers since we have them offline)
  lastReviewData = {
    percentage,
    questions: questions.map(q => ({
      id: q.id,
      question_text: q.question_text,
      option_a: q.option_a,
      option_b: q.option_b,
      option_c: q.option_c,
      option_d: q.option_d,
      correct_option: q.correct_option,
      explanation: q.explanation,
      topic: q.topic,
      student_answer: answers[q.id],
      is_correct: (answers[q.id] || "").toUpperCase() === (q.correct_option || "").toUpperCase(),
    })),
  };

  showResults(lastResult);
}

// ── Results ────────────────────────────────────────────────────────────────
function showResults(result) {
  const pct = result.percentage || 0;
  document.getElementById("score-pct").textContent = pct + "%";
  document.getElementById("stat-correct").textContent = result.total_correct;
  document.getElementById("stat-wrong").textContent = result.total_wrong;

  const circle = document.getElementById("score-circle");
  circle.className = "score-circle " + (pct >= 50 ? "pass" : "fail");

  document.getElementById("results-icon").textContent = pct >= 70 ? "🎉" : pct >= 50 ? "👍" : "📚";
  document.getElementById("results-title").textContent = pct >= 70 ? "Excellent work!" : pct >= 50 ? "Good effort!" : "Keep practising!";

  const weakBlock = document.getElementById("weak-topics-block");
  const weakList = document.getElementById("weak-topics-list");
  if (result.weak_topics && result.weak_topics.length > 0) {
    weakList.innerHTML = result.weak_topics.map(t => `<span class="weak-tag">${escHtml(t)}</span>`).join("");
    weakBlock.style.display = "block";
  } else {
    weakBlock.style.display = "none";
  }

  showScreen("screen-results");
}

function showReview() {
  if (!lastReviewData) { alert("Review data not available."); return; }
  const list = document.getElementById("review-list");
  list.innerHTML = lastReviewData.questions.map((q, i) => {
    const opts = [
      { key: "A", text: q.option_a },
      { key: "B", text: q.option_b },
      { key: "C", text: q.option_c },
      { key: "D", text: q.option_d },
    ];
    return `
      <div class="review-item ${q.is_correct ? "correct-item" : "wrong-item"}">
        <div class="review-q-num">Question ${i + 1} ${q.is_correct ? "✓" : "✗"}</div>
        <div class="review-q-text">${escHtml(q.question_text)}</div>
        <div class="review-options">
          ${opts.map(o => {
            let cls = "";
            if (o.key === q.correct_option) cls = "opt-correct";
            else if (o.key === q.student_answer && !q.is_correct) cls = "opt-wrong";
            return `<div class="review-option ${cls}">${o.key}. ${escHtml(o.text)}${o.key === q.correct_option ? " ✓" : ""}</div>`;
          }).join("")}
        </div>
        ${q.explanation ? `<div class="review-explanation"><span class="explain-label">Explanation:</span>${escHtml(q.explanation)}</div>` : ""}
      </div>
    `;
  }).join("");
  showScreen("screen-review");
}

function backToList() {
  showScreen("screen-list");
  currentExam = null;
  currentSession = null;
  answers = {};
  clearInterval(timerInterval);
  loadExams();
}

// ── Auth ───────────────────────────────────────────────────────────────────
function logout() {
  localStorage.removeItem("sia_token");
  localStorage.removeItem("sia_name");
  window.location.href = "auth.html";
}

// ── Helpers ────────────────────────────────────────────────────────────────
function firstName(name) {
  if (!name) return "Student";
  if (name.includes("@")) return name.split("@")[0];
  return name.split(" ")[0];
}

function escHtml(str) {
  return (str || "").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
}
