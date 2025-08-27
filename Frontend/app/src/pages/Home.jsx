// src/pages/Home.jsx
import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import Header from "../components/Header";
import ProjectCard from "../components/ProjectCard";
import LoadingPlaceholder from "../components/LoadingPlaceholder";
import SideNavbar from "../components/SideNavbar";
import MobileWrapper from "../components/MobileWrapper";
import { fetchProjects, createProject, deleteProject } from "../services/projects";
import { getUserById } from "../services/auth";

export default function Home() {
  const navigate = useNavigate();
  const token =
    localStorage.getItem("authToken") ||
    sessionStorage.getItem("authToken");
  
  const [userName, setUserName] = useState(
    localStorage.getItem("displayName") ||
    sessionStorage.getItem("displayName") ||
    "User"
  );

  const [welcomeType, setWelcomeType] = useState("welcome"); // "welcome" or "welcome_back"
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showModal, setShowModal] = useState(false);
  const [projectName, setProjectName] = useState("");
  const [creating, setCreating] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  // Function to get first name with first letter capitalized
  // Extracts first name from "First Last" format and capitalizes first letter
  const getFirstName = (fullName) => {
    if (!fullName || fullName === "User") return "User";
    
    // Handle cases where there might be extra spaces or single name
    const trimmedName = fullName.trim();
    if (!trimmedName) return "User";
    
    const firstName = trimmedName.split(" ")[0];
    if (!firstName) return "User";
    
    // Capitalize first letter and make rest lowercase
    return firstName.charAt(0).toUpperCase() + firstName.slice(1).toLowerCase();
  };

  const openSidebar = () => setIsSidebarOpen(true);
  const closeSidebar = () => setIsSidebarOpen(false);

  useEffect(() => {
    if (!token) {
      navigate("/login", { replace: true });
      return;
    }

    // Check where user is coming from
    const isFromOnboarding = localStorage.getItem("fromOnboarding") === "true";
    const isFromLogin = localStorage.getItem("fromLogin") === "true";
    
    if (isFromOnboarding) {
      setWelcomeType("welcome");
      localStorage.removeItem("fromOnboarding"); // Clean up
    } else if (isFromLogin) {
      setWelcomeType("welcome_back");
      localStorage.removeItem("fromLogin"); // Clean up
    } else {
      // Default to welcome back for existing sessions
      setWelcomeType("welcome_back");
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

  function openModal() {
    setProjectName("");
    setShowModal(true);
  }

  function closeModal() {
    setShowModal(false);
  }

  const handleKeyDown = (e) => {
    if(e.key === 'Enter'){
      startProject();
    }
  };

  async function startProject() {
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
    } catch (err) {
      console.error("deleteProject:", err);
      // revert if delete failed
      setProjects(prev => {
        fetchProjects(token).then(setProjects).catch(() => {});
        return prev;
      });
      setError("Could not delete project: " + err.message);
    }
  }

  if (loading) return <LoadingPlaceholder />;

  return (
    <MobileWrapper>

      
      {/* Main Content Container */}
      <div className="flex-1 flex flex-col bg-white h-screen overflow-hidden relative">
        {/* Header */}
        <div className="p-4 border-b border-gray-100 flex-shrink-0">
          <div className="flex items-center justify-between">
            <h1 className="text-2xl font-bold text-gray-900">
              {welcomeType === "welcome" ? "Welcome" : "Welcome back"}, <span className="text-blue-600">{getFirstName(userName)}</span>
            </h1>
            <button 
              onClick={openSidebar}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <svg className="w-6 h-6 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
          </div>
        </div>

        {/* Error Message */}
        {error && (
          <div className="mx-6 mt-4 p-3 bg-red-50 border border-red-200 rounded-lg flex-shrink-0">
            <p className="text-sm text-red-700">{error}</p>
          </div>
        )}

        {/* Content Area - Takes remaining space with max height */}
        <div className="flex-1 px-6 py-6 overflow-hidden">
          {/* Ongoing Projects Section */}
          <h2 className="text-lg font-semibold text-gray-900 mb-6">Ongoing Projects</h2>
          
          {projects.length === 0 ? (
            <div className="text-center py-8">
              <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-3">
                <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                </svg>
              </div>
              <p className="text-gray-500 text-sm">You have no ongoing projects.</p>
            </div>
          ) : (
            <div className="space-y-4 overflow-y-auto h-full pr-2">
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
              ))}
            </div>
          )}
        </div>

        {/* Footer - Always at bottom */}
        <div className="flex-shrink-0 border-t border-gray-100 bg-white">
          <div className="p-4">
            <div className="text-center">
              <p className="text-base font-medium text-gray-700 mb-4">
                Need help solving household problem?
              </p>
              <button
                onClick={openModal}
                className="w-full bg-gray-200 hover:bg-gray-300 px-4 py-2 rounded-xl font-semibold text-gray-800 transition-colors flex items-center justify-center space-x-3"
              >
                <span className="text-2xl">+</span>
                <span>Start New Project</span>
              </button>
            </div>
          </div>
        </div>

        {/* Side Navigation Bar */}
        <SideNavbar 
          isOpen={isSidebarOpen} 
          onClose={closeSidebar} 
        />
      </div>

      {/* New Project Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl w-full max-w-xs p-4 shadow-xl">
            <h3 className="text-lg font-semibold text-gray-900 mb-3 text-center">
              New Project Name
            </h3>

            <input
              type="text"
              className="w-full border-2 border-blue-500 rounded-lg px-3 py-2 mb-4 focus:outline-none focus:border-blue-500 transition-colors text-sm"
              placeholder="Enter project name"
              value={projectName}
              onChange={(e) => setProjectName(e.target.value)}
              disabled={creating}
              onKeyDown={handleKeyDown}
            />

            <div className="flex space-x-2">
              <button
                className="flex-1 px-3 py-2 rounded-lg bg-gray-200 text-gray-700 font-medium hover:bg-gray-300 transition-colors text-sm"
                onClick={closeModal}
                disabled={creating}
              >
                Cancel
              </button>
              <button
                className={`flex-1 px-3 py-2 rounded-lg font-medium transition-colors text-sm ${
                  projectName.trim()
                    ? creating
                      ? "bg-blue-300 text-white cursor-wait"
                      : "bg-blue-600 text-white hover:bg-green-700"
                    : "bg-gray-200 text-gray-400 cursor-not-allowed"
                }`}
                onClick={startProject}
                onKeyDown={handleKeyDown}
                disabled={!projectName.trim() || creating}
              >
                {creating ? "Starting…" : "Start"}
              </button>
            </div>
          </div>
        </div>
      )}
    </MobileWrapper>
  );
}