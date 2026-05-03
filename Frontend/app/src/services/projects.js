// src/services/projects.js
import { authHeaders, jsonAuthHeaders } from "./api";
const API_BASE = process.env.REACT_APP_BASE_URL ;

// Log the API base URL for debugging
console.log('🔍 projects.js: API_BASE URL:', API_BASE);
console.log('🔍 projects.js: Environment check:', {
  NODE_ENV: process.env.NODE_ENV,
  REACT_APP_BASE_URL: process.env.REACT_APP_BASE_URL
});

/** GET /projects?user_id=... -> { message, projects: [...] } */
export async function fetchProjects(userId) {
  const res = await fetch(`${API_BASE}/projects?user_id=${encodeURIComponent(userId)}`, {
    headers: authHeaders(),
  });

  
  if (res.status === 405) return [];

  if (!res.ok) {
    
    let msg = res.statusText;
    try { msg = (await res.json()).detail || msg; } catch {}
    throw new Error(msg);
  }

  const data = await res.json();
  // backend returns { message, projects }
  const projects = Array.isArray(data.projects) ? data.projects : [];
  
  console.log('🔍 fetchProjects: Raw projects from API:', projects);
  console.log('🔍 fetchProjects: Number of projects:', projects.length);
  
  // Test progress API with first project if available
  if (projects.length > 0) {
    const testProject = projects[0];
    console.log('🔍 fetchProjects: Testing progress API with first project:', testProject._id);
    try {
      const testProgress = await fetchProjectProgress(testProject._id);
      console.log('🔍 fetchProjects: Test progress API result:', testProgress);
    } catch (testError) {
      console.error('🔍 fetchProjects: Test progress API failed:', testError);
    }
  }
  
  // Fetch progress for each project
  const projectsWithProgress = await Promise.all(
    projects.map(async (project) => {
      try {
        console.log(`🔍 fetchProjects: Starting progress fetch for: ${project._id} - ${project.projectTitle}`);
        const progress = await fetchProjectProgress(project._id);
        console.log(`🔍 fetchProjects: Progress result for ${project.projectTitle}:`, progress);
        
        const projectWithProgress = {
          ...project,
          percentComplete: progress
        };
        
        console.log(`🔍 fetchProjects: Final project data for ${project.projectTitle}:`, {
          id: projectWithProgress._id,
          title: projectWithProgress.projectTitle,
          progress: projectWithProgress.percentComplete
        });
        
        return projectWithProgress;
      } catch (error) {
        console.error(`🔍 fetchProjects: Error fetching progress for project ${project._id}:`, error);
        console.error(`🔍 fetchProjects: Error details:`, {
          projectId: project._id,
          projectTitle: project.projectTitle,
          error: error.message,
          stack: error.stack
        });
        
        return {
          ...project,
          percentComplete: 0
        };
      }
    })
  );
  
  console.log('🔍 fetchProjects: FINAL RESULT - All projects with progress:', projectsWithProgress.map(p => ({
    id: p._id,
    title: p.projectTitle,
    progress: p.percentComplete,
    hasProgress: 'percentComplete' in p
  })));
  
  return projectsWithProgress;
}

/** Refresh progress for a single project */
export async function refreshProjectProgress(projectId) {
  try {
    const progress = await fetchProjectProgress(projectId);
    return progress;
  } catch (error) {
    console.error('Error refreshing project progress:', error);
    return 0;
  }
}

/** GET /generation/status/{project_id} -> { message: string } */
export async function fetchGenerationStatus(projectId) {
  const res = await fetch(`${API_BASE}/generation/status/${encodeURIComponent(projectId)}`, {
    headers: authHeaders(),
  });

  if (!res.ok) {
    let msg = res.statusText;
    try { msg = (await res.json()).detail || msg; } catch {}
    throw new Error(msg);
  }

  return res.json();
}

/** PUT /project/{project_id}/complete -> Mark entire project as complete */
export async function completeProject(projectId) {
  try {
    const res = await fetch(`${API_BASE}/project/${encodeURIComponent(projectId)}/complete`, {
      method: 'PUT',
      headers: jsonAuthHeaders()
    });
    
    if (!res.ok) {
      let msg = res.statusText;
      try { msg = (await res.json()).detail || msg; } catch {}
      throw new Error(msg);
    }
    
    const data = await res.json();
    console.log('Project completed successfully:', data);
    return data;
  } catch (error) {
    console.error('Error completing project:', error);
    throw error;
  }
}

/** POST /projects -> { id } */
export async function createProject(userId, projectTitle) {
  const res = await fetch(`${API_BASE}/projects`, {
    method: "POST",
    headers: jsonAuthHeaders(),
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
  const res = await fetch(`${API_BASE}/projects/${id}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  if (!res.ok) {
    let msg = res.statusText;
    try { msg = (await res.json()).detail || msg; } catch {}
    throw new Error(msg);
  }
}

/** PUT /projects/{project_id} -> Update project */
export async function updateProject(projectId, updateData) {
  try {
    const res = await fetch(`${API_BASE}/projects/${encodeURIComponent(projectId)}`, {
      method: 'PUT',
      headers: jsonAuthHeaders(),
      body: JSON.stringify(updateData)
    });
    
    if (!res.ok) {
      let msg = res.statusText;
      try { msg = (await res.json()).detail || msg; } catch {}
      throw new Error(msg);
    }
    
    const data = await res.json();
    console.log('Project updated successfully:', data);
    return data;
  } catch (error) {
    console.error('Error updating project:', error);
    throw error;
  }
}

/** GET /project/{project_id}/progress -> { progress: number } */
export async function fetchProjectProgress(projectId) {
  try {
    console.log(`🔍 fetchProjectProgress: Starting API call for project ${projectId}`);
    
    const res = await fetch(`${API_BASE}/project/${encodeURIComponent(projectId)}/progress`, {
      headers: authHeaders(),
    });
    
    if (!res.ok) {
      throw new Error(`API error: ${res.status}`);
    }
    
    const data = await res.json();
    console.log(`🔍 fetchProjectProgress: Raw API response:`, data);
    
    // Extract the progress value and convert to percentage
    const progressPercentage = Math.round(Number(data) * 100);
    
    console.log(`🔍 fetchProjectProgress: ${data} -> ${progressPercentage}%`);
    
    return progressPercentage;
  } catch (error) {
    console.error(`🔍 fetchProjectProgress: Error for project ${projectId}:`, error);
    return 0;
  }
}



