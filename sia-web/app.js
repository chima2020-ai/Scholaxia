const API = "https://scholaxia.onrender.com";

// ── State ──────────────────────────────────────────────
let token = localStorage.getItem("sia_token") || "";
let userName = localStorage.getItem("sia_name") || "";
let chats = JSON.parse(localStorage.getItem("sia_chats") || "[]");
let currentChatId = null;
let selectedImage = null;
let isRecording = false;
let recognition = null;
let isSpeaking = false;

// ── Init ───────────────────────────────────────────────
window.onload = () => {
  if (token && userName) showApp();
  else showAuthScreen();
  initVoiceRecognition();
};

// ── Auth ───────────────────────────────────────────────
function showAuthScreen() {
  document.getElementById("auth-screen").style.display = "flex";
  document.getElementById("app").style.display = "none";
}

function showApp() {
  document.getElementById("auth-screen").style.display = "none";
  document.getElementById("app").style.display = "flex";
  document.getElementById("user-name-display").textContent = firstName(userName);
  document.getElementById("user-avatar").textContent = firstName(userName)[0].toUpperCase();
  renderHistory();
}

function showSignup() {
  document.getElementById("login-form").style.display = "none";
  document.getElementById("signup-form").style.display = "block";
  clearErrors();
}

function showLogin() {
  document.getElementById("signup-form").style.display = "none";
  document.getElementById("login-form").style.display = "block";
  clearErrors();
}

function clearErrors() {
  document.getElementById("login-error").textContent = "";
  document.getElementById("signup-error").textContent = "";
}

async function login() {
  const email = document.getElementById("login-email").value.trim();
  const password = document.getElementById("login-password").value;
  const errEl = document.getElementById("login-error");
  errEl.textContent = "";
  if (!email || !password) { errEl.textContent = "Please fill in all fields."; return; }
  const btn = document.querySelector("#login-form .btn-primary");
  btn.disabled = true; btn.textContent = "Logging in...";
  try {
    const res = await fetch(`${API}/api/v1/auth/login`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
      signal: AbortSignal.timeout(30000),
    });
    const data = await res.json();
    if (!res.ok) { errEl.textContent = data.detail || "Login failed."; return; }
    token = data.access_token;
    const profile = await fetch(`${API}/api/v1/students/me`, { headers: { Authorization: `Bearer ${token}` } });
    userName = profile.ok ? (await profile.json()).full_name || email : email;
    localStorage.setItem("sia_token", token);
    localStorage.setItem("sia_name", userName);
    showApp();
  } catch (e) {
    errEl.textContent = e.name === "TimeoutError" ? "Server waking up — try again in 30s." : "Network error.";
  } finally { btn.disabled = false; btn.textContent = "Log in"; }
}

async function signup() {
  const name = document.getElementById("signup-name").value.trim();
  const email = document.getElementById("signup-email").value.trim();
  const password = document.getElementById("signup-password").value;
  const errEl = document.getElementById("signup-error");
  errEl.textContent = "";
  if (!name || !email || !password) { errEl.textContent = "Please fill in all fields."; return; }
  if (password.length < 8) { errEl.textContent = "Password must be at least 8 characters."; return; }
  const btn = document.querySelector("#signup-form .btn-primary");
  btn.disabled = true; btn.textContent = "Creating account...";
  try {
    const res = await fetch(`${API}/api/v1/auth/student/signup`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password, full_name: name }),
      signal: AbortSignal.timeout(30000),
    });
    const data = await res.json();
    if (!res.ok) { errEl.textContent = data.detail || "Signup failed."; return; }
    token = data.access_token; userName = name;
    localStorage.setItem("sia_token", token);
    localStorage.setItem("sia_name", userName);
    showApp();
  } catch (e) {
    errEl.textContent = e.name === "TimeoutError" ? "Server waking up — try again in 30s." : "Network error.";
  } finally { btn.disabled = false; btn.textContent = "Create account"; }
}

function logout() {
  token = ""; userName = "";
  localStorage.removeItem("sia_token");
  localStorage.removeItem("sia_name");
  showAuthScreen();
}

// ── Chat ───────────────────────────────────────────────
function newChat() {
  currentChatId = Date.now().toString();
  chats.unshift({ id: currentChatId, title: "New chat", messages: [] });
  saveChats(); renderHistory(); clearMessages(); clearBoard();
}

function loadChat(id) {
  currentChatId = id;
  const chat = chats.find(c => c.id === id);
  if (!chat) return;
  clearMessages(); clearBoard();
  chat.messages.forEach(m => appendMessage(m.role, m.content, m.imageUrl, false));
  if (chat.messages.length > 0) showMessages();
  renderHistory();
}

function clearMessages() {
  document.getElementById("messages").innerHTML = "";
  document.getElementById("messages").classList.remove("has-messages");
  document.getElementById("empty-state").style.display = "flex";
}

