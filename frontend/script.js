/* ═══════════════════════════════════════════════════════════════════
   NOVA AI — ULTIMATE MASTER SAAS PLATFORM SCRIPT (v3.0)
   Full-stack integration for Chat, Code, Video, Voice, Music, Studio,
   Subscriptions, Click/Payme/Uzum Payments, and Admin Control.
═══════════════════════════════════════════════════════════════════ */

"use strict";

/* ── CONFIG ──────────────────────────────────────────────────────── */
const API = window.location.port === "8000" ? window.location.origin : "http://127.0.0.1:8000";
let token = sessionStorage.getItem("nova_token") || "";

/* ── STATE ───────────────────────────────────────────────────────── */
let currentUser = null;
let isLogin = true;
let currentChatId = null;
let activeVideoJobId = null;
let activeVideoPollTimer = null;
let studioUploadedFileId = null;
let confirmResolve = null;

let promptHistory = JSON.parse(localStorage.getItem("nova_prompt_history") || "[]");

/* ── UTILITY ─────────────────────────────────────────────────────── */
const $ = (id) => document.getElementById(id);
const show = (id) => { const el = $(id); if (el) el.classList.remove("hidden"); };
const hide = (id) => { const el = $(id); if (el) el.classList.add("hidden"); };

function formatError(detail, fallback = "An unexpected error occurred") {
  if (!detail) return fallback;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((d) => d.msg || d.message || JSON.stringify(d)).join(", ");
  }
  if (typeof detail === "object") {
    return detail.msg || detail.message || JSON.stringify(detail);
  }
  return String(detail);
}

/* ── API HELPER ──────────────────────────────────────────────────── */
async function api(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  if (!(options.body instanceof FormData) && options.body && typeof options.body === "string") {
    headers["Content-Type"] = "application/json";
  }
  const res = await fetch(API + path, { ...options, headers });
  if (res.status === 401 && !path.includes("/login") && !path.includes("/register")) {
    logout();
    throw new Error("Session expired. Please log in again.");
  }
  let data;
  try { data = await res.json(); } catch { data = {}; }
  if (!res.ok) {
    throw new Error(formatError(data.detail, `Server error (${res.status})`));
  }
  return data;
}

/* ── TOAST NOTIFICATIONS ─────────────────────────────────────────── */
function notify(message, type = "info") {
  const icons = { success: "✓", error: "✕", info: "ℹ", warning: "⚠" };
  const container = $("toastContainer");
  if (!container) return;
  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `<span class="toast-icon">${icons[type] || icons.info}</span><span>${message}</span>`;
  container.appendChild(toast);
  setTimeout(() => {
    toast.classList.add("toast-out");
    setTimeout(() => toast.remove(), 320);
  }, 4000);
}

/* ── BLOB DOWNLOAD ───────────────────────────────────────────────── */
async function downloadMedia(mediaUrl, filename) {
  try {
    const fullUrl = mediaUrl.startsWith("http") ? mediaUrl : API + mediaUrl;
    const res = await fetch(fullUrl, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!res.ok) throw new Error("Download failed");
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename || "nova_ai_media";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(() => URL.revokeObjectURL(url), 5000);
    notify("Download started", "success");
  } catch (err) {
    notify("Download failed: " + err.message, "error");
  }
}

/* ── CONFIRM MODAL ───────────────────────────────────────────────── */
function openConfirm(title = "Confirm Action", body = "Are you sure you want to proceed?") {
  const t = $("confirmTitle");
  const b = $("confirmBody");
  if (t) t.textContent = title;
  if (b) b.textContent = body;
  show("confirmModal");
  return new Promise((resolve) => { confirmResolve = resolve; });
}
function closeConfirm(result) {
  hide("confirmModal");
  if (confirmResolve) { confirmResolve(result); confirmResolve = null; }
}

/* ── AUTH WORKFLOW ───────────────────────────────────────────────── */
function openAuthModal(mode = "login") {
  setAuthMode(mode === "login");
  show("authModal");
  setTimeout(() => $("authEmail")?.focus(), 50);
}

function closeAuthModal() {
  hide("authModal");
  hide("authError");
}

$("topbarSignUpBtn")?.addEventListener("click", () => openAuthModal("login"));
$("closeAuthModal")?.addEventListener("click", closeAuthModal);
$("authModal")?.addEventListener("click", (e) => {
  if (e.target.id === "authModal") closeAuthModal();
});

document.querySelectorAll(".social-oauth-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    const provider = btn.dataset.provider || "Social";
    show("passwordStepWrap");
    $("authEmail").value = `developer_${provider.toLowerCase()}@nova.ai`;
    $("authPassword").focus();
    notify(`Connected via ${provider} OAuth sandbox`, "info");
  });
});

function setAuthMode(loginMode) {
  isLogin = loginMode;
  $("authSubmit").textContent = isLogin ? "Continue" : "Create Account";
  $("authSwitchText").textContent = isLogin ? "Don't have an account?" : "Already have an account?";
  $("authToggle").textContent = isLogin ? "Sign Up" : "Log In";
  loginMode ? hide("registerFields") : show("registerFields");
  hide("authError");
}

$("authToggle")?.addEventListener("click", () => {
  setAuthMode(!isLogin);
  show("passwordStepWrap");
});

$("authForm")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  hide("authError");

  const email = $("authEmail").value.trim();
  const passwordStep = $("passwordStepWrap");

  if (passwordStep.classList.contains("hidden")) {
    if (!email) { showAuthError("Please enter your email"); return; }
    show("passwordStepWrap");
    $("authPassword").focus();
    return;
  }

  const password = $("authPassword").value;
  const btn = $("authSubmit");
  if (!password) { showAuthError("Please enter your password"); return; }

  btn.disabled = true;
  btn.textContent = isLogin ? "Signing In…" : "Creating Account…";

  try {
    if (!isLogin) {
      const username = $("regUsername").value.trim() || email.split("@")[0];
      const confirm = $("authConfirm").value;
      if (password !== confirm) throw new Error("Passwords do not match");
      if (password.length < 8) throw new Error("Password must be at least 8 characters");

      await api("/api/auth/register", {
        method: "POST",
        body: JSON.stringify({ username, email, password }),
      });
      notify("Account created! Logging in...", "success");

      const loginRes = await api("/api/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      token = loginRes.access_token;
      sessionStorage.setItem("nova_token", token);
      await loadUser();
      enterApp();
      closeAuthModal();
    } else {
      const json = await api("/api/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      token = json.access_token;
      sessionStorage.setItem("nova_token", token);
      await loadUser();
      enterApp();
      closeAuthModal();
      notify(`Welcome back, ${currentUser.username}!`, "success");
    }
  } catch (err) {
    showAuthError(err.message);
  } finally {
    btn.disabled = false;
    btn.textContent = isLogin ? "Continue" : "Create Account";
  }
});

function showAuthError(msg) {
  const errEl = $("authError");
  if (errEl) { errEl.textContent = msg; show("authError"); }
}

$("togglePassword")?.addEventListener("click", () => {
  const inp = $("authPassword");
  if (inp) inp.type = inp.type === "password" ? "text" : "password";
});

async function loadUser() {
  currentUser = await api("/api/auth/me");
  applyUserToUI();
  loadNotifications();
  return currentUser;
}

