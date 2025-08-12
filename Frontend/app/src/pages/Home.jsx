// src/pages/Home.jsx
import React, { useEffect, useState } from "react";
import { useNavigate }               from "react-router-dom";
import Header                         from "../components/Header";
import ProjectCard                    from "../components/ProjectCard";
import LoadingPlaceholder             from "../components/LoadingPlaceholder";
import { fetchProjects, createProject, deleteProject } from "../services/projects";
import { getUserById } from "../services/auth";


export default function Home() {
  const navigate = useNavigate();
  const token    =
    localStorage.getItem("authToken") ||
    sessionStorage.getItem("authToken");
  
    const [userName, setUserName] = useState(
    localStorage.getItem("displayName") ||
    sessionStorage.getItem("displayName") ||
    "User"
  );

  // const projectsKey = `${token}`;

  const [projects, setProjects] = useState([]);


  const [loading,  setLoading ]     = useState(true);
  const [error,    setError   ]     = useState("");
  const [showModal, setShowModal]   = useState(false);
  const [projectName, setProjectName] = useState("");
  const [creating, setCreating]     = useState(false);

  
  useEffect(() => {
    if (!token) {
      navigate("/login", { replace: true });
      return;
    }
    if (!localStorage.getItem("displayName") &&
       !sessionStorage.getItem("displayName")) {
     getUserById(token).then(u => {
       const full = [u.firstname, u.lastname].filter(Boolean).join(" ") || (u.email ?? "User");
       setUserName(full);
       const store = localStorage.getItem("authToken") ? localStorage : sessionStorage;
       store.setItem("displayName", full);
     }).catch(() => {}); // ignore for Google-only ids
    }

    fetchProjects(token)
      .then(data => {
        setProjects(data);
        setLoading(false);
      })
      .catch(err => {
        console.error("fetchProjects:", err);
        setError(err.message);
        setLoading(false);
      });
  }, [token, navigate]);

  function handleSignOut() {
    localStorage.removeItem("authToken");
    sessionStorage.removeItem("authToken");

    localStorage.removeItem(`chatMessages`);
    localStorage.removeItem("introShown");
    localStorage.removeItem("displayName");
    sessionStorage.removeItem("displayName");

    navigate("/login", { replace: true });
  }

  function openModal() {
    setProjectName("");
    setShowModal(true);
  }

  function closeModal() {
    setShowModal(false);
  }

  // async function startProject() 
  // {
  //   const name = projectName.trim();
  //   if (!name) return;

  //   setCreating(true);
  //   setError("");
  //   try {
  //     // call POST /projects
  //     console.log("Token:", token);
  //     const newId = await createProject(token, name);

      
  //     // fetchProjects(token).then(setProjects).catch(console.error);

  //     setShowModal(false);

  //     navigate("/chat", { state: { projectId: newId, projectName: name } });
  //   } catch (err) {
  //     console.error("createProject:", err);
  //     setError("Could not create project: " + err.message);
  //   } finally {
  //     setCreating(false);
  //   }
  // }

  async function startProject() 
  {
    const name = projectName.trim();
    if (!name) return;

    setCreating(true);
    setError("");
    try {
      const newId = await createProject(token, name);

      const newProject = {
        _id: newId,
        projectTitle: name,
        lastActivity: null,
        percentComplete: 0,
        projectImages: [],
      };

      setProjects((prev) => {
        const updated = [newProject, ...prev];
        // localStorage.setItem(projectsKey, JSON.stringify(updated));
        return updated;
      });

      setShowModal(false);

    } catch (err) {
      console.error("createProject:", err);
      setError("Could not create project: " + err.message);
    } finally {
      setCreating(false);
    }
  }

  async function handleRemoveProject(id) {
  try {
    // optimistic UI: remove first
    setProjects(prev => prev.filter(p => p._id !== id));

    await deleteProject(id);
    // (optional) toast/snackbar here
  } catch (err) {
    console.error("deleteProject:", err);
    // revert if delete failed
    setProjects(prev => {
      // you might keep a copy to restore; simplest is to refetch
      fetchProjects(token).then(setProjects).catch(() => {});
      return prev;
    });
    setError("Could not delete project: " + err.message);
  }
}


  if (loading) return <LoadingPlaceholder />;

  return (
    <div className="min-h-screen flex flex-col items-center p-4">
      
      {error && (
        <div className="mb-4 p-2 bg-red-100 text-red-700 rounded">
          {error}
        </div>
      )}

      {/* Header */}
	  <div className="w-full max-w-md">
      <Header userName={userName} onSignOut={handleSignOut} />
	  </div>

	  <div className="w-full max-w-md flex flex-col items-center">

      {/* CTA */}
      <p className="text-lg font-medium mb-2">
        Need help solving household problem?
      </p>
      <button
        className="w-full bg-gray-300 py-2 rounded-lg font-semibold mb-6 flex items-center justify-center"
        onClick={openModal}
      >
        <span className="text-2xl mr-2">+</span> Start New Project
      </button>

      {/* Ongoing Projects */}
      <h2 className="text-xl font-semibold mb-2">Ongoing Projects</h2>
      {projects.length === 0 ? (
        <div className="text-gray-500">You have no ongoing projects.</div>
      ) : (
        <div
          className="space-y-2 overflow-y-auto"
          style={{ maxHeight: "60vh" }}
        >
          {projects.map((p) => (
            <ProjectCard
              key={p._id}
              id={p._id}
              projectTitle={p.projectTitle}
              lastActivity={p.lastActivity}
              percentComplete={p.percentComplete}
              onStartChat={() => navigate("/chat", {state: {projectId: p._id, projectName: p.projectTitle, userId: token}})}
              onRemove={handleRemoveProject}
            />
            // <div
            //   key={p._id}
            //   className="border rounded-lg p-4 bg-white shadow flex justify-between items-center"
            // >
            //   <div>
            //     <h3 className="text-lg font-semibold">{p.projectTitle}</h3>
            //     <p className="text-sm text-gray-500">Last Activity: {p.lastActivity || "N/A"}</p>
            //     <p className="text-sm text-gray-500">Progress: {p.percentComplete || 0}%</p>
            //   </div>

            //   <div className="flex flex-col ml-20 space-y-2">
            //     <button
            //       className="bg-blue-600 text-white px-3 py-1 rounded text-sm"
            //       onClick={() =>
            //         navigate("/chat", {
            //           state: {
            //             projectId: p._id,
            //             projectName: p.projectTitle,
            //           },
            //         })
            //       }
            //     >
            //       Start Chat
            //     </button>

            //     <button
            //       className="bg-gray-300 text-black px-3 py-1 rounded text-sm"
            //       onClick={() => alert("Remove clicked (placeholder)")}
            //     >
            //       Remove
            //     </button>
            //   </div>
            // </div>
          ))}
        </div>
		
      )}
	  </div>
      {/* Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-40 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg w-11/12 max-w-sm p-6">
            <h3 className="text-lg font-semibold mb-4">
              New Project Name
            </h3>

            <input
              type="text"
              className="w-full border border-gray-300 rounded px-3 py-2 mb-4 focus:outline-none"
              placeholder="Enter project name"
              value={projectName}
              onChange={(e) => setProjectName(e.target.value)}
              disabled={creating}
            />

            <div className="flex justify-end space-x-3">
              <button
                className="px-4 py-2 rounded bg-gray-200"
                onClick={closeModal}
                disabled={creating}
              >
                Cancel
              </button>
              <button
                className={
                  "px-4 py-2 rounded font-semibold " +
                  (projectName.trim()
                    ? creating
                      ? "bg-blue-300 text-white cursor-wait"
                      : "bg-blue-600 text-white"
                    : "bg-blue-200 text-blue-600 cursor-not-allowed")
                }
                onClick={startProject}
                disabled={!projectName.trim() || creating}
              >
                {creating ? "Starting…" : "Start"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}