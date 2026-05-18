const API = "https://scholaxia.onrender.com";

// ── State ──────────────────────────────────────────────
let token = localStorage.getItem("sia_token") || "";
let userName = localStorage.getItem("sia_name") || "";
let chats = JSON.parse(localStorage.getItem("sia_chats") || "[]");
let currentChatId = null;

// ── Init ───────────────────────────────────────────────
window.onload = () => {
  if (token && userName) {
    showApp();
  } else {
    showAuthScreen();
  }
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
  btn.disabled = true;
  btn.textContent = "Logging in...";

  try {
    const res = await fetch(`${API}/api/v1/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    const data = await res.json();
    if (!res.ok) { errEl.textContent = data.detail || "Login failed."; return; }

    token = data.access_token;
    // Get name from profile
    const profile = await fetch(`${API}/api/v1/students/me`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    if (profile.ok) {
      const p = await profile.json();
      userName = p.full_name || email;
    } else {
      userName = email;
    }

    localStorage.setItem("sia_token", token);
    localStorage.setItem("sia_name", userName);
    showApp();
  } catch (e) {
    errEl.textContent = "Network error. Please try again.";
  } finally {
    btn.disabled = false;
    btn.textContent = "Log in";
  }
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
  btn.disabled = true;
  btn.textContent = "Creating account...";

  try {
    const res = await fetch(`${API}/api/v1/auth/student/signup`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password, full_name: name }),
    });
    const data = await res.json();
    if (!res.ok) { errEl.textContent = data.detail || "Signup failed."; return; }

    token = data.access_token;
    userName = name;
    localStorage.setItem("sia_token", token);
    localStorage.setItem("sia_name", userName);
    showApp();
  } catch (e) {
    errEl.textContent = "Network error. Please try again.";
  } finally {
    btn.disabled = false;
    btn.textContent = "Create account";
  }
}

function logout() {
  token = "";
  userName = "";
  localStorage.removeItem("sia_token");
  localStorage.removeItem("sia_name");
  showAuthScreen();
}

// ── Chat ───────────────────────────────────────────────
function newChat() {
  currentChatId = Date.now().toString();
  chats.unshift({ id: currentChatId, title: "New chat", messages: [] });
  saveChats();
  renderHistory();
  clearMessages();
}

function loadChat(id) {
  currentChatId = id;
  const chat = chats.find(c => c.id === id);
  if (!chat) return;
  clearMessages();
  chat.messages.forEach(m => appendMessage(m.role, m.content, false));
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
    <div class="history-item ${c.id === currentChatId ? 'active' : ''}" onclick="loadChat('${c.id}')">
      ${escHtml(c.title)}
    </div>
  `).join("");
}

function saveChats() {
  localStorage.setItem("sia_chats", JSON.stringify(chats.slice(0, 30)));
}

// ── Send Message ───────────────────────────────────────
async function sendMessage() {
  const input = document.getElementById("chat-input");
  const text = input.value.trim();
  if (!text) return;

  const subject = document.getElementById("subject-input").value.trim() || "General";
  const mode = document.getElementById("sia-mode").value;
  const language = document.getElementById("sia-language").value;

  input.value = "";
  input.style.height = "auto";

  // Create chat if none
  if (!currentChatId) {
    currentChatId = Date.now().toString();
    chats.unshift({ id: currentChatId, title: text.slice(0, 40), messages: [] });
    saveChats();
    renderHistory();
  }

  showMessages();
  appendMessage("user", text);
  saveToChat("user", text);

  // Update chat title from first message
  const chat = chats.find(c => c.id === currentChatId);
  if (chat && chat.title === "New chat") {
    chat.title = text.slice(0, 40);
    saveChats();
    renderHistory();
  }

  // Show typing
  const typingId = showTyping();
  document.getElementById("send-btn").disabled = true;

  try {
    const body = buildRequestBody(mode, text, subject, language);
    const res = await fetch(`${API}/api/v1/sia/${mode}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(body),
    });

    removeTyping(typingId);

    if (res.status === 401) {
      logout();
      return;
    }

    const data = await res.json();
    const answer = data.sia || data.result || data.answer || "Sorry, I couldn't get a response.";
    appendMessage("sia", answer);
    saveToChat("sia", answer);
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

function saveToChat(role, content) {
  const chat = chats.find(c => c.id === currentChatId);
  if (chat) {
    chat.messages.push({ role, content });
    saveChats();
  }
}

// ── DOM Helpers ────────────────────────────────────────
function appendMessage(role, content, scroll = true) {
  const el = document.getElementById("messages");
  const div = document.createElement("div");
  div.className = `message ${role}`;
  div.innerHTML = `
    <div class="msg-avatar">${role === "sia" ? "S" : firstName(userName)[0].toUpperCase()}</div>
    <div class="msg-content">${formatContent(content)}</div>
  `;
  el.appendChild(div);
  if (scroll) el.scrollTop = el.scrollHeight;
}

function showTyping() {
  const el = document.getElementById("messages");
  const id = "typing-" + Date.now();
  const div = document.createElement("div");
  div.className = "message sia";
  div.id = id;
  div.innerHTML = `
    <div class="msg-avatar">S</div>
    <div class="msg-content">
      <div class="typing-indicator">
        <span></span><span></span><span></span>
      </div>
    </div>
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
  // Convert newlines to paragraphs, bold **text**, numbered lists
  return text
    .split("\n\n")
    .map(para => {
      const lines = para.split("\n").map(line => {
        line = line.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
        line = line.replace(/\*(.*?)\*/g, "<em>$1</em>");
        return line;
      });
      return `<p>${lines.join("<br/>")}</p>`;
    })
    .join("");
}

function escHtml(str) {
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function firstName(name) {
  return (name || "Student").split(" ")[0];
}

function handleKey(e) {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
}

function autoResize(el) {
  el.style.height = "auto";
  el.style.height = Math.min(el.scrollHeight, 200) + "px";
}

function updateMode() {
  const mode = document.getElementById("sia-mode").value;
  const placeholders = {
    ask: "Ask Sia anything...",
    explain: "Enter a topic to explain (e.g. Photosynthesis)",
    solve: "Enter a problem to solve (e.g. Solve: 2x + 5 = 15)",
    evaluate: "Enter your answer for Sia to evaluate",
    "generate-questions": "Enter a topic for practice questions",
    feedback: "Press send to get your performance feedback",
  };
  document.getElementById("chat-input").placeholder = placeholders[mode] || "Message Sia...";
}
