// src/services/projects.js
const API_BASE = process.env.REACT_APP_API_BASE_URL || "";

export async function fetchProjects(userId) {
  const url = `${API_BASE}/projects?user_id=${userId}`;
  const res = await fetch(url);

  // FastAPI: you only have a POST on /projects, so GET /projects → 405
  if (res.status === 405) {
    // treat as "no projects yet"
    return [];
  }

  if (!res.ok) {
    // any other problem, surface it
    const text = await res.text();
    throw new Error(text);
  }

  return res.json();
}
