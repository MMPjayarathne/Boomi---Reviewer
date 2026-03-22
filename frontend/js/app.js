import { analyzeXml, listSessions, getSession, deleteSession, sendChatMessage, getChatHistory } from "./api.js";

// ── State ──────────────────────────────────────
let currentSessionId = null;
let currentFindings = [];
let isSending = false;

// ── DOM references ─────────────────────────────
const uploadZone = document.getElementById("upload-zone");
const fileInput = document.getElementById("file-input");
const sessionList = document.getElementById("session-list");
const welcomeScreen = document.getElementById("welcome-screen");
const analysisView = document.getElementById("analysis-view");
const loadingOverlay = document.getElementById("loading-overlay");
const loadingText = document.getElementById("loading-text");
const processNameDisplay = document.getElementById("process-name-display");
const cachedBadge = document.getElementById("cached-badge");
const summaryBadges = document.getElementById("summary-badges");
const findingsList = document.getElementById("findings-list");
const findingsSearch = document.getElementById("findings-search");
const chatMessages = document.getElementById("chat-messages");
const chatInput = document.getElementById("chat-input");
const chatSendBtn = document.getElementById("chat-send-btn");

// ── Utility ────────────────────────────────────
function showLoading(msg = "Analyzing process...") {
  loadingText.textContent = msg;
  loadingOverlay.classList.remove("hidden");
}

function hideLoading() {
  loadingOverlay.classList.add("hidden");
}

function showAnalysis() {
  welcomeScreen.classList.add("hidden");
  analysisView.classList.remove("hidden");
}

function showWelcome() {
  welcomeScreen.classList.remove("hidden");
  analysisView.classList.add("hidden");
}

