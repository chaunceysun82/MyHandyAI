// src/services/projects.js
import axios from "axios";
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
  try {
    const res = await axios.delete(`${API_BASE}/projects/${id}`, {
    });

    // Axios automatically throws on non-2xx, so if we get here, it's successful.
    return res.data;
  } catch (err) {
    // Extract error message safely
    const msg =
      err.response?.data?.detail ||
      err.response?.statusText ||
      err.message ||
      "Unknown error";

    throw new Error(msg);
  }
}