function enterApp() {
  show("appShell");
  hide("topbarSignUpBtn");
  show("topbarAvatar");
  applyUserToUI();
}

function applyUserToUI() {
  if (!currentUser) return;
  const initial = (currentUser.username || "U")[0].toUpperCase();
  const colorMap = {
    purple: "linear-gradient(135deg,#9c7cff,#6b5bd6)",
    cyan:   "linear-gradient(135deg,#6be1d2,#3ab8a8)",
    pink:   "linear-gradient(135deg,#f472b6,#db2777)",
    orange: "linear-gradient(135deg,#fb923c,#ea580c)",
    blue:   "linear-gradient(135deg,#60a5fa,#2563eb)",
  };
  const grad = colorMap[currentUser.avatar_color] || colorMap["purple"];
  ["sidebarAvatar", "topbarAvatar", "profileAvatar"].forEach((id) => {
    const el = $(id);
    if (el) { el.textContent = initial; el.style.background = grad; }
  });

  const usernameEl = $("sidebarUsername");
  if (usernameEl) usernameEl.textContent = currentUser.username || "User";

  const creditEl = $("userCreditCount");
  if (creditEl) creditEl.textContent = currentUser.credits ?? 50;

  // Admin access
  if (currentUser.role === "admin") {
    show("adminSidebarBtn");
  } else {
    hide("adminSidebarBtn");
  }

  // Pre-fill profile fields
  const pu = $("profileUsername");
  const pfn = $("profileFullName");
  const pb = $("profileBio");
  if (pu) pu.value = currentUser.username || "";
  if (pfn) pfn.value = currentUser.full_name || "";
  if (pb) pb.value = currentUser.bio || "";
}

function logout() {
  token = "";
  currentUser = null;
  sessionStorage.removeItem("nova_token");
  show("topbarSignUpBtn");
  hide("topbarAvatar");
  hide("adminSidebarBtn");
  const usernameEl = $("sidebarUsername");
  if (usernameEl) usernameEl.textContent = "Guest";
  const avatarEl = $("sidebarAvatar");
  if (avatarEl) { avatarEl.textContent = "G"; avatarEl.style.background = ""; }
  notify("Signed out successfully", "info");
}

/* ── NAVIGATION ──────────────────────────────────────────────────── */
const PAGE_TITLES = {
  dashPage:        "Dashboard",
  chatPage:        "AI Chat Assistant",
  codePage:        "AI Code Assistant",
  createPage:      "Image Generator",
  editPage:        "Image Editor",
  videoPage:       "AI Video Generator",
  voicePage:       "Voice Studio",
  musicPage:       "Music Generator",
  audioStudioPage: "Audio Studio Tools",
  historyPage:     "My Creations",
  pricingPage:     "Subscription & Pricing",
  adminPage:       "Admin Control Panel",
  profilePage:     "Profile Settings",
  settingsPage:    "Platform Settings",
};

function navigate(pageId) {
  document.querySelectorAll(".page").forEach((p) => p.classList.add("hidden"));
  document.querySelectorAll(".nav-item").forEach((n) => n.classList.remove("active"));

  show(pageId);

  const navBtn = document.querySelector(`[data-page="${pageId}"]`);
  if (navBtn) navBtn.classList.add("active");

  const topbarTitle = $("topbarTitle");
  if (topbarTitle) topbarTitle.textContent = PAGE_TITLES[pageId] || "Studio";

  // Mobile sidebar close
  const sidebar = $("sidebar");
  if (sidebar) sidebar.classList.remove("open");

  // Page specific data loaders
  if (pageId === "dashPage")        loadDashboard();
  if (pageId === "chatPage")        loadChatConversations();
  if (pageId === "videoPage")       loadVideoHistory();
  if (pageId === "voicePage")       loadVoiceHistory();
  if (pageId === "musicPage")       loadMusicHistory();
  if (pageId === "audioStudioPage") loadStudioFiles();
  if (pageId === "historyPage")     loadCreations();
  if (pageId === "adminPage")       loadAdminDashboard();
  if (pageId === "profilePage")     applyUserToUI();
}

document.querySelectorAll(".nav-item").forEach((btn) => {
  btn.addEventListener("click", () => navigate(btn.dataset.page));
});

$("hamburger")?.addEventListener("click", () => {
  $("sidebar")?.classList.toggle("open");
});

/* ── NOTIFICATIONS ───────────────────────────────────────────────── */
function toggleNotifications() {
  const drawer = $("notifDrawer");
  if (drawer) drawer.classList.toggle("hidden");
}

async function loadNotifications() {
  if (!token) return;
  try {
    const data = await api("/api/notifications/");
    const badge = $("notifBadge");
    if (badge) {
      if (data.unread_count > 0) {
        badge.textContent = data.unread_count;
        badge.classList.remove("hidden");
      } else {
        badge.classList.add("hidden");
      }
    }
    const list = $("notifList");
    if (list && data.notifications) {
      if (data.notifications.length === 0) {
        list.innerHTML = `<div class="notif-empty">No notifications yet.</div>`;
        return;
      }
      list.innerHTML = data.notifications.map((n) => `
        <div class="notif-item ${n.is_read ? '' : 'unread'}" onclick="markNotificationRead(${n.id})">
          <div class="notif-item-title">${n.title}</div>
          <div class="notif-item-msg">${n.message}</div>
        </div>
      `).join("");
    }
  } catch { /* silent */ }
}

async function markNotificationRead(id) {
  try {
    await api(`/api/notifications/${id}/read`, { method: "PATCH" });
    loadNotifications();
  } catch { /* silent */ }
}

async function markAllNotificationsRead() {
  try {
    await api("/api/notifications/read-all", { method: "POST" });
    loadNotifications();
    notify("All notifications marked as read", "success");
  } catch { /* silent */ }
}

/* ── 1. DASHBOARD ────────────────────────────────────────────────── */
async function loadDashboard() {
  const statsGrid = $("statsGrid");
  statsGrid.innerHTML = [1,2,3,4].map(() => `<div class="stat-card skeleton" style="height:90px"></div>`).join("");

  try {
    const data = await api("/api/dashboard/stats");
    const s = data.statistics;
    statsGrid.innerHTML = `
      <div class="stat-card">
        <div class="stat-value">${s.total_images ?? 0}</div>
        <div class="stat-label">AI Images (${s.total_generated_images} gen / ${s.total_edited_images} edit)</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">${s.total_videos ?? 0}</div>
        <div class="stat-label">Videos Created</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">${s.total_conversations ?? 0}</div>
        <div class="stat-label">Chat Sessions</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">${s.credits_remaining ?? 50}</div>
        <div class="stat-label">Remaining Credits (${s.current_plan.toUpperCase()})</div>
      </div>`;

    const recentGrid = $("recentGrid");
    if (data.recent_activity && data.recent_activity.length > 0) {
      recentGrid.innerHTML = data.recent_activity.map((item) => `
        <div class="hist-card">
          <img src="${API + item.url}" class="card-img" alt="${item.prompt}" />
          <div class="card-body">
            <div class="badge badge-gen">${item.operation.toUpperCase()}</div>
            <div class="card-prompt" title="${item.prompt}">${item.prompt}</div>
          </div>
        </div>
      `).join("");
    } else {
      recentGrid.innerHTML = `<p style="color:var(--text-muted);grid-column:1/-1">No creations yet. Choose any tool above to get started!</p>`;
    }
  } catch {
    statsGrid.innerHTML = `<p style="color:var(--text-muted);grid-column:1/-1">Could not load dashboard stats.</p>`;
  }
}