function showMessages() {
  document.getElementById("messages").classList.add("has-messages");
  document.getElementById("empty-state").style.display = "none";
}

function renderHistory() {
  const el = document.getElementById("chat-history");
  el.innerHTML = chats.slice(0, 20).map(c => `
    <div class="history-item ${c.id === currentChatId ? "active" : ""}" onclick="loadChat('${c.id}')">
      ${escHtml(c.title)}
    </div>
  `).join("");
}

function saveChats() {
  localStorage.setItem("sia_chats", JSON.stringify(chats.slice(0, 30)));
}

// ── Voice Input ────────────────────────────────────────
function initVoiceRecognition() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) return;
  recognition = new SpeechRecognition();
  recognition.continuous = false;
  recognition.interimResults = true;
  recognition.lang = "en-NG"; // Nigerian English

  recognition.onresult = (e) => {
    const transcript = Array.from(e.results).map(r => r[0].transcript).join("");
    document.getElementById("chat-input").value = transcript;
    document.getElementById("voice-text").textContent = transcript || "Listening...";
  };

  recognition.onend = () => {
    isRecording = false;
    document.getElementById("voice-btn").classList.remove("recording");
    document.getElementById("voice-status").style.display = "none";
    const text = document.getElementById("chat-input").value.trim();
    if (text) sendMessage();
  };

  recognition.onerror = () => {
    isRecording = false;
    document.getElementById("voice-btn").classList.remove("recording");
    document.getElementById("voice-status").style.display = "none";
  };
}

function toggleVoice() {
  if (!recognition) {
    alert("Voice input not supported in this browser. Try Chrome.");
    return;
  }
  if (isRecording) {
    recognition.stop();
  } else {
    isRecording = true;
    document.getElementById("voice-btn").classList.add("recording");
    document.getElementById("voice-status").style.display = "flex";
    document.getElementById("voice-text").textContent = "Listening... speak now";
    document.getElementById("chat-input").value = "";
    recognition.start();
  }
}

// ── Voice Output (Sia speaks) ──────────────────────────
async function speakResponse(text) {
  if (!token) return;
  try {
    const res = await fetch(`${API}/api/v1/sia/speak`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      body: JSON.stringify({ text: text.slice(0, 1000), language: "english" }),
    });
    if (!res.ok) return;
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const audio = document.getElementById("sia-audio");
    audio.src = url;
    audio.play();
  } catch (e) {
    // Voice output failed silently — text response still shown
  }
}

// ── Image Upload ───────────────────────────────────────
function handleImageSelect(event) {
  const file = event.target.files[0];
  if (!file) return;
  selectedImage = file;
  const reader = new FileReader();
  reader.onload = (e) => {
    document.getElementById("preview-img").src = e.target.result;
    document.getElementById("image-preview").style.display = "block";
  };
  reader.readAsDataURL(file);
}

function clearImage() {
  selectedImage = null;
  document.getElementById("image-preview").style.display = "none";
  document.getElementById("image-input").value = "";
}

// ── Board ──────────────────────────────────────────────
function updateBoard(boardItems) {
  if (!boardItems || boardItems.length === 0) return;
  const panel = document.getElementById("board-panel");
  const content = document.getElementById("board-content");
  panel.style.display = "block";
  content.innerHTML = boardItems.map(item => `
    <div class="board-item ${item.type}">${escHtml(item.content)}</div>
  `).join("");
}

function clearBoard() {
  document.getElementById("board-panel").style.display = "none";
  document.getElementById("board-content").innerHTML = "";
}

