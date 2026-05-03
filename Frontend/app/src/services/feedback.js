// src/services/feedback.js
import { authHeaders, jsonAuthHeaders } from "./api";

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
  const res = await fetch(`${API}/projects/${encodeURIComponent(projectId)}/completion-message`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(await readErr(res));
  return res.json(); // { message: "..." }
}

export async function submitFeedback(projectId, { rating, comments, tags = [] }) {
  const res = await fetch(`${API}/projects/${encodeURIComponent(projectId)}/feedback`, {
    method: "POST",
    headers: jsonAuthHeaders(),
    body: JSON.stringify({ rating, comments, tags }),
  });
  if (!res.ok) throw new Error(await readErr(res));
  return res.json(); // { ok: true, averageRating, totalFeedback }
}