/* ── 2. AI CHAT ──────────────────────────────────────────────────── */
async function loadChatConversations() {
  if (!token) return;
  try {
    const list = await api("/api/chat/conversations");
    const container = $("conversationList");
    if (!container) return;
    if (list.length === 0) {
      container.innerHTML = `<p style="font-size:0.8rem; color:var(--text-muted); padding:10px;">No chats yet. Click '+ New Chat'.</p>`;
      return;
    }
    container.innerHTML = list.map((c) => `
      <div class="conv-item ${c.id === currentChatId ? 'active' : ''}" onclick="selectConversation(${c.id})">
        <span style="overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">💬 ${c.title}</span>
      </div>
    `).join("");

    if (!currentChatId && list.length > 0) {
      selectConversation(list[0].id);
    }
  } catch (err) {
    notify(err.message, "error");
  }
}

async function createNewChat() {
  if (!token) { openAuthModal("login"); return; }
  try {
    const conv = await api("/api/chat/conversations", {
      method: "POST",
      body: JSON.stringify({ title: "New Conversation", model: "gpt-4o-mini" }),
    });
    currentChatId = conv.id;
    await loadChatConversations();
    selectConversation(conv.id);
  } catch (err) {
    notify(err.message, "error");
  }
}

async function selectConversation(id) {
  currentChatId = id;
  document.querySelectorAll(".conv-item").forEach((el) => el.classList.remove("active"));
  try {
    const conv = await api(`/api/chat/conversations/${id}`);
    $("currentChatTitle").textContent = conv.title;
    $("currentChatModel").textContent = conv.model || "NOVA Smart LLM";

    const msgContainer = $("chatMessages");
    if (!conv.messages || conv.messages.length === 0) {
      msgContainer.innerHTML = `
        <div class="chat-welcome-card">
          <div class="brand-icon" style="margin-bottom: 12px;">✦</div>
          <h2>Ready to help you think, write, and build</h2>
          <p>Ask a question or select a prompt suggestion below.</p>
          <div class="chat-prompts-grid">
            <button class="chat-prompt-card" onclick="sendQuickChatMessage(this)">Explain system architecture patterns for scalable AI applications</button>
            <button class="chat-prompt-card" onclick="sendQuickChatMessage(this)">Write an algorithm to optimize database indexing and queries</button>
            <button class="chat-prompt-card" onclick="sendQuickChatMessage(this)">Translate and localize this product description into Uzbek</button>
          </div>
        </div>
      `;
      return;
    }

    msgContainer.innerHTML = conv.messages.map((m) => renderChatMessageBubble(m.role, m.content)).join("");
    msgContainer.scrollTop = msgContainer.scrollHeight;
  } catch (err) {
    notify(err.message, "error");
  }
}

function renderChatMessageBubble(role, content) {
  const isUser = role === "user";
  const initial = isUser ? (currentUser?.username?.[0]?.toUpperCase() || "U") : "✦";
  return `
    <div class="chat-row ${isUser ? 'user-row' : 'assistant-row'}">
      ${!isUser ? `<div class="chat-avatar-bubble bot-avatar-bubble">${initial}</div>` : ''}
      <div class="chat-bubble">
        ${formatMarkdownContent(content)}
      </div>
      ${isUser ? `<div class="chat-avatar-bubble user-avatar-bubble">${initial}</div>` : ''}
    </div>
  `;
}

