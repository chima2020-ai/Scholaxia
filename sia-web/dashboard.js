const API = "https://scholaxia.onrender.com";
const token = localStorage.getItem("sia_token") || "";
const userName = localStorage.getItem("sia_name") || "";

window.onload = () => {
  if (!token) { window.location.href = "auth.html"; return; }
  const name = firstName(userName);
  document.getElementById("dash-name").textContent = name;
  document.getElementById("dash-avatar").textContent = name[0].toUpperCase();
  loadKeys();
};

function firstName(name) {
  if (!name) return "Developer";
  if (name.includes("@")) return name.split("@")[0];
  return name.split(" ")[0];
}

function logout() {
  localStorage.clear();
  window.location.href = "auth.html";
}

function showSection(name) {
  ["keys","docs","usage"].forEach(s => {
    document.getElementById(`section-${s}`).style.display = s === name ? "block" : "none";
  });
  document.querySelectorAll(".dash-link").forEach(l => l.classList.remove("active"));
  event.currentTarget.classList.add("active");
  const titles = { keys: ["API Keys","Manage your Scholaxia API keys"], docs: ["API Documentation","Integrate Sia into your application"], usage: ["Usage Analytics","Monitor your API usage"] };
  document.getElementById("section-title").textContent = titles[name][0];
  document.getElementById("section-desc").textContent = titles[name][1];
  if (name === "usage") loadUsage();
}

// ── API Keys ───────────────────────────────────────────
async function loadKeys() {
  const list = document.getElementById("keys-list");
  try {
    const res = await fetch(`${API}/api/v1/developer/keys/`, { headers: { Authorization: `Bearer ${token}` } });
    if (res.status === 401) { window.location.href = "auth.html"; return; }
    const keys = await res.json();
    if (!keys.length) {
      list.innerHTML = `<div class="empty-state"><p>No API keys yet.</p><p>Generate your first key to start building.</p></div>`;
      return;
    }
    list.innerHTML = keys.map(k => `
      <div class="key-card" id="key-${k.id}">
        <div class="key-info">
          <div class="key-name">${escHtml(k.name)}</div>
          <div class="key-meta">
            <span class="key-prefix">${k.key_prefix}...</span>
            <span class="key-tier">${k.tier}</span>
            <span class="key-status">${k.is_active ? "● Active" : "○ Revoked"}</span>
            <span class="key-date">Created ${new Date(k.created_at).toLocaleDateString()}</span>
            <span class="key-date">${k.daily_limit.toLocaleString()} req/day</span>
          </div>
        </div>
        <div class="key-actions">
          ${k.is_active ? `<button class="btn-revoke" onclick="revokeKey('${k.id}')">Revoke</button>` : ""}
        </div>
      </div>
    `).join("");
  } catch(e) {
    list.innerHTML = `<div class="loading">Failed to load keys. Please refresh.</div>`;
  }
}

function showCreateKey() {
  document.getElementById("create-key-form").style.display = "block";
  document.getElementById("key-name").focus();
}

function hideCreateKey() {
  document.getElementById("create-key-form").style.display = "none";
}

async function createKey() {
  const name = document.getElementById("key-name").value.trim();
  const tier = document.getElementById("key-tier").value;
  if (!name) { alert("Please enter a key name."); return; }
  const btn = document.querySelector(".btn-create");
  btn.disabled = true; btn.textContent = "Generating...";
  try {
    const res = await fetch(`${API}/api/v1/developer/keys/`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      body: JSON.stringify({ name, tier }),
    });
    const data = await res.json();
    if (!res.ok) { alert(data.detail || "Failed to create key."); return; }
    hideCreateKey();
    document.getElementById("key-name").value = "";
    // Show the key once
    document.getElementById("new-key-value").textContent = data.key;
    document.getElementById("new-key-display").style.display = "block";
    loadKeys();
  } catch(e) {
    alert("Network error. Please try again.");
  } finally { btn.disabled = false; btn.textContent = "Generate key"; }
}

async function revokeKey(id) {
  if (!confirm("Revoke this API key? This cannot be undone.")) return;
  try {
    await fetch(`${API}/api/v1/developer/keys/${id}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    });
    loadKeys();
  } catch(e) { alert("Failed to revoke key."); }
}

function copyKey() {
  const key = document.getElementById("new-key-value").textContent;
  navigator.clipboard.writeText(key).then(() => {
    const btn = document.querySelector(".copy-btn");
    btn.textContent = "Copied!";
    setTimeout(() => btn.textContent = "Copy", 2000);
  });
}

// ── Usage ──────────────────────────────────────────────
async function loadUsage() {
  const content = document.getElementById("usage-content");
  try {
    const keysRes = await fetch(`${API}/api/v1/developer/keys/`, { headers: { Authorization: `Bearer ${token}` } });
    const keys = await keysRes.json();
    if (!keys.length) {
      content.innerHTML = `<div class="empty-state"><p>No API keys yet. Generate a key to see usage.</p></div>`;
      return;
    }
    // Load usage for first active key
    const activeKey = keys.find(k => k.is_active);
    if (!activeKey) { content.innerHTML = `<div class="empty-state"><p>No active keys.</p></div>`; return; }
    const usageRes = await fetch(`${API}/api/v1/developer/keys/${activeKey.id}/usage`, { headers: { Authorization: `Bearer ${token}` } });
    const usage = await usageRes.json();
    const pct = Math.round((usage.total_requests / (activeKey.daily_limit * 30)) * 100);
    content.innerHTML = `
      <div class="usage-cards">
        <div class="usage-card">
          <div class="label">Total Requests</div>
          <div class="value">${usage.total_requests.toLocaleString()}</div>
          <div class="sub">All time</div>
        </div>
        <div class="usage-card">
          <div class="label">Tokens Used</div>
          <div class="value">${(usage.total_tokens_used || 0).toLocaleString()}</div>
          <div class="sub">All time</div>
        </div>
        <div class="usage-card">
          <div class="label">Avg Latency</div>
          <div class="value">${usage.avg_latency_ms || 0}<span style="font-size:16px;font-weight:400">ms</span></div>
          <div class="sub">Per request</div>
        </div>
        <div class="usage-card">
          <div class="label">Daily Limit</div>
          <div class="value">${activeKey.daily_limit.toLocaleString()}</div>
          <div class="sub">${activeKey.tier} tier</div>
          <div class="usage-bar"><div class="usage-bar-fill" style="width:${Math.min(pct,100)}%"></div></div>
        </div>
      </div>
      <h3 style="margin-bottom:16px;font-size:16px">Recent Requests</h3>
      <div class="keys-list">
        ${(usage.recent_logs || []).slice(0,10).map(l => `
          <div class="key-card">
            <div class="key-info">
              <div class="key-name" style="font-size:13px;font-family:monospace">${l.endpoint}</div>
              <div class="key-meta">
                <span class="key-tier">${l.status} ${l.status === 200 ? "✓" : "✗"}</span>
                <span class="key-date">${l.tokens} tokens</span>
                <span class="key-date">${l.latency_ms}ms</span>
                <span class="key-date">${new Date(l.at).toLocaleString()}</span>
              </div>
            </div>
          </div>
        `).join("") || "<div class='loading'>No requests yet.</div>"}
      </div>
    `;
  } catch(e) {
    content.innerHTML = `<div class="loading">Failed to load usage data.</div>`;
  }
}

function escHtml(str) {
  return (str||"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
}