function formatDate(iso) {
  const d = new Date(iso);
  return d.toLocaleDateString() + " " + d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

// ── Upload ─────────────────────────────────────
uploadZone.addEventListener("click", () => fileInput.click());

fileInput.addEventListener("change", (e) => {
  const file = e.target.files[0];
  if (file) handleUpload(file);
  fileInput.value = "";
});

uploadZone.addEventListener("dragover", (e) => {
  e.preventDefault();
  uploadZone.classList.add("drag-over");
});

uploadZone.addEventListener("dragleave", () => uploadZone.classList.remove("drag-over"));

uploadZone.addEventListener("drop", (e) => {
  e.preventDefault();
  uploadZone.classList.remove("drag-over");
  const file = e.dataTransfer.files[0];
  if (file && file.name.endsWith(".xml")) handleUpload(file);
  else alert("Please drop a .xml file.");
});

async function handleUpload(file) {
  showLoading(`Analyzing ${file.name}...`);
  try {
    const result = await analyzeXml(file);
    await loadSession(result.session_id, result);
    await refreshSessionList();
  } catch (err) {
    alert(`Error: ${err.message}`);
  } finally {
    hideLoading();
  }
}

// ── Session List ───────────────────────────────
async function refreshSessionList() {
  try {
    const sessions = await listSessions();
    sessionList.innerHTML = sessions.length
      ? sessions.map(s => {
          const summary = typeof s.summary === "string" ? JSON.parse(s.summary || "{}") : (s.summary || {});
          const critCount = summary.CRITICAL || 0;
          const highCount = summary.HIGH || 0;
          const fileLabel = escapeHtml(s.filename || "process.xml");
          const processLabel = escapeHtml(s.name || "Unnamed process");
          return `
            <div class="session-item ${s.id === currentSessionId ? "active" : ""}">
              <button type="button" class="session-item-info" data-id="${s.id}"
                title="Open this analysis"
                aria-label="Open analysis ${fileLabel}">
                <div class="session-file">${fileLabel}</div>
                <div class="session-process">${processLabel}</div>
                <div class="session-meta">
                  ${formatDate(s.created_at)}
                  ${critCount ? `<span style="color:var(--critical)"> · ${critCount} CRIT</span>` : ""}
                  ${highCount ? `<span style="color:var(--high)"> · ${highCount} HIGH</span>` : ""}
                </div>
              </button>
              <button type="button" class="session-item-remove" data-id="${s.id}"
                title="Remove this file from cache"
                aria-label="Remove ${fileLabel} from cache">Remove</button>
            </div>`;
        }).join("")
      : "<div style='padding:16px;color:var(--text-muted);font-size:12px'>No analyses yet</div>";
  } catch (_) {}
}

function resetToWelcomeAfterClear() {
  currentSessionId = null;
  currentFindings = [];
  showWelcome();
}

sessionList.addEventListener("click", async (e) => {
  const removeBtn = e.target.closest(".session-item-remove");
  if (removeBtn) {
    e.preventDefault();
    const id = removeBtn.dataset.id;
    const row = removeBtn.closest(".session-item");
    const fileEl = row?.querySelector(".session-file");
    const label = fileEl?.textContent?.trim() || "this file";
    if (!id || !confirm(`Remove “${label}” from cache? You can upload the XML again later.`)) return;
    try {
      await deleteSession(id);
      if (currentSessionId === id) {
        resetToWelcomeAfterClear();
      }
      await refreshSessionList();
    } catch (err) {
      alert(`Error: ${err.message}`);
    }
    return;
  }

  const openBtn = e.target.closest(".session-item-info");
  if (!openBtn) return;
  const id = openBtn.dataset.id;
  showLoading("Loading session...");
  try {
    const session = await getSession(id);
    await loadSession(id, {
      session_id: id,
      process_name: session.name,
      cached: true,
      summary: typeof session.summary === "string" ? JSON.parse(session.summary || "{}") : session.summary,
      findings: session.findings,
    });
  } catch (err) {
    alert(`Error: ${err.message}`);
  } finally {
    hideLoading();
  }
});

// ── Findings (API may return DB rows; normalize for UI) ──
function normalizeFindings(raw) {
  if (!raw || !Array.isArray(raw)) return [];
  return raw.map((f) => ({
    rule_id: f.rule_id ?? "",
    rule_name: f.rule_name ?? "",
    severity: String(f.severity ?? "INFO").toUpperCase(),
    shape_id: f.shape_id ?? "",
    shape_label: f.shape_label ?? "",
    description: f.description ?? "",
    recommendation: f.recommendation ?? "",
  }));
}

// ── Load Session ───────────────────────────────
async function loadSession(sessionId, data) {
  currentSessionId = sessionId;
  if (findingsSearch) findingsSearch.value = "";
  currentFindings = normalizeFindings(data.findings);

  // Header
  processNameDisplay.textContent = data.process_name;
  cachedBadge.classList.toggle("hidden", !data.cached);

  // Summary badges
  const severityOrder = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"];
  const colorMap = { CRITICAL: "critical", HIGH: "high", MEDIUM: "medium", LOW: "low", INFO: "info" };
  summaryBadges.innerHTML = severityOrder
    .filter(s => (data.summary || {})[s])
    .map(s => `<span class="badge badge-${colorMap[s]}">${(data.summary || {})[s]} ${s}</span>`)
    .join("");

  // Findings
  renderFindings(currentFindings);

  // Chat history
  await loadChatHistory(sessionId);

  showAnalysis();
  await refreshSessionList();
}

// ── Findings ───────────────────────────────────
function renderFindings(findings) {
  if (!findings.length) {
    findingsList.innerHTML = `
      <div style="padding:24px;text-align:center;color:var(--text-muted)">
        ✅ No issues found
      </div>`;
    return;
  }

  const query = (findingsSearch.value || "").toLowerCase();
  const filtered = query
    ? findings.filter(f =>
        (f.description || "").toLowerCase().includes(query) ||
        (f.rule_name || "").toLowerCase().includes(query) ||
        (f.severity || "").toLowerCase().includes(query) ||
        (f.shape_label || "").toLowerCase().includes(query)
      )
    : findings;

  // Sort by severity weight
  const sevWeight = { CRITICAL: 5, HIGH: 4, MEDIUM: 3, LOW: 2, INFO: 1 };
  const sorted = [...filtered].sort((a, b) => (sevWeight[b.severity] || 0) - (sevWeight[a.severity] || 0));

  findingsList.innerHTML = sorted.map(f => `
    <div class="finding-card sev-${f.severity}" data-rule="${f.rule_id}">
      <div class="finding-top">
        <span class="finding-rule-id">${f.rule_id}</span>
        <span class="finding-title">${f.rule_name}</span>
        <span class="badge badge-${f.severity.toLowerCase()}">${f.severity}</span>
      </div>
      <div class="finding-desc">${escapeHtml(f.description || "")}</div>
      ${f.shape_id ? `<div class="finding-shape">📌 ${f.shape_label || f.shape_id}</div>` : ""}
    </div>
  `).join("");
}

findingsSearch.addEventListener("input", () => renderFindings(currentFindings));

// Click on finding → ask AI about it
findingsList.addEventListener("click", (e) => {
  const card = e.target.closest(".finding-card");
  if (!card) return;
  const ruleId = card.dataset.rule;
  const f = currentFindings.find(x => x.rule_id === ruleId);
  if (f) {
    chatInput.value = `Explain issue [${f.rule_id}]: "${f.description}" — what is the root cause and how do I fix it?`;
    chatInput.focus();
  }
});

// ── Chat ───────────────────────────────────────
async function loadChatHistory(sessionId) {
  chatMessages.innerHTML = "";
  try {
    const history = await getChatHistory(sessionId);
    for (const msg of history) {
      appendMessage(msg.role, msg.content);
    }
    if (!history.length) {
      appendSystemHint();
    }
  } catch (_) {
    appendSystemHint();
  }
  scrollChatBottom();
}

function appendSystemHint() {
  chatMessages.innerHTML = `
    <div style="text-align:center;color:var(--text-muted);font-size:12px;margin-top:24px">
      🤖 Ask anything about this Boomi process.<br/>
      Click on a finding to get an instant explanation.
    </div>`;
}

function appendMessage(role, content) {
  const div = document.createElement("div");
  div.className = `chat-msg ${role}`;
  div.innerHTML = `
    <div class="chat-role">${role === "user" ? "You" : "AI Copilot"}</div>
    <div class="chat-bubble">${escapeHtml(content)}</div>
  `;
  chatMessages.appendChild(div);
  return div;
}

function appendStreamingMessage() {
  const div = document.createElement("div");
  div.className = "chat-msg assistant";
  div.innerHTML = `
    <div class="chat-role">AI Copilot</div>
    <div class="chat-bubble"></div>
  `;
  chatMessages.appendChild(div);
  return div.querySelector(".chat-bubble");
}

function scrollChatBottom() {
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function escapeHtml(text) {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/`(.+?)`/g, "<code>$1</code>")
    .replace(/^### (.+)$/gm, "<h3>$1</h3>")
    .replace(/^- (.+)$/gm, "<li>$1</li>")
    .replace(/(<li>.*<\/li>)/s, "<ul>$1</ul>");
}

async function sendMessage() {
  const message = chatInput.value.trim();
  if (!message || isSending) return;
  if (!currentSessionId) {
    alert("Please upload a process.xml first.");
    return;
  }

  isSending = true;
  chatSendBtn.disabled = true;
  chatInput.disabled = true;

  // Show user message
  appendMessage("user", message);
  chatInput.value = "";
  scrollChatBottom();

  // Streaming assistant bubble
  const bubble = appendStreamingMessage();
  bubble.textContent = "▌";
  scrollChatBottom();

  try {
    let fullText = "";
    await sendChatMessage(currentSessionId, message, (chunk) => {
      fullText += chunk;
      bubble.innerHTML = escapeHtml(fullText) + "▌";
      scrollChatBottom();
    });
    bubble.innerHTML = escapeHtml(fullText);
  } catch (err) {
    bubble.textContent = `Error: ${err.message}`;
  } finally {
    isSending = false;
    chatSendBtn.disabled = false;
    chatInput.disabled = false;
    chatInput.focus();
    scrollChatBottom();
  }
}

chatSendBtn.addEventListener("click", sendMessage);

chatInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

// Suggestion chips
document.querySelectorAll(".suggestion").forEach(btn => {
  btn.addEventListener("click", () => {
    chatInput.value = btn.dataset.q;
    sendMessage();
  });
});

// ── Init ───────────────────────────────────────
(async () => {
  await refreshSessionList();
})();