function formatMarkdownContent(text) {
  if (!text) return "";
  // Escape HTML tags for security
  let esc = text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  
  // Format code blocks ```lang code ```
  esc = esc.replace(/```([a-zA-Z0-9_-]*)\n([\s\S]*?)```/g, (match, lang, code) => {
    return `
      <div class="code-output-card" style="margin: 10px 0;">
        <div class="code-card-header">
          <span>${lang || 'code'}</span>
          <button class="btn btn-ghost btn-xs" onclick="navigator.clipboard.writeText(decodeURIComponent('${encodeURIComponent(code)}')); notify('Code copied!','success');">Copy</button>
        </div>
        <pre class="code-display">${code}</pre>
      </div>
    `;
  });

  // Inline backticks
  esc = esc.replace(/`([^`]+)`/g, '<code style="background:var(--surface3); padding:2px 6px; border-radius:4px; font-family:monospace;">$1</code>');
  // Bold
  esc = esc.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  // Newlines to breaks
  esc = esc.replace(/\n/g, '<br/>');
  return esc;
}

function sendQuickChatMessage(btn) {
  const input = $("chatInput");
  if (input) {
    input.value = btn.textContent.trim();
    handleSendChatMessage(new Event("submit"));
  }
}

function handleChatInputKey(e) {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    handleSendChatMessage(e);
  }
}

async function handleSendChatMessage(e) {
  if (e) e.preventDefault();
  if (!token) { openAuthModal("login"); return; }
  const input = $("chatInput");
  const text = input.value.trim();
  if (!text) return;
  input.value = "";

  if (!currentChatId) {
    await createNewChat();
  }

  const msgContainer = $("chatMessages");
  // Append user bubble
  msgContainer.innerHTML += renderChatMessageBubble("user", text);
  msgContainer.scrollTop = msgContainer.scrollHeight;

  // Placeholder bot bubble
  const placeholderId = `ai_reply_${Date.now()}`;
  msgContainer.innerHTML += `
    <div class="chat-row assistant-row" id="${placeholderId}">
      <div class="chat-avatar-bubble bot-avatar-bubble">✦</div>
      <div class="chat-bubble">
        <span class="btn-loader">NOVA AI is thinking…</span>
      </div>
    </div>
  `;
  msgContainer.scrollTop = msgContainer.scrollHeight;

  try {
    const res = await api(`/api/chat/conversations/${currentChatId}/messages`, {
      method: "POST",
      body: JSON.stringify({ content: text }),
    });

    const aiBubble = $(placeholderId);
    if (aiBubble) {
      aiBubble.querySelector(".chat-bubble").innerHTML = formatMarkdownContent(res.assistant_message.content);
    }
    if (res.remaining_credits !== undefined) {
      $("userCreditCount").textContent = res.remaining_credits;
      if (currentUser) currentUser.credits = res.remaining_credits;
    }
  } catch (err) {
    const aiBubble = $(placeholderId);
    if (aiBubble) {
      aiBubble.querySelector(".chat-bubble").innerHTML = `<span style="color:var(--danger)">Error: ${err.message}</span>`;
    }
  }
}

async function exportCurrentChat() {
  if (!currentChatId) return;
  try {
    const data = await api(`/api/chat/conversations/${currentChatId}/export?format=markdown`);
    const blob = new Blob([data.content], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = data.filename || "conversation.md";
    a.click();
    URL.revokeObjectURL(url);
    notify("Export complete", "success");
  } catch (err) {
    notify(err.message, "error");
  }
}

async function renameCurrentChatPrompt() {
  if (!currentChatId) return;
  const newTitle = prompt("Enter new conversation title:");
  if (newTitle && newTitle.trim()) {
    try {
      await api(`/api/chat/conversations/${currentChatId}`, {
        method: "PATCH",
        body: JSON.stringify({ title: newTitle.trim() }),
      });
      loadChatConversations();
      selectConversation(currentChatId);
      notify("Conversation renamed", "success");
    } catch (err) {
      notify(err.message, "error");
    }
  }
}

async function deleteCurrentChatPrompt() {
  if (!currentChatId) return;
  const ok = await openConfirm("Delete Conversation", "Are you sure you want to delete this chat?");
  if (ok) {
    try {
      await api(`/api/chat/conversations/${currentChatId}`, { method: "DELETE" });
      currentChatId = null;
      await loadChatConversations();
      $("chatMessages").innerHTML = `<div class="chat-welcome-card"><h2>Conversation deleted</h2></div>`;
      notify("Deleted", "info");
    } catch (err) {
      notify(err.message, "error");
    }
  }
}

/* ── 3. AI CODE ASSISTANT ────────────────────────────────────────── */
// Tabs
document.querySelectorAll(".code-tab-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".code-tab-btn").forEach((b) => b.classList.remove("active"));
    document.querySelectorAll(".code-tab-content").forEach((c) => c.classList.add("hidden"));
    btn.classList.add("active");
    show(btn.dataset.tab);
  });
});

async function submitGenerateCode() {
  if (!token) { openAuthModal("login"); return; }
  const promptVal = $("codePrompt").value.trim();
  const lang = $("codeLanguage").value;
  if (!promptVal) { notify("Enter a code description", "error"); return; }

  const btn = $("generateCodeBtn");
  btn.disabled = true;
  btn.textContent = "Synthesizing Code…";
  $("codeGenOutput").textContent = "Generating complete production code...";

  try {
    const res = await api("/api/code/generate", {
      method: "POST",
      body: JSON.stringify({ prompt: promptVal, language: lang }),
    });
    $("codeGenOutput").textContent = res.solution;
    if (res.remaining_credits !== undefined) $("userCreditCount").textContent = res.remaining_credits;
    notify("Code generated successfully!", "success");
  } catch (err) {
    $("codeGenOutput").textContent = "Error: " + err.message;
    notify(err.message, "error");
  } finally {
    btn.disabled = false;
    btn.textContent = "Generate Production Code";
  }
}

async function submitDebugCode() {
  if (!token) { openAuthModal("login"); return; }
  const code = $("debugSourceCode").value.trim();
  const err = $("debugErrorMessage").value.trim();
  if (!code) { notify("Paste source code first", "error"); return; }

  const btn = $("debugSubmitBtn");
  btn.disabled = true;
  btn.textContent = "Analyzing Bug…";
  $("debugOutput").textContent = "Analyzing root cause and generating fix...";

  try {
    const res = await api("/api/code/debug", {
      method: "POST",
      body: JSON.stringify({ code, error_message: err, language: "python" }),
    });
    $("debugOutput").textContent = res.analysis_and_fix;
    notify("Debug diagnosis complete!", "success");
  } catch (err) {
    $("debugOutput").textContent = "Error: " + err.message;
    notify(err.message, "error");
  } finally {
    btn.disabled = false;
    btn.textContent = "Diagnose & Fix Code";
  }
}

async function submitReviewCode() {
  if (!token) { openAuthModal("login"); return; }
  const code = $("reviewSourceCode").value.trim();
  if (!code) { notify("Paste code for review", "error"); return; }

  const btn = $("reviewSubmitBtn");
  btn.disabled = true;
  btn.textContent = "Auditing Code…";
  $("reviewOutput").textContent = "Auditing security, OWASP vulnerabilities, and performance bottlenecks...";

  try {
    const res = await api("/api/code/review", {
      method: "POST",
      body: JSON.stringify({ code, language: "python" }),
    });
    $("reviewOutput").textContent = res.review;
    notify("Code review complete!", "success");
  } catch (err) {
    $("reviewOutput").textContent = "Error: " + err.message;
    notify(err.message, "error");
  } finally {
    btn.disabled = false;
    btn.textContent = "Run Code Review";
  }
}

async function submitBuildProject() {
  if (!token) { openAuthModal("login"); return; }
  const desc = $("projectDesc").value.trim();
  const stack = $("projectTechStack").value.trim();
  if (!desc) { notify("Describe your project", "error"); return; }

  const btn = $("buildProjectBtn");
  btn.disabled = true;
  btn.textContent = "Architecting Project…";
  $("projectBlueprintOutput").textContent = "Architecting multi-file software blueprint...";

  try {
    const res = await api("/api/code/build-project", {
      method: "POST",
      body: JSON.stringify({ description: desc, tech_stack: stack }),
    });
    $("projectBlueprintOutput").textContent = res.blueprint;
    notify("Project blueprint created!", "success");
  } catch (err) {
    $("projectBlueprintOutput").textContent = "Error: " + err.message;
    notify(err.message, "error");
  } finally {
    btn.disabled = false;
    btn.textContent = "Generate Project Blueprint";
  }
}

async function submitExecuteSandbox() {
  if (!token) { openAuthModal("login"); return; }
  const code = $("sandboxCode").value.trim();
  const lang = $("sandboxLang").value;
  if (!code) { notify("Write code to execute", "error"); return; }

  const btn = $("runSandboxBtn");
  btn.disabled = true;
  btn.textContent = "Executing in Sandbox…";
  $("sandboxOutput").textContent = "Spawning isolated subprocess execution environment...";

  try {
    const res = await api("/api/code/execute", {
      method: "POST",
      body: JSON.stringify({ code, language: lang }),
    });
    $("sandboxMeta").textContent = `${res.execution_time_ms} ms — Exit code ${res.returncode ?? 0}`;
    if (res.success) {
      $("sandboxOutput").textContent = res.stdout || "(Code executed cleanly with no stdout output)";
      notify("Execution finished successfully", "success");
    } else {
      $("sandboxOutput").textContent = res.stderr || res.stdout || "Execution failed";
      notify("Execution error encountered", "warning");
    }
  } catch (err) {
    $("sandboxOutput").textContent = "Execution harness error: " + err.message;
    notify(err.message, "error");
  } finally {
    btn.disabled = false;
    btn.textContent = "▶ Run in Sandbox";
  }
}

function copyCodeOutput(elementId) {
  const text = $(elementId)?.textContent;
  if (text) {
    navigator.clipboard.writeText(text);
    notify("Copied to clipboard!", "success");
  }
}

/* ── 4. CREATE IMAGE (TEXT TO IMAGE) ─────────────────────────────── */
function initVisualSelectors() {
  document.querySelectorAll(".style-card").forEach((card) => {
    card.addEventListener("click", () => {
      document.querySelectorAll(".style-card").forEach((c) => c.classList.remove("active"));
      card.classList.add("active");
      const inp = $("style");
      if (inp) inp.value = card.dataset.style;
    });
  });

  document.querySelectorAll(".ratio-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".ratio-btn").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      const inp = $("ratio");
      if (inp) inp.value = btn.dataset.ratio;
    });
  });
}

function updatePromptCount() {
  const val = $("prompt").value.length;
  $("promptCount").textContent = `${val} / 1000`;
}
$("prompt")?.addEventListener("input", updatePromptCount);

function toggleAdvanced() {
  const group = $("negativePromptGroup");
  const btn = $("advancedToggle");
  const isHidden = group.classList.contains("hidden");
  group.classList.toggle("hidden", !isHidden);
  btn.textContent = isHidden ? "⚙ Hide advanced" : "⚙ Advanced options";
}

function improvePrompt() {
  const prompt = $("prompt").value.trim();
  if (!prompt) { notify("Enter a prompt first", "error"); return; }
  const style = $("style").value;
  const additions = {
    "Photorealistic": "highly detailed, 8K resolution, professional photography, perfect lighting, sharp focus",
    "3D Render":      "octane render, ray tracing, studio lighting, 4K, high detail, professional 3D",
    "Anime":          "anime art style, detailed, vibrant colors, clean lines, professional illustration",
    "Digital Art":    "digital painting, concept art, artstation, high quality, detailed brushwork",
    "Cinematic":      "cinematic photography, movie still, dramatic lighting, 35mm film, anamorphic lens",
    "Fantasy":        "ethereal, hyperdetailed, fantasy concept art, volumetric lighting, magical atmosphere",
    "Minimalist":     "minimalist design, clean composition, simple elegant, white space, modern",
  };
  $("prompt").value = `${prompt}, ${additions[style] || 'high quality, masterpiece, detailed'}`;
  updatePromptCount();
  notify("Prompt enhanced!", "success");
}

function togglePromptHistory() {
  const dropdown = $("promptHistoryDropdown");
  if (promptHistory.length === 0) { notify("No prompt history yet", "info"); return; }
  dropdown.classList.toggle("hidden");
  dropdown.innerHTML = promptHistory.slice(-5).reverse().map((p) => `<div class="prompt-hist-item" title="${p}">${p}</div>`).join("");
  dropdown.querySelectorAll(".prompt-hist-item").forEach((item) => {
    item.addEventListener("click", () => {
      $("prompt").value = item.title;
      updatePromptCount();
      hide("promptHistoryDropdown");
    });
  });
}

function fillPrompt(btn) {
  const p = $("prompt");
  if (p) {
    p.value = btn.textContent.trim();
    updatePromptCount();
    p.focus();
    notify("Prompt loaded!", "info");
  }
}

let lastGeneratedImageUrl = "";
let lastGeneratedFilename = "";

async function generateImage() {
  if (!token) { openAuthModal("login"); return; }
  const promptVal = $("prompt").value.trim();
  if (!promptVal) { notify("Please enter a prompt", "error"); return; }

  const btn = $("generateBtn");
  setButtonLoading(btn, true);
  hide("canvasEmptyState");
  hide("generateResult");
  show("canvasLoadingState");

  if (!promptHistory.includes(promptVal)) {
    promptHistory.unshift(promptVal);
    if (promptHistory.length > 10) promptHistory.pop();
    localStorage.setItem("nova_prompt_history", JSON.stringify(promptHistory));
  }

  try {
    const fd = new FormData();
    fd.append("prompt", promptVal);
    fd.append("style", $("style").value);
    fd.append("ratio", $("ratio").value);
    const neg = $("negativePrompt").value.trim();
    if (neg) fd.append("negative_prompt", neg);

    const data = await api("/api/images/generate", { method: "POST", body: fd });
    const imgUrl = data.image;
    lastGeneratedImageUrl = imgUrl;
    lastGeneratedFilename = data.filename;

    $("resultImage").src = API + imgUrl;
    hide("canvasLoadingState");
    show("generateResult");

    $("generateDownloadBtn").onclick = () => downloadMedia(imgUrl, data.filename);
    $("generateVariationBtn").onclick = () => createVariation(imgUrl, data.filename);

    if (data.remaining_credits !== undefined) $("userCreditCount").textContent = data.remaining_credits;
    notify(`Image generated successfully via ${data.provider}!`, "success");
  } catch (err) {
    hide("canvasLoadingState");
    show("canvasEmptyState");
    notify(err.message, "error");
  } finally {
    setButtonLoading(btn, false);
  }
}

async function createVariation(imageUrl, filename) {
  notify("Creating variation...", "info");
  try {
    const res = await fetch(API + imageUrl);
    const blob = await res.blob();
    const fd = new FormData();
    fd.append("image", new File([blob], filename || "img.png", { type: blob.type }));
    fd.append("ratio", $("ratio").value);

    const data = await api("/api/images/variation", { method: "POST", body: fd });
    $("resultImage").src = API + data.image;
    lastGeneratedImageUrl = data.image;
    lastGeneratedFilename = data.filename;
    notify("Variation created!", "success");
  } catch (err) {
    notify(err.message, "error");
  }
}

function editInEditor() {
  if (!lastGeneratedImageUrl) return;
  sessionStorage.setItem("edit_prefill_url", API + lastGeneratedImageUrl);
  sessionStorage.setItem("edit_prefill_filename", lastGeneratedFilename);
  navigate("editPage");
  prefillEditorImage();
}

/* ── 5. IMAGE EDITOR (FIXED!) ────────────────────────────────────── */
let uploadedFile = null;
let editBeforeUrl = "";
let editAfterUrl = "";
let showingBefore = false;

function handleUpload(event) {
  const file = event.target.files[0];
  if (file) processUpload(file);
}

function processUpload(file) {
  const allowed = ["image/png", "image/jpeg", "image/webp"];
  if (!allowed.includes(file.type)) { notify("Please upload PNG, JPG, or WEBP", "error"); return; }
  if (file.size > 15 * 1024 * 1024) { notify("File must be under 15 MB", "error"); return; }
  uploadedFile = file;

  const reader = new FileReader();
  reader.onload = (e) => {
    $("uploadedImage").src = e.target.result;
    editBeforeUrl = e.target.result;
    hide("uploadPlaceholder");
    show("uploadPreview");
  };
  reader.readAsDataURL(file);
}

function removeUpload(e) {
  if (e) e.stopPropagation();
  uploadedFile = null;
  $("imageUpload").value = "";
  $("uploadedImage").src = "";
  editBeforeUrl = "";
  show("uploadPlaceholder");
  hide("uploadPreview");
  hide("editResult");
}

async function prefillEditorImage() {
  const prefillUrl = sessionStorage.getItem("edit_prefill_url");
  if (!prefillUrl) return;
  sessionStorage.removeItem("edit_prefill_url");
  sessionStorage.removeItem("edit_prefill_filename");
  try {
    const res = await fetch(prefillUrl);
    const blob = await res.blob();
    const file = new File([blob], "transferred.png", { type: blob.type });
    processUpload(file);
    notify("Image loaded into Editor", "info");
  } catch { /* silent */ }
}

async function transformImage() {
  if (!token) { openAuthModal("login"); return; }
  if (!uploadedFile) { notify("Please upload an image first", "error"); return; }
  const promptVal = $("editPrompt").value.trim();
  if (!promptVal) { notify("Please enter an edit instruction", "error"); return; }

  const btn = $("transformBtn");
  setButtonLoading(btn, true);
  hide("editResult");

  try {
    const fd = new FormData();
    fd.append("prompt", promptVal);
    fd.append("image", uploadedFile, uploadedFile.name);
    fd.append("style", $("editStyle").value);
    fd.append("ratio", $("editRatio").value);

    const data = await api("/api/images/edit", { method: "POST", body: fd });
    editAfterUrl = API + data.image;

    $("editResultImage").src = editAfterUrl;
    $("baLabel").textContent = "After";
    show("editResult");
    showingBefore = false;

    $("editDownloadBtn").onclick = () => downloadMedia(data.image, data.filename);
    if (data.remaining_credits !== undefined) $("userCreditCount").textContent = data.remaining_credits;
    notify(`Transformation complete via ${data.provider}!`, "success");
  } catch (err) {
    notify(err.message, "error");
  } finally {
    setButtonLoading(btn, false);
  }
}

function toggleBeforeAfter() {
  const img = $("editResultImage");
  const label = $("baLabel");
  if (!editBeforeUrl || !editAfterUrl) return;
  showingBefore = !showingBefore;
  img.src = showingBefore ? editBeforeUrl : editAfterUrl;
  if (label) label.textContent = showingBefore ? "Before" : "After";
}

/* ── 6. AI VIDEO GENERATOR ───────────────────────────────────────── */
function setVideoMode(mode) {
  if (mode === "text") {
    $("videoModeTextBtn").classList.add("active");
    $("videoModeImgBtn").classList.remove("active");
    hide("videoImageUploadWrap");
  } else {
    $("videoModeImgBtn").classList.add("active");
    $("videoModeTextBtn").classList.remove("active");
    show("videoImageUploadWrap");
  }
}

async function submitGenerateVideo() {
  if (!token) { openAuthModal("login"); return; }
  const promptVal = $("videoPrompt").value.trim();
  if (!promptVal) { notify("Please enter a motion prompt", "error"); return; }

  const isImg = $("videoModeImgBtn").classList.contains("active");
  const btn = $("generateVideoBtn");
  btn.disabled = true;

  show("videoProgressCard");
  hide("videoResultCard");
  $("videoProgressBar").style.width = "15%";
  $("videoStatusText").textContent = "Submitting video generation job...";

  try {
    const fd = new FormData();
    fd.append("prompt", promptVal);
    fd.append("source_type", isImg ? "image" : "text");
    fd.append("style", $("videoStyle").value);
    fd.append("duration", $("videoDuration").value);

    if (isImg) {
      const imgFile = $("videoImageInput").files[0];
      if (imgFile) fd.append("image", imgFile);
    }

    const data = await api("/api/videos/generate", { method: "POST", body: fd });
    activeVideoJobId = data.job_id;
    if (data.remaining_credits !== undefined) $("userCreditCount").textContent = data.remaining_credits;
    notify("Video generation started in background", "info");

    pollVideoJobProgress(data.job_id);
  } catch (err) {
    hide("videoProgressCard");
    btn.disabled = false;
    notify(err.message, "error");
  }
}

function pollVideoJobProgress(jobId) {
  if (activeVideoPollTimer) clearInterval(activeVideoPollTimer);

  activeVideoPollTimer = setInterval(async () => {
    try {
      const job = await api(`/api/videos/jobs/${jobId}`);
      $("videoProgressBar").style.width = `${Math.max(15, job.progress)}%`;
      $("videoStatusText").textContent = `Synthesizing frames: ${job.progress}% (${job.status})`;

      if (job.status === "completed") {
        clearInterval(activeVideoPollTimer);
        hide("videoProgressCard");
        $("generateVideoBtn").disabled = false;

        const player = $("videoPlayer");
        player.src = API + job.video_url;
        show("videoResultCard");

        $("videoDownloadLink").onclick = () => downloadMedia(job.video_url, "nova_ai_video.mp4");
        notify("Video generation completed!", "success");
      } else if (job.status === "failed") {
        clearInterval(activeVideoPollTimer);
        hide("videoProgressCard");
        $("generateVideoBtn").disabled = false;
        notify(`Video job failed: ${job.error_message}`, "error");
      }
    } catch (e) {
      clearInterval(activeVideoPollTimer);
      $("generateVideoBtn").disabled = false;
    }
  }, 2500);
}

async function loadVideoHistory() {
  if (!token) return;
  try {
    const videos = await api("/api/videos/history");
    if (videos.length > 0 && !$("videoPlayer").src) {
      const last = videos[0];
      if (last.video_url) {
        $("videoPlayer").src = API + last.video_url;
        show("videoResultCard");
        $("videoDownloadLink").onclick = () => downloadMedia(last.video_url, "nova_ai_video.mp4");
      }
    }
  } catch { /* silent */ }
}

/* ── 7. VOICE STUDIO ─────────────────────────────────────────────── */
async function submitGenerateVoice() {
  if (!token) { openAuthModal("login"); return; }
  const text = $("voiceText").value.trim();
  if (!text) { notify("Enter text for voice synthesis", "error"); return; }

  const btn = $("generateVoiceBtn");
  btn.disabled = true;
  btn.textContent = "Synthesizing Voice…";

  try {
    const fd = new FormData();
    fd.append("text", text);
    fd.append("voice", $("voiceSelect").value);
    fd.append("speed", $("voiceSpeed").value);
    fd.append("language", $("voiceLanguage").value);

    const data = await api("/api/voice/tts", { method: "POST", body: fd });
    const player = $("voiceAudioPlayer");
    player.src = API + data.audio_url;
    player.play();

    $("voiceDownloadBtn").onclick = () => downloadMedia(data.audio_url, data.filename);
    if (data.remaining_credits !== undefined) $("userCreditCount").textContent = data.remaining_credits;
    notify(`Voice synthesized using ${data.provider}!`, "success");
  } catch (err) {
    notify(err.message, "error");
  } finally {
    btn.disabled = false;
    btn.textContent = "🎙️ Synthesize Speech";
  }
}

async function loadVoiceHistory() {
  if (!token) return;
  try {
    const history = await api("/api/voice/history");
    if (history.length > 0 && !$("voiceAudioPlayer").src) {
      $("voiceAudioPlayer").src = API + history[0].audio_url;
      $("voiceDownloadBtn").onclick = () => downloadMedia(history[0].audio_url, "voice.mp3");
    }
  } catch { /* silent */ }
}

/* ── 8. MUSIC GENERATOR ──────────────────────────────────────────── */
async function submitGenerateMusic() {
  if (!token) { openAuthModal("login"); return; }
  const promptVal = $("musicPrompt").value.trim();
  if (!promptVal) { notify("Enter a music theme or description", "error"); return; }

  const btn = $("generateMusicBtn");
  btn.disabled = true;
  btn.textContent = "Composing Music Track…";

  try {
    const fd = new FormData();
    fd.append("prompt", promptVal);
    fd.append("genre", $("musicGenre").value);
    fd.append("mood", $("musicMood").value);
    fd.append("duration", 20);

    const data = await api("/api/music/generate", { method: "POST", body: fd });
    $("musicTrackTitle").textContent = data.title;
    $("musicTrackDetails").textContent = `${data.genre} • ${data.mood} • ${data.duration}s • Synthesized via ${data.provider}`;

    const player = $("musicAudioPlayer");
    player.src = API + data.audio_url;
    player.play();

    $("musicDownloadBtn").onclick = () => downloadMedia(data.audio_url, "nova_music.wav");
    if (data.remaining_credits !== undefined) $("userCreditCount").textContent = data.remaining_credits;
    notify("Original music composition created!", "success");
  } catch (err) {
    notify(err.message, "error");
  } finally {
    btn.disabled = false;
    btn.textContent = "🎵 Generate Music Track (3 Credits)";
  }
}

async function loadMusicHistory() {
  if (!token) return;
  try {
    const list = await api("/api/music/history");
    if (list.length > 0 && !$("musicAudioPlayer").src) {
      const first = list[0];
      $("musicTrackTitle").textContent = first.title;
      $("musicAudioPlayer").src = API + first.audio_url;
      $("musicDownloadBtn").onclick = () => downloadMedia(first.audio_url, "nova_music.wav");
    }
  } catch { /* silent */ }
}

/* ── 9. AUDIO STUDIO TOOLS ───────────────────────────────────────── */
async function handleStudioAudioUpload(e) {
  const file = e.target.files[0];
  if (!file) return;

  const fd = new FormData();
  fd.append("file", file);
  notify("Uploading audio file for inspection...", "info");

  try {
    const res = await api("/api/audio-studio/upload", { method: "POST", body: fd });
    studioUploadedFileId = res.id;
    const m = res.metadata;
    $("studioMetaInfo").innerHTML = `
      <strong>${res.original_name}</strong> &bull; Format: ${m.format?.toUpperCase()} &bull; Duration: ${m.duration_seconds}s &bull; Rate: ${m.sample_rate}Hz
    `;
    $("studioAudioPlayer").src = API + res.audio_url;
    notify("Audio file uploaded and analyzed!", "success");
  } catch (err) {
    notify(err.message, "error");
  }
}

async function submitProcessAudioStudio() {
  if (!studioUploadedFileId) { notify("Please upload an audio file first", "error"); return; }
  const btn = $("processAudioBtn");
  btn.disabled = true;
  btn.textContent = "Processing Audio…";

  try {
    const fd = new FormData();
    fd.append("file_id", studioUploadedFileId);
    fd.append("start_sec", $("studioStartSec").value || 0.0);
    const end = $("studioEndSec").value;
    if (end) fd.append("end_sec", end);
    fd.append("volume", $("studioVolume").value);
    fd.append("target_format", $("studioFormat").value);

    const res = await api("/api/audio-studio/process", { method: "POST", body: fd });
    $("studioAudioPlayer").src = API + res.audio_url;
    $("studioDownloadBtn").onclick = () => downloadMedia(res.audio_url, res.filename);
    notify("Audio processed successfully!", "success");
  } catch (err) {
    notify(err.message, "error");
  } finally {
    btn.disabled = false;
    btn.textContent = "🎚️ Process Audio";
  }
}

async function loadStudioFiles() {
  if (!token) return;
  try {
    const files = await api("/api/audio-studio/files");
    if (files.length > 0 && !studioUploadedFileId) {
      studioUploadedFileId = files[0].id;
      $("studioAudioPlayer").src = API + files[0].audio_url;
    }
  } catch { /* silent */ }
}

/* ── 10. MY CREATIONS LIBRARY ────────────────────────────────────── */
let activeCreationsCategory = "all";

function filterCreationsCategory(cat) {
  activeCreationsCategory = cat;
  document.querySelectorAll("#creationsCategoryPills .pill").forEach((p) => {
    p.classList.toggle("active", p.dataset.cat === cat);
  });
  loadCreations();
}

function handleCreationsSearch() {
  loadCreations();
}

async function loadCreations() {
  if (!token) return;
  const search = $("historySearch").value.trim();
  const grid = $("historyGrid");
  const empty = $("historyEmpty");
  grid.innerHTML = [1,2,3,4].map(() => `<div class="skeleton-card skeleton"></div>`).join("");

  try {
    const searchParam = search ? `&search=${encodeURIComponent(search)}` : "";
    const res = await api(`/api/creations/?category=${activeCreationsCategory}${searchParam}&limit=30`);
    if (!res.items || res.items.length === 0) {
      grid.innerHTML = "";
      show("historyEmpty");
      return;
    }
    hide("historyEmpty");

    grid.innerHTML = res.items.map((item) => {
      let previewHtml = "";
      if (item.type === "image") {
        previewHtml = `<img src="${API + item.media_url}" class="card-img" alt="${item.title}" />`;
      } else if (item.type === "video") {
        previewHtml = `<video src="${API + item.media_url}" class="card-img" preload="metadata"></video>`;
      } else {
        previewHtml = `<div style="height:140px; display:flex; align-items:center; justify-content:center; background:var(--surface3); font-size:2.5rem;">${item.type==='music'?'🎵':'💬'}</div>`;
      }

      return `
        <div class="hist-card">
          ${previewHtml}
          <div class="card-body">
            <div class="badge badge-gen">${item.subtype || item.type.toUpperCase()}</div>
            <div class="card-prompt" title="${item.description}">${item.title}</div>
            <div style="display:flex; gap:6px; margin-top:8px;">
              ${item.media_url ? `<button class="btn btn-ghost btn-xs" onclick="downloadMedia('${item.media_url}', '${item.title}')">⬇</button>` : ''}
              <button class="btn btn-danger btn-xs" onclick="deleteCreationItem('${item.type}', ${item.id})">🗑</button>
            </div>
          </div>
        </div>
      `;
    }).join("");
  } catch {
    grid.innerHTML = `<p style="color:var(--text-muted);grid-column:1/-1">Failed to load creations.</p>`;
  }
}

async function deleteCreationItem(type, id) {
  const ok = await openConfirm("Delete Creation", `Are you sure you want to delete this ${type}?`);
  if (!ok) return;
  try {
    await api(`/api/creations/${type}/${id}`, { method: "DELETE" });
    notify("Item deleted", "success");
    loadCreations();
  } catch (err) {
    notify(err.message, "error");
  }
}

/* ── 11. SUBSCRIPTIONS & CHECKOUT ────────────────────────────────── */
let selectedPlanCode = "pro";

function openCheckoutModal(planCode, planName) {
  if (!token) { openAuthModal("login"); return; }
  selectedPlanCode = planCode;
  $("checkoutPlanDesc").textContent = `Upgrade to ${planName} using secure Uzbekistan payment rails (Click, Payme, Uzum Bank).`;
  show("checkoutModal");
}

function closeCheckoutModal() {
  hide("checkoutModal");
}

async function processPaymentCheckout() {
  const provider = document.querySelector('input[name="payProvider"]:checked')?.value || "click";
  const isSandbox = $("sandboxSimulateCheck").checked;
  const btn = $("confirmPaymentBtn");
  btn.disabled = true;
  btn.textContent = "Processing…";

  try {
    if (isSandbox) {
      const res = await api("/api/payments/sandbox-simulate", {
        method: "POST",
        body: JSON.stringify({ provider, plan_code: selectedPlanCode }),
      });
      notify(res.message, "success");
      $("userCreditCount").textContent = res.credits;
      if (currentUser) {
        currentUser.plan = res.plan;
        currentUser.credits = res.credits;
      }
      closeCheckoutModal();
      navigate("dashPage");
    } else {
      const checkout = await api("/api/subscriptions/checkout", {
        method: "POST",
        body: JSON.stringify({ plan_code: selectedPlanCode, provider }),
      });
      if (checkout.payment_url) {
        window.open(checkout.payment_url, "_blank");
        notify("Payment gateway opened in new tab", "info");
      }
      closeCheckoutModal();
    }
  } catch (err) {
    notify(err.message, "error");
  } finally {
    btn.disabled = false;
    btn.textContent = "Confirm & Proceed";
  }
}

/* ── 12. ADMIN CONTROL PANEL ─────────────────────────────────────── */
async function loadAdminDashboard() {
  if (!token || currentUser?.role !== "admin") return;
  const metricsGrid = $("adminMetricsGrid");
  try {
    const data = await api("/api/admin/overview");
    const m = data.metrics;
    const w = data.ai_workload;

    metricsGrid.innerHTML = `
      <div class="stat-card">
        <div class="stat-value">${m.total_users}</div>
        <div class="stat-label">Total Users (${m.active_users} active)</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">${m.total_revenue_uzs.toLocaleString()} UZS</div>
        <div class="stat-label">Platform Revenue (${m.pro_subscribers} Pro, ${m.premium_subscribers} Ultra)</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">${w.total_ai_operations}</div>
        <div class="stat-label">Total AI Workload Operations</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">${w.image_generations + w.video_generations}</div>
        <div class="stat-label">Synthesized Media (Images & Videos)</div>
      </div>
    `;

    // Users table
    const usersRes = await api("/api/admin/users?limit=50");
    const tbody = $("adminUsersTbody");
    tbody.innerHTML = usersRes.users.map((u) => `
      <tr>
        <td style="padding:10px 16px;">#${u.id}</td>
        <td style="padding:10px 16px;">
          <strong>${u.username}</strong><br/>
          <span style="font-size:0.75rem; color:var(--text-muted);">${u.email}</span>
        </td>
        <td style="padding:10px 16px;">
          <span class="badge-role ${u.role==='admin'?'badge-admin':'badge-user'}">${u.role.toUpperCase()}</span>
        </td>
        <td style="padding:10px 16px;">${u.plan.toUpperCase()}</td>
        <td style="padding:10px 16px;">${u.credits}</td>
        <td style="padding:10px 16px;">
          <span style="color:${u.is_active?'var(--success)':'var(--danger)'}; font-weight:600;">${u.is_active?'Active':'Suspended'}</span>
        </td>
        <td style="padding:10px 16px;">
          <button class="btn btn-ghost btn-xs" onclick="adminToggleRole(${u.id}, '${u.role==='admin'?'user':'admin'}')">Role</button>
          <button class="btn btn-ghost btn-xs" onclick="adminToggleStatus(${u.id}, ${!u.is_active})">${u.is_active?'Suspend':'Activate'}</button>
          <button class="btn btn-ghost btn-xs" onclick="adminAdjustCreditsPrompt(${u.id}, ${u.credits})">+Credits</button>
        </td>
      </tr>
    `).join("");
  } catch (err) {
    notify(err.message, "error");
  }
}

async function adminToggleRole(userId, newRole) {
  try {
    await api(`/api/admin/users/${userId}/role`, {
      method: "PATCH",
      body: JSON.stringify({ role: newRole }),
    });
    notify("User role updated", "success");
    loadAdminDashboard();
  } catch (err) {
    notify(err.message, "error");
  }
}

async function adminToggleStatus(userId, newStatus) {
  try {
    await api(`/api/admin/users/${userId}/status`, {
      method: "PATCH",
      body: JSON.stringify({ is_active: newStatus }),
    });
    notify("User status updated", "success");
    loadAdminDashboard();
  } catch (err) {
    notify(err.message, "error");
  }
}

async function adminAdjustCreditsPrompt(userId, currentCredits) {
  const amount = prompt("Enter new credit balance:", currentCredits + 100);
  if (amount !== null && !isNaN(parseInt(amount))) {
    try {
      await api(`/api/admin/users/${userId}/credits`, {
        method: "PATCH",
        body: JSON.stringify({ credits: parseInt(amount) }),
      });
      notify("Credits updated", "success");
      loadAdminDashboard();
    } catch (err) {
      notify(err.message, "error");
    }
  }
}

/* ── 13. PROFILE & PASSWORD ──────────────────────────────────────── */
document.querySelectorAll(".color-dot").forEach((dot) => {
  dot.addEventListener("click", () => {
    document.querySelectorAll(".color-dot").forEach((d) => d.classList.remove("selected"));
    dot.classList.add("selected");
    const colorMap = {
      purple: "linear-gradient(135deg,#9c7cff,#6b5bd6)",
      cyan:   "linear-gradient(135deg,#6be1d2,#3ab8a8)",
      pink:   "linear-gradient(135deg,#f472b6,#db2777)",
      orange: "linear-gradient(135deg,#fb923c,#ea580c)",
      blue:   "linear-gradient(135deg,#60a5fa,#2563eb)",
    };
    const grad = colorMap[dot.dataset.color] || colorMap["purple"];
    ["sidebarAvatar", "topbarAvatar", "profileAvatar"].forEach((id) => {
      const el = $(id);
      if (el) el.style.background = grad;
    });
  });
});

async function saveProfile() {
  const username = $("profileUsername").value.trim();
  const full_name = $("profileFullName").value.trim();
  const bio = $("profileBio").value.trim();
  const selectedColor = document.querySelector(".color-dot.selected")?.dataset.color || "purple";

  if (!username) { notify("Username cannot be empty", "error"); return; }

  try {
    const updated = await api("/api/auth/me", {
      method: "PATCH",
      body: JSON.stringify({ username, full_name, bio, avatar_color: selectedColor }),
    });
    currentUser = updated;
    applyUserToUI();
    notify("Profile updated successfully!", "success");
  } catch (err) {
    notify(err.message, "error");
  }
}

async function changePassword() {
  const current = $("currentPassword").value;
  const newPass = $("newPassword").value;
  const confirm = $("confirmNewPassword").value;

  if (!current || !newPass) { notify("Fill in all password fields", "error"); return; }
  if (newPass !== confirm) { notify("New passwords do not match", "error"); return; }
  if (newPass.length < 8) { notify("Password must be at least 8 characters", "error"); return; }

  try {
    await api("/api/auth/change-password", {
      method: "POST",
      body: JSON.stringify({ current_password: current, new_password: newPass }),
    });
    $("currentPassword").value = "";
    $("newPassword").value = "";
    $("confirmNewPassword").value = "";
    notify("Password updated successfully!", "success");
  } catch (err) {
    notify(err.message, "error");
  }
}

async function deleteAccountPrompt() {
  const ok = await openConfirm("Delete Account", "WARNING: This will permanently delete your account and all generated media. Proceed?");
  if (!ok) return;

  try {
    await api("/api/auth/me", { method: "DELETE" });
    notify("Account deleted", "info");
    logout();
  } catch (err) {
    notify(err.message, "error");
  }
}

function setButtonLoading(btn, loading) {
  if (!btn) return;
  btn.disabled = loading;
  btn.classList.toggle("loading", loading);
}

/* ── INITIALIZATION ──────────────────────────────────────────────── */
(function init() {
  show("appShell");
  navigate("dashPage");
  initVisualSelectors();

  if (token) {
    loadUser()
      .then(() => {
        enterApp();
      })
      .catch(() => {
        token = "";
        sessionStorage.removeItem("nova_token");
        show("topbarSignUpBtn");
        hide("topbarAvatar");
      });
  } else {
    show("topbarSignUpBtn");
    hide("topbarAvatar");
  }

  // Periodic notifications polling
  setInterval(() => {
    if (token) loadNotifications();
  }, 25000);
})();
