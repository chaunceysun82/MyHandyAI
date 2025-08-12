// src/services/projects.js
const API_BASE = process.env.REACT_APP_BASE_URL ;

/** GET /projects?user_id=... -> { message, projects: [...] } */
export async function fetchProjects(userId) {
  const res = await fetch(`${API_BASE}/projects?user_id=${encodeURIComponent(userId)}`);

  
  if (res.status === 405) return [];

  if (!res.ok) {
    
    let msg = res.statusText;
    try { msg = (await res.json()).detail || msg; } catch {}
    throw new Error(msg);
  }

  const data = await res.json();
  // backend returns { message, projects }
  return Array.isArray(data.projects) ? data.projects : [];
}

/** POST /projects -> { id } */
export async function createProject(userId, projectTitle) {
  const res = await fetch(`${API_BASE}/projects`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ projectTitle, userId }),
  });

  if (!res.ok) {
    let msg = res.statusText;
    try { msg = (await res.json()).detail || msg; } catch {}
    throw new Error(msg);
  }

  const { id } = await res.json();
  return id;
}


export async function deleteProject(id) {
  const res = await fetch(`${API_BASE}/projects/${id}`, { method: "DELETE" });
  if (!res.ok) {
    let msg = res.statusText;
    try { msg = (await res.json()).detail || msg; } catch {}
    throw new Error(msg);
  }
}


