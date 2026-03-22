// Central API client — all fetch calls go through here
const BASE = "";  // Same origin (FastAPI serves the frontend)

export async function analyzeXml(file) {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${BASE}/api/analyze`, { method: "POST", body: form });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Analysis failed");
  }
  return res.json();
}

export async function listSessions() {
  const res = await fetch(`${BASE}/api/sessions`);
  if (!res.ok) throw new Error("Could not load sessions");
  return res.json();
}

export async function getSession(sessionId) {
  const res = await fetch(`${BASE}/api/sessions/${sessionId}`);
  if (!res.ok) throw new Error("Session not found");
  return res.json();
}

export async function deleteSession(sessionId) {
  const res = await fetch(`${BASE}/api/sessions/${sessionId}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Delete failed");
  return res.json();
}

export async function getChatHistory(sessionId) {
  const res = await fetch(`${BASE}/api/chat/history/${sessionId}`);
  if (!res.ok) throw new Error("Could not load history");
  return res.json();
}

/**
 * Send a chat message and stream the response.
 * onChunk(text) is called for each streamed chunk.
 * Returns the full response string when done.
 */
export async function sendChatMessage(sessionId, message, onChunk) {
  const res = await fetch(`${BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, message }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Chat failed");
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let fullText = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop();
    for (const line of lines) {
      if (!line.startsWith("data: ")) continue;
      try {
        const data = JSON.parse(line.slice(6));
        if (data.chunk) {
          fullText += data.chunk;
          onChunk(data.chunk);
        }
      } catch (_) {}
    }
  }
  return fullText;
}
