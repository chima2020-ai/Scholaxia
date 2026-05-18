const API = "https://scholaxia.onrender.com";

// ── State ──────────────────────────────────────────────
const token = localStorage.getItem("sia_token") || "";
const userName = localStorage.getItem("sia_name") || "";
let recognition = null;
let isListening = false;
let stepCounter = 0;

// ── Init ───────────────────────────────────────────────
window.onload = () => {
  if (!token) { window.location.href = "index.html"; return; }
  const name = firstName(userName);
  document.getElementById("student-name-top").textContent = name;
  document.getElementById("class-subject").textContent = "Sia Classroom";
  initRecognition();
  // Greet student with voice on load
  setTimeout(() => greetStudent(name), 800);
};

function firstName(name) { return (name || "Student").split(" ")[0]; }

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

  recognition.onerror = () => stopListeningUI();
}

function startListening() {
  if (!recognition || isListening) return;
  isListening = true;
  document.getElementById("mic-btn").classList.add("listening");
  document.getElementById("mic-label").textContent = "Listening...";
  document.getElementById("listening-overlay").style.display = "flex";
  document.getElementById("transcript-preview").textContent = "";
  recognition.start();
}

function stopListening() {
  if (!recognition || !isListening) return;
  recognition.stop();
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

  // Show thinking on board
  writeToBoardRaw("thinking", "Sia is thinking...");

  try {
    const res = await fetch(`${API}/api/v1/sia/ask`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        question,
        subject,
        language: "english",
      }),
    });

    if (res.status === 401) { window.location.href = "index.html"; return; }

    const data = await res.json();
    const answer = data.sia || "Sorry, I couldn't get a response.";
    const board = data.board || [];

    // Remove thinking indicator
    removeThinking();

    // Write board content (educational writing)
    if (board.length > 0) {
      clearBoardContent();
      writeToBoard(board);
    }

    // Sia speaks the answer
    await speakAnswer(answer);

  } catch (e) {
    removeThinking();
    speakFallback("Sorry, something went wrong. Please try again.");
  }
}

// ── Board Writing ──────────────────────────────────────
function clearBoardContent() {
  const writing = document.getElementById("board-writing");
  writing.innerHTML = "";
  stepCounter = 0;
}

function clearBoard() {
  clearBoardContent();
  document.getElementById("board-writing").innerHTML = `
    <div class="board-welcome">
      <p class="welcome-text">Board cleared.</p>
      <p class="welcome-sub">Ask me anything to start teaching.</p>
    </div>
  `;
}

function writeToBoard(items) {
  const writing = document.getElementById("board-writing");
  let delay = 0;

  items.forEach((item, i) => {
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
    delay += 300; // stagger each item appearing
  });
}

function writeToBoardRaw(type, content) {
  const writing = document.getElementById("board-writing");
  const el = document.createElement("div");
  el.className = `chalk-item chalk-${type}`;
  el.id = "thinking-indicator";
  el.textContent = content;
  el.style.opacity = "0.5";
  el.style.fontStyle = "italic";
  writing.innerHTML = "";
  writing.appendChild(el);
}

function removeThinking() {
  const el = document.getElementById("thinking-indicator");
  if (el) el.remove();
}

// ── Sia Speaks ─────────────────────────────────────────
async function speakAnswer(text) {
  showSpeakingBar(text);

  // Try ElevenLabs TTS via backend
  try {
    const res = await fetch(`${API}/api/v1/sia/speak`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ text: text.slice(0, 1500), language: "english" }),
    });

    if (res.ok) {
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const audio = document.getElementById("classroom-audio");
      audio.src = url;
      audio.onended = hideSpeakingBar;
      audio.play();
      return;
    }
  } catch (e) {
    // Fall through to browser TTS
  }

  // Fallback: browser built-in TTS
  speakFallback(text);
}

function speakFallback(text) {
  if (!window.speechSynthesis) { hideSpeakingBar(); return; }
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.rate = 0.95;
  utterance.pitch = 1.0;
  utterance.volume = 1.0;
  // Try to find a good voice
  const voices = speechSynthesis.getVoices();
  const preferred = voices.find(v =>
    v.name.includes("Google") || v.name.includes("Natural") || v.lang.startsWith("en")
  );
  if (preferred) utterance.voice = preferred;
  utterance.onend = hideSpeakingBar;
  speechSynthesis.speak(utterance);
}

function showSpeakingBar(text) {
  const bar = document.getElementById("sia-speaking-bar");
  const dot = document.getElementById("sia-dot");
  bar.style.display = "flex";
  dot.classList.add("speaking");
  // Show first 60 chars of what Sia is saying
  document.getElementById("sia-speaking-text").textContent =
    `"${text.slice(0, 80)}${text.length > 80 ? "..." : ""}"`;
}

function hideSpeakingBar() {
  document.getElementById("sia-speaking-bar").style.display = "none";
  document.getElementById("sia-dot").classList.remove("speaking");
}

// ── Greeting ───────────────────────────────────────────
async function greetStudent(name) {
  const greeting = `Good day ${name}! I'm Sia, your personal teacher. I'm here to help you understand any topic deeply. Just hold the microphone button and ask me anything — a question, a topic you want to learn, or a problem you want me to solve. What are we studying today?`;

  // Write welcome on board
  const writing = document.getElementById("board-writing");
  writing.innerHTML = `
    <div class="chalk-item chalk-heading">Welcome, ${name}!</div>
    <div class="chalk-item chalk-point">Hold the mic and ask me anything</div>
    <div class="chalk-item chalk-point">I'll explain, solve, and teach on this board</div>
    <div class="chalk-item chalk-point">I speak — you listen and learn</div>
    <hr class="chalk-divider" />
    <div class="chalk-item chalk-diagram">Select your subject below, then press the mic</div>
  `;

  await speakAnswer(greeting);
}
