// src/services/feedback.js
const API = process.env.REACT_APP_BASE_URL;

async function readErr(res) {
  try {
    const j = await res.json();
    return j?.detail || JSON.stringify(j);
  } catch {
    try { return await res.text(); } catch { return res.statusText; }
  }
}

export async function getCompletionMessage(projectId) {
  const res = await fetch(`${API}/projects/${encodeURIComponent(projectId)}/completion-message`);
  if (!res.ok) throw new Error(await readErr(res));
  return res.json(); // { message: "..." }
}

export async function submitFeedback(projectId, { rating, comments }) {
  const res = await fetch(`${API}/projects/${encodeURIComponent(projectId)}/feedback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ rating, comments }),
  });
  if (!res.ok) throw new Error(await readErr(res));
  return res.json(); // { ok: true, averageRating, totalFeedback }
}
