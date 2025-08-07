// src/services/projects.js
const API_BASE = process.env.REACT_APP_API_BASE_URL || "";  



export async function fetchProjects(/* userId */) {
  // No-op → always return empty list for now
  return [];
}

/**
 * POST /projects
 * payload must include exactly { projectTitle, userId }
 * Returns the new project’s ID.
 */
export async function createProject(userId, projectTitle) {
  const res = await fetch(`${API_BASE}/projects`, {
    method:  "POST",
    headers: { "Content-Type": "application/json" },
    body:    JSON.stringify({ projectTitle, userId }),
  });

  if (!res.ok) {
    const errText = await res.text();
    throw new Error(errText || res.statusText);
  }

  
  const { id } = await res.json();
  return id;
}
