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
    if (transcript && !isFetching) askSia(transcript);
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
let isFetching = false; // prevent double calls

async function askSia(question) {
  if (isFetching) return; // ignore if already waiting for response
  isFetching = true;

  const subject = document.getElementById("classroom-subject").value;
  writeToBoardRaw("Sia is thinking...");

  try {
    const res = await fetch(`${API}/api/v1/sia/ask`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ question, subject, language: "english" }),
    });

    if (res.status === 401) {
      // Token expired — don't redirect, just tell the student
      removeThinking();
      isFetching = false;
      speakDeep("Your session expired. Please go back and log in again.");
      setTimeout(() => { window.location.href = "index.html"; }, 4000);
      return;
    }
    if (!res.ok) {
      removeThinking();
      speakDeep("I had trouble getting a response. Please ask again.");
      return;
    }

    const data = await res.json();
    const answer = data.sia || "I could not get a response. Please try again.";
    const board = data.board || [];

    removeThinking();

    if (board.length > 0) {
      clearBoardContent();
      writeToBoard(board);
    } else {
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
    speakDeep("Please ask your question again.");
  } finally {
    isFetching = false; // always reset so next question works
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

      // For formulas — render on a mini canvas
      if (item.type === "formula") {
        el.innerHTML = renderFormula(item.content);
      } else if (item.type === "diagram_hint") {
        el.innerHTML = renderDiagram(item.content);
      } else {
        el.textContent = item.content;
      }

      writing.appendChild(el);
      writing.scrollTop = writing.scrollHeight;
    }, delay);
    delay += 280;
  });
}

function renderFormula(text) {
  // Render formula with highlighted math symbols
  const formatted = text
    .replace(/\^(\d+)/g, '<sup>$1</sup>')
    .replace(/sqrt\(([^)]+)\)/g, '√($1)')
    .replace(/([=+\-×÷])/g, ' <span class="math-op">$1</span> ')
    .replace(/\*\*/g, '')
    .replace(/\*/g, '×');
  return `<span class="formula-text">${formatted}</span>`;
}

function renderDiagram(text) {
  // Draw a simple ASCII-style diagram on canvas
  const canvas = document.createElement("canvas");
  canvas.width = 320;
  canvas.height = 120;
  canvas.style.cssText = "border:1px solid rgba(255,255,255,0.1);border-radius:6px;margin-top:4px;";
  const ctx = canvas.getContext("2d");

  // Dark background
  ctx.fillStyle = "#1a3a2a";
  ctx.fillRect(0, 0, 320, 120);

  // Draw based on content keywords
  const lower = text.toLowerCase();
  ctx.strokeStyle = "#f0ede0";
  ctx.lineWidth = 1.5;
  ctx.font = "12px 'Courier New'";
  ctx.fillStyle = "#f0ede0";

  if (lower.includes("force") || lower.includes("motion") || lower.includes("arrow")) {
    // Draw force/motion arrow diagram
    ctx.beginPath();
    ctx.moveTo(40, 60); ctx.lineTo(200, 60);
    ctx.stroke();
    // Arrowhead
    ctx.beginPath();
    ctx.moveTo(200, 60); ctx.lineTo(185, 50); ctx.lineTo(185, 70); ctx.closePath();
    ctx.fillStyle = "#7ec8e3"; ctx.fill();
    ctx.fillStyle = "#f5e642";
    ctx.fillText("F →", 100, 50);
    ctx.fillStyle = "#f0ede0";
    ctx.fillText("Object", 80, 90);

  } else if (lower.includes("circuit") || lower.includes("electric")) {
    // Simple circuit
    ctx.strokeRect(60, 30, 200, 60);
    ctx.fillStyle = "#f5e642";
    ctx.fillText("+ Battery -", 100, 20);
    ctx.fillStyle = "#7ec8e3";
    ctx.fillText("R (Resistor)", 100, 75);

  } else if (lower.includes("wave") || lower.includes("frequency")) {
    // Wave diagram
    ctx.beginPath();
    ctx.moveTo(20, 60);
    for (let x = 20; x < 300; x++) {
      ctx.lineTo(x, 60 + 25 * Math.sin((x - 20) * 0.08));
    }
    ctx.strokeStyle = "#7ec8e3"; ctx.stroke();
    ctx.fillStyle = "#f5e642";
    ctx.fillText("wavelength →", 80, 110);

  } else if (lower.includes("triangle") || lower.includes("angle") || lower.includes("pythagoras")) {
    // Right triangle
    ctx.beginPath();
    ctx.moveTo(40, 100); ctx.lineTo(280, 100); ctx.lineTo(40, 20); ctx.closePath();
    ctx.strokeStyle = "#f0ede0"; ctx.stroke();
    ctx.fillStyle = "#f5e642";
    ctx.fillText("a", 150, 115);
    ctx.fillText("b", 25, 60);
    ctx.fillStyle = "#7ec8e3";
    ctx.fillText("c (hyp)", 155, 55);
    // Right angle mark
    ctx.strokeRect(40, 85, 15, 15);

  } else if (lower.includes("cell") || lower.includes("plant") || lower.includes("photosynthesis")) {
    // Simple cell/plant diagram
    ctx.beginPath();
    ctx.ellipse(160, 60, 100, 45, 0, 0, Math.PI * 2);
    ctx.strokeStyle = "#7dba7d"; ctx.stroke();
    ctx.beginPath();
    ctx.ellipse(160, 60, 30, 20, 0, 0, Math.PI * 2);
    ctx.strokeStyle = "#f5e642"; ctx.stroke();
    ctx.fillStyle = "#f5e642";
    ctx.fillText("nucleus", 135, 65);
    ctx.fillStyle = "#7dba7d";
    ctx.fillText("cell membrane", 95, 115);

  } else {
    // Generic: write the text as chalk on board
    ctx.fillStyle = "#f0ede0";
    ctx.font = "13px 'Courier New'";
    const words = text.split(" ");
    let line = ""; let y = 30;
    words.forEach(word => {
      const test = line + word + " ";
      if (ctx.measureText(test).width > 290 && line) {
        ctx.fillText(line, 15, y); y += 22; line = word + " ";
      } else { line = test; }
    });
    if (line) ctx.fillText(line, 15, y);
  }

  return canvas.outerHTML;
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
