const API = "https://scholaxia.onrender.com";

// ── State ──────────────────────────────────────────────
const token = localStorage.getItem("sia_token") || "";
const rawName = localStorage.getItem("sia_name") || "";
let recognition = null;
let isListening = false;
let stepCounter = 0;

// Extract first name — never show email
function firstName(name) {
  if (!name) return "Student";
  // If it looks like an email, use the part before @
  if (name.includes("@")) return name.split("@")[0].split(".")[0];
  return name.split(" ")[0];
}

const studentName = firstName(rawName);

// ── Init ───────────────────────────────────────────────
window.onload = () => {
  if (!token) { window.location.href = "index.html"; return; }
  document.getElementById("student-name-top").textContent = studentName;
  initRecognition();
  setTimeout(() => greetStudent(studentName), 600);
};

// ── Voice Recognition ──────────────────────────────────
function initRecognition() {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) {
    document.getElementById("mic-label").textContent = "Not supported";
    return;
  }
  recognition = new SR();
  recognition.continuous = false;
  recognition.interimResults = true;
  recognition.lang = "en-NG";

  recognition.onresult = (e) => {
    const transcript = Array.from(e.results).map(r => r[0].transcript).join("");
    document.getElementById("transcript-preview").textContent = transcript;
  };

  recognition.onend = () => {
    const transcript = document.getElementById("transcript-preview").textContent.trim();
    stopListeningUI();
    if (transcript) askSia(transcript);
  };

  recognition.onerror = (e) => {
    console.log("Speech error:", e.error);
    stopListeningUI();
  };
}

function startListening() {
  if (!recognition || isListening) return;
  // Stop any ongoing speech first
  if (window.speechSynthesis) window.speechSynthesis.cancel();
  const audio = document.getElementById("classroom-audio");
  if (audio) { audio.pause(); audio.src = ""; }
  hideSpeakingBar();

  isListening = true;
  document.getElementById("mic-btn").classList.add("listening");
  document.getElementById("mic-label").textContent = "Listening...";
  document.getElementById("listening-overlay").style.display = "flex";
  document.getElementById("transcript-preview").textContent = "";
  try { recognition.start(); } catch(e) { stopListeningUI(); }
}

function stopListening() {
  if (!recognition || !isListening) return;
  try { recognition.stop(); } catch(e) { stopListeningUI(); }
}

function stopListeningUI() {
  isListening = false;
  document.getElementById("mic-btn").classList.remove("listening");
  document.getElementById("mic-label").textContent = "Hold to speak";
  document.getElementById("listening-overlay").style.display = "none";
}

// ── Ask Sia ────────────────────────────────────────────
async function askSia(question) {
  const subject = document.getElementById("classroom-subject").value;
  writeToBoardRaw("Sia is thinking...");

  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 90000); // 90s timeout

    const res = await fetch(`${API}/api/v1/sia/ask`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ question, subject, language: "english" }),
      signal: controller.signal,
    });

    clearTimeout(timeout);

    if (res.status === 401) { window.location.href = "index.html"; return; }
    if (!res.ok) {
      removeThinking();
      speakDeep("I had trouble connecting. Please try again.");
      return;
    }

    const data = await res.json();
    const answer = data.sia || "I couldn't get a response. Please try again.";
    const board = data.board || [];

    removeThinking();

    if (board.length > 0) {
      clearBoardContent();
      writeToBoard(board);
    } else {
      // Even if no structured board, write the key sentence
      clearBoardContent();
      const firstLine = answer.split("\n").find(l => l.trim().length > 10) || "";
      if (firstLine) {
        const el = document.createElement("div");
        el.className = "chalk-item chalk-point";
        el.textContent = firstLine.replace(/\*\*/g, "").slice(0, 120);
        document.getElementById("board-writing").appendChild(el);
      }
    }

    speakDeep(answer);

  } catch (e) {
    removeThinking();
    if (e.name === "AbortError") {
      speakDeep("That took too long. The server might be waking up. Please try again.");
    } else {
      speakDeep("Connection issue. Please check your internet and try again.");
    }
  }
}