// ── Send Message ───────────────────────────────────────
async function sendMessage() {
  const input = document.getElementById("chat-input");
  const text = input.value.trim();
  const hasImage = !!selectedImage;

  if (!text && !hasImage) return;

  const subject = document.getElementById("subject-input").value || "General";
  const mode = document.getElementById("sia-mode").value;
  const language = document.getElementById("sia-language").value;

  input.value = "";
  input.style.height = "auto";

  if (!currentChatId) {
    currentChatId = Date.now().toString();
    const title = text ? text.slice(0, 40) : "Image question";
    chats.unshift({ id: currentChatId, title, messages: [] });
    saveChats(); renderHistory();
  }

  showMessages();

  // Show user message
  const imageUrl = hasImage ? URL.createObjectURL(selectedImage) : null;
  appendMessage("user", text || "📷 Image sent", imageUrl);
  saveToChat("user", text || "📷 Image sent", imageUrl);

  // Update chat title
  const chat = chats.find(c => c.id === currentChatId);
  if (chat && chat.title === "New chat") {
    chat.title = (text || "Image question").slice(0, 40);
    saveChats(); renderHistory();
  }

  const typingId = showTyping();
  document.getElementById("send-btn").disabled = true;

  try {
    let answer, board;

    if (hasImage) {
      // Image analysis
      const formData = new FormData();
      formData.append("image", selectedImage);
      formData.append("question", text || "Analyze this image and help me understand it");
      formData.append("subject", document.getElementById("subject-input").value || "General");
      formData.append("language", language);

      const res = await fetch(`${API}/api/v1/sia/analyze-image`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });

      if (res.status === 401) { logout(); return; }
      const data = await res.json();
      answer = data.sia || "Sorry, I couldn't analyze that image.";
      board = data.board;
      clearImage();
    } else {
      // Text message
      const body = buildRequestBody(mode, text, subject, language);

      // Include conversation history
      if (chat) {
        const history = chat.messages.slice(-6);
        if (history.length > 0) {
          body.conversation_history = history.map(m => ({
            role: m.role === "sia" ? "assistant" : "user",
            content: m.content
          }));
        }
      }

      const res = await fetch(`${API}/api/v1/sia/${mode}`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify(body),
      });

      if (res.status === 401) { logout(); return; }
      const data = await res.json();
      answer = data.sia || data.result || data.answer || "Sorry, I couldn't get a response.";
      board = data.board;
    }

    removeTyping(typingId);
    appendMessage("sia", answer);
    saveToChat("sia", answer);

    // Update board
    if (board && board.length > 0) updateBoard(board);

    // Sia speaks (auto-play voice response)
    speakResponse(answer);

  } catch (e) {
    removeTyping(typingId);
    appendMessage("sia", "Sorry, something went wrong. Please try again.");
  } finally {
    document.getElementById("send-btn").disabled = false;
  }
}

function buildRequestBody(mode, text, subject, language) {
  const base = { subject, language };
  switch (mode) {
    case "ask": return { ...base, question: text };
    case "explain": return { ...base, topic: text };
    case "solve": return { ...base, question: text };
    case "evaluate": return { ...base, question: text, student_answer: text };
    case "generate-questions": return { ...base, topic: text, number: 5, curriculum: "WAEC" };
    case "feedback": return { ...base };
    default: return { ...base, question: text };
  }
}

function sendSuggestion(question, subject) {
  document.getElementById("subject-input").value = subject;
  document.getElementById("chat-input").value = question;
  sendMessage();
}

function saveToChat(role, content, imageUrl = null) {
  const chat = chats.find(c => c.id === currentChatId);
  if (chat) { chat.messages.push({ role, content, imageUrl }); saveChats(); }
}

// ── DOM Helpers ────────────────────────────────────────
function appendMessage(role, content, imageUrl = null, scroll = true) {
  const el = document.getElementById("messages");
  const div = document.createElement("div");
  div.className = `message ${role}`;
  const imgHtml = imageUrl ? `<img src="${imageUrl}" class="msg-image" alt="Sent image" />` : "";
  div.innerHTML = `
    <div class="msg-avatar">${role === "sia" ? "S" : firstName(userName)[0].toUpperCase()}</div>
    <div class="msg-content">${imgHtml}${formatContent(content)}</div>
  `;
  el.appendChild(div);
  if (scroll) el.scrollTop = el.scrollHeight;
}

function showTyping() {
  const el = document.getElementById("messages");
  const id = "typing-" + Date.now();
  const div = document.createElement("div");
  div.className = "message sia"; div.id = id;
  div.innerHTML = `
    <div class="msg-avatar">S</div>
    <div class="msg-content"><div class="typing-indicator"><span></span><span></span><span></span></div></div>
  `;
  el.appendChild(div);
  el.scrollTop = el.scrollHeight;
  return id;
}

function removeTyping(id) {
  const el = document.getElementById(id);
  if (el) el.remove();
}

function formatContent(text) {
  return text.split("\n\n").map(para => {
    const lines = para.split("\n").map(line => {
      line = line.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
      line = line.replace(/\*(.*?)\*/g, "<em>$1</em>");
      return line;
    });
    return `<p>${lines.join("<br/>")}</p>`;
  }).join("");
}

function escHtml(str) {
  return (str || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function firstName(name) {
  if (!name) return "Student";
  // If it looks like an email, use the part before @
  if (name.includes("@")) return name.split("@")[0].split(".")[0];
  return name.split(" ")[0];
}

function handleKey(e) {
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); }
}

function autoResize(el) {
  el.style.height = "auto";
  el.style.height = Math.min(el.scrollHeight, 200) + "px";
}

function updateMode() {
  const placeholders = {
    ask: "Ask Sia anything...",
    explain: "Enter a topic to explain (e.g. Photosynthesis)",
    solve: "Enter a problem to solve",
    evaluate: "Enter your answer for Sia to evaluate",
    "generate-questions": "Enter a topic for practice questions",
    feedback: "Press send to get your performance feedback",
  };
  document.getElementById("chat-input").placeholder =
    placeholders[document.getElementById("sia-mode").value] || "Message Sia...";
}