// ── Board Writing ──────────────────────────────────────
function clearBoardContent() {
  document.getElementById("board-writing").innerHTML = "";
  stepCounter = 0;
}

function clearBoard() {
  clearBoardContent();
  document.getElementById("board-writing").innerHTML = `
    <div class="board-welcome">
      <p class="welcome-text">Board cleared.</p>
      <p class="welcome-sub">Ask me anything to start.</p>
    </div>
  `;
}

function writeToBoard(items) {
  const writing = document.getElementById("board-writing");
  let delay = 0;
  items.forEach((item) => {
    setTimeout(() => {
      const el = document.createElement("div");
      el.className = `chalk-item chalk-${item.type}`;
      if (item.type === "step") {
        stepCounter++;
        el.setAttribute("data-num", stepCounter);
      }
      el.textContent = item.content;
      writing.appendChild(el);
      writing.scrollTop = writing.scrollHeight;
    }, delay);
    delay += 280;
  });
}

function writeToBoardRaw(content) {
  const writing = document.getElementById("board-writing");
  writing.innerHTML = `<div class="chalk-item chalk-diagram" id="thinking-indicator" style="opacity:0.5;font-style:italic">${content}</div>`;
}

function removeThinking() {
  const el = document.getElementById("thinking-indicator");
  if (el) el.remove();
}

// ── Deep Voice (Sia speaks) ────────────────────────────
function speakDeep(text) {
  showSpeakingBar(text);

  if (!window.speechSynthesis) { hideSpeakingBar(); return; }

  // Cancel any ongoing speech
  window.speechSynthesis.cancel();

  const utterance = new SpeechSynthesisUtterance(text);

  // Deep, authoritative teacher voice settings
  utterance.rate = 0.88;    // slightly slower — clear and deliberate
  utterance.pitch = 0.75;   // lower pitch = deeper voice
  utterance.volume = 1.0;

  // Wait for voices to load then pick the deepest male voice available
  const setVoice = () => {
    const voices = window.speechSynthesis.getVoices();
    // Priority: deep male voices
    const deepVoice =
      voices.find(v => v.name === "Google UK English Male") ||
      voices.find(v => v.name === "Microsoft David Desktop") ||
      voices.find(v => v.name.toLowerCase().includes("male")) ||
      voices.find(v => v.name.includes("Daniel")) ||
      voices.find(v => v.name.includes("Alex")) ||
      voices.find(v => v.lang === "en-GB") ||
      voices.find(v => v.lang.startsWith("en"));

    if (deepVoice) utterance.voice = deepVoice;
    utterance.onend = hideSpeakingBar;
    utterance.onerror = hideSpeakingBar;
    window.speechSynthesis.speak(utterance);
  };

  if (window.speechSynthesis.getVoices().length > 0) {
    setVoice();
  } else {
    window.speechSynthesis.onvoiceschanged = setVoice;
  }
}

function showSpeakingBar(text) {
  document.getElementById("sia-speaking-bar").style.display = "flex";
  document.getElementById("sia-dot").classList.add("speaking");
  document.getElementById("sia-speaking-text").textContent =
    text.slice(0, 90) + (text.length > 90 ? "..." : "");
}

function hideSpeakingBar() {
  document.getElementById("sia-speaking-bar").style.display = "none";
  document.getElementById("sia-dot").classList.remove("speaking");
}

// ── Greeting ───────────────────────────────────────────
function greetStudent(name) {
  document.getElementById("board-writing").innerHTML = `
    <div class="chalk-item chalk-heading">Welcome, ${name}!</div>
    <div class="chalk-item chalk-point">Hold the mic button and ask me anything</div>
    <div class="chalk-item chalk-point">I will explain, solve, and write on this board</div>
    <div class="chalk-item chalk-point">Select your subject below before asking</div>
    <hr class="chalk-divider" />
    <div class="chalk-item chalk-diagram">Ready when you are, ${name}.</div>
  `;

  speakDeep(`Good day ${name}. I am Sia, your personal teacher. Hold the microphone and ask me anything. I will explain it clearly and write the key points on the board. What subject are we studying today?`);
}
