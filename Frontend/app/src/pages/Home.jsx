// src/pages/Home.jsx
import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import Header from "../components/Header";
import ProjectCard from "../components/ProjectCard";
import LoadingPlaceholder from "../components/LoadingPlaceholder";
import SideNavbar from "../components/SideNavbar";
import MobileWrapper from "../components/MobileWrapper";
import { fetchProjects, createProject, deleteProject, completeProject, updateProject } from "../services/projects";
import { getUserById } from "../services/auth";
import defaultHome from "../../src/assets/default-home.png";
import { ReactComponent as Filter } from '../../src/assets/Frame.svg';


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
  
  // New state for tabs, search, and filtering
  const [activeTab, setActiveTab] = useState("ongoing"); // "ongoing" or "completed"
  const [searchQuery, setSearchQuery] = useState("");
  const [showFilterMenu, setShowFilterMenu] = useState(false);
  
  // New state for completion confirmation
  const [showCompletionModal, setShowCompletionModal] = useState(false);
  const [projectToComplete, setProjectToComplete] = useState(null);
  const [isCompleting, setIsCompleting] = useState(false);
  
  // New state for rename functionality
  const [showRenameModal, setShowRenameModal] = useState(false);
  const [projectToRename, setProjectToRename] = useState(null);
  const [newProjectName, setNewProjectName] = useState("");
  const [isRenaming, setIsRenaming] = useState(false);

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

  // Get project counts for tabs
  const ongoingCount = projects.filter(p => p.percentComplete < 100).length;
  const completedCount = projects.filter(p => p.percentComplete >= 100).length;

  // Filter projects based on active tab and search query
  const filteredProjects = projects.filter(project => {
    // First filter by tab (ongoing vs completed)
    const isCompleted = project.percentComplete >= 100;
    const matchesTab = activeTab === "ongoing" ? !isCompleted : isCompleted;
    
    // Then filter by search query
    const matchesSearch = searchQuery === "" || 
      project.projectTitle.toLowerCase().includes(searchQuery.toLowerCase());
    
    return matchesTab && matchesSearch;
  });


  // Simple test - show first project progress
  if (projects.length > 0) {
    const firstProject = projects[0];
    console.log('Home: FIRST PROJECT TEST:', {
      title: firstProject.projectTitle,
      progress: firstProject.percentComplete,
      type: typeof firstProject.percentComplete,
      converted: Math.round(Number(firstProject.percentComplete) || 0)
    });
  }

  // Close filter menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (showFilterMenu && !event.target.closest('.filter-menu-container')) {
        setShowFilterMenu(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [showFilterMenu]);

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
        console.log('Home: fetchProjects result:', data);
        console.log('Home: First project data:', data[0]);
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

      /*Navigate to chat page with new project*/
      navigate("/chat", {state: {projectId: newProject._id, projectName: newProject.projectTitle, userId: token, userName: userName}});

    } catch (err) {
      console.error("createProject:", err);
      setError("Could not create project: " + err.message);
    } finally {
      setCreating(false);
    }
  }

  const handleRemoveProject = async (projectId) => {
    try {
      await deleteProject(projectId);
      setProjects(projects.filter(p => p._id !== projectId));
    } catch (error) {
      console.error("Error removing project:", error);
      setError("Failed to remove project. Please try again.");
    }
  };

  const handleCompleteProject = async (projectId) => {
    try {
      await completeProject(projectId);
      // Refresh projects to get updated progress
      const updatedProjects = await fetchProjects(token);
      setProjects(updatedProjects);
    } catch (error) {
      console.error("Error completing project:", error);
      setError("Failed to complete project. Please try again.");
    }
  };

  // Function to show rename modal
  const showRenameConfirmation = (project) => {
    setProjectToRename(project);
    setNewProjectName(project.projectTitle);
    setShowRenameModal(true);
  };

  // Function to handle project rename
  const handleRenameProject = async () => {
    if (!projectToRename || !newProjectName.trim()) {
      setError("Please enter a valid project name.");
      return;
    }

    setIsRenaming(true);
    try {
      await updateProject(projectToRename._id, { projectTitle: newProjectName.trim() });
      
      // Update the project in the local state
      setProjects(projects.map(p => 
        p._id === projectToRename._id 
          ? { ...p, projectTitle: newProjectName.trim() }
          : p
      ));
      
      setShowRenameModal(false);
      setProjectToRename(null);
      setNewProjectName("");
    } catch (error) {
      console.error("Error renaming project:", error);
      setError("Failed to rename project. Please try again.");
    } finally {
      setIsRenaming(false);
    }
  };

  // Function to close rename modal
  const closeRenameModal = () => {
    setShowRenameModal(false);
    setProjectToRename(null);
    setNewProjectName("");
  };

  // Function to show completion confirmation modal
  const showCompletionConfirmation = (project) => {
    setProjectToComplete(project);
    setShowCompletionModal(true);
  };

  // Function to confirm project completion
  const confirmProjectCompletion = async () => {
    if (!projectToComplete) return;
    
    setIsCompleting(true); // Start loading
    try {
      await completeProject(projectToComplete._id);
      // Refresh projects to get updated progress
      const updatedProjects = await fetchProjects(token);
      setProjects(updatedProjects);
      setShowCompletionModal(false);
      setProjectToComplete(null);
      
      // Show success message
      setError(""); // Clear any previous errors
      // You could add a success state here if you want to show success messages
      console.log(`Project "${projectToComplete.projectTitle}" completed successfully!`);
    } catch (error) {
      console.error("Error completing project:", error);
      setError("Failed to complete project. Please try again.");
    } finally {
      setIsCompleting(false); // End loading
    }
  };

  // Function to check if a project has steps generated
  const hasProjectSteps = (project) => {
    // Check if project has any meaningful data beyond just being created
    // Projects with steps usually have:
    // 1. Progress > 0 (meaning steps were generated and some were completed)
    // 2. Last activity (meaning user has interacted with the project)
    // 3. Or if it's a very new project that might not have steps yet
    
    // If project has progress > 0, it definitely has steps
    if (project.percentComplete > 0) {
      return true;
    }
    
    // If project has last activity, it likely has steps
    if (project.lastActivity) {
      return true;
    }
    
    // For very new projects (created but not yet processed), assume no steps
    // This prevents users from marking incomplete projects as complete
    return false;
  };

  if (loading) return <LoadingPlaceholder />;

  return (
    <MobileWrapper>

      
      {/* Main Content Container */}
      <div className="flex-1 flex flex-col bg-[#fffef6] h-screen overflow-hidden relative">
        {/* Header */}
        <div className="p-4 border-b border-gray-100 flex-shrink-0">
          <div className="flex items-center justify-between">
            <h1 className="text-[20px] font-regular text-[#000000]">
              {welcomeType === "welcome" ? "Welcome" : "Welcome back"}, <span className="text-black font-bold text-[20px]">{getFirstName(userName)}</span>
            </h1>
            <button 
              onClick={openSidebar}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <svg className="w-6 h-6 text-[#000000]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
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
          {/* Project Category Tabs */}
          <div className="flex mb-4">
            <button
              onClick={() => setActiveTab("ongoing")}
              className={`flex-1 py-1 px-4 rounded-l-[21.63px] text-[16px] font transition-colors border ${
                activeTab === "ongoing"
                  ? "bg-[#1484A3] text-white border-[#1484A3] font-medium"
                  : "bg-[#FFFFFF] text-[#000000] border-[#1484A3] font-regular"
              }`}
            >
              Ongoing 
            </button>
            <button
              onClick={() => setActiveTab("completed")}
              className={`flex-1 py-1 px-4 rounded-r-[21.63px] text-[16px] font transition-colors border ${
                activeTab === "completed"
                  ? "bg-[#1484A3] text-white border-[#1484A3] font-medium"
                  : "bg-[#FFFFFF] text-[#000000] border-[#1484A3] font-regular"
              }`}
            >
              Completed 
            </button>
          </div>

          {/* Search and Filter Bar */}
          <div className="flex items-center gap-3 mb-1">
            <div className="flex-1 relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <svg className="h-5 w-5 text-[#000000]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              </div>
              <input
                type="text"
                placeholder="Search for projects"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-1.5 bg-[#FFFFFF] border border-[#000000] rounded-[15px] font-light text-[12px] text-[#000000] placeholder-[#000000]"
              />
            </div>
            
            {/* Filter Button */}
            <div className="filter-menu-container relative">
              <button
                onClick={() => setShowFilterMenu(!showFilterMenu)}
                className="p-4 hover:bg-gray-100 transition-colors rounded-[15px] flex items-center justify-center"
              >
                {/* <svg className="h-5 w-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.707A1 1 0 013 7V4z" />
                </svg> */}
                <Filter className="h-5 w-5 text-gray-600" />
              </button>
              
              {/* Filter Menu Dropdown */}
              {showFilterMenu && (
                <div className="absolute right-0 top-full mt-2 w-48 bg-white rounded-lg shadow-lg border border-gray-200 z-10">
                  <div className="py-2">
                    <button
                      onClick={() => {
                        setSearchQuery("");
                        setShowFilterMenu(false);
                      }}
                      className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition-colors"
                    >
                      Clear Search
                    </button>
                    <button
                      onClick={() => {
                        setActiveTab("ongoing");
                        setShowFilterMenu(false);
                      }}
                      className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition-colors"
                    >
                      Show Ongoing Only
                    </button>
                    <button
                      onClick={() => {
                        setActiveTab("completed");
                        setShowFilterMenu(false);
                      }}
                      className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition-colors"
                    >
                      Show Completed Only
                    </button>
                    <button
                      onClick={() => {
                        setActiveTab("ongoing");
                        setSearchQuery("");
                        setShowFilterMenu(false);
                      }}
                      className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition-colors"
                    >
                      Reset All Filters
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Projects Section */}
          {/* <h2 className="text-lg font-semibold text-gray-900 mb-6">
            {activeTab === "ongoing" ? "Ongoing Projects" : "Completed Projects"}
          </h2> */}
          
          {filteredProjects.length === 0 ? (
            <div className="text-center py-12">
              {/* SVG Illustration */}
              <div className="w-32 h-24 mx-auto mb-6">
                <img 
                  src={defaultHome}
                  alt="No projects illustration" 
                  className="w-full h-full object-contain"
                />
              </div>
              
              {/* Main Heading */}
              <h3 className="text-xl font-bold text-gray-900 mb-3">
                No {activeTab === "ongoing" ? "Ongoing" : "Completed"} Project
              </h3>
              
              {/* Sub-text */}
              <p className="text-gray-600 text-sm leading-relaxed max-w-xs mx-auto">
                All caught up! Let MyHandyAI know if household issues need fixing
              </p>
            </div>
          ) : (
            <div className="space-y-4 overflow-y-auto h-full pr-2">
              {filteredProjects.map((p) => {
                console.log('Home: Rendering ProjectCard with data:', {
                  id: p._id,
                  title: p.projectTitle,
                  percentComplete: p.percentComplete,
                  fullProject: p
                });

                
                return (
                  <ProjectCard
                    key={p._id}
                    id={p._id}
                    projectTitle={p.projectTitle}
                    lastActivity={p.lastActivity}
                    percentComplete={p.percentComplete}
                    							onStartChat={() => navigate("/chat", {state: {projectId: p._id, projectName: p.projectTitle, userId: token, userName: userName}})}
                    onRemove={handleRemoveProject}
                    onComplete={() => showCompletionConfirmation(p)}
                    onRename={() => showRenameConfirmation(p)}
                    hasSteps={hasProjectSteps(p)}
                  />
                );
              })}
            </div>
          )}
        </div>

        {/* Footer - Always at bottom */}
        <div className="flex-shrink-0 border-gray-100 bg-[#fffef6]">
          <div className="p-4">
            <div className="text-left">
              <p className="text-base ml-1 font-medium text-[#000000] mb-4">
                Need help solving household problem!
              </p>
              <button
                onClick={openModal}
                className="w-full bg-[#1484A3] hover:bg-[#066580] px-4 py-1.5 rounded-[21.63px] text-[#FFFFFF] transition-colors flex items-center justify-center space-x-2"
                style={{
                  boxShadow: '0px 6px 12px 0px rgba(0, 0, 0, 0.1)',
                }}
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 25 25">
                  <path strokeLinecap="square" strokeWidth={2} d="M12 6v12M6 12h12" />
                </svg>
                <span className="text-[14px] font-medium" 
                >Start New Project</span>
              </button>
            </div>
          </div>
        </div>

        {/* Side Navigation Bar */}
        <SideNavbar 
          isOpen={isSidebarOpen} 
          onClose={closeSidebar} 
          onStartNewProject={openModal}
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

      {/* Project Completion Confirmation Modal */}
      {showCompletionModal && projectToComplete && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl w-full max-w-xs p-4 shadow-xl">
            <h3 className="text-lg font-semibold text-gray-900 mb-3 text-center">
              Complete Project
            </h3>
            
            <div className="text-center mb-4">
              <p className="text-sm text-gray-600 mb-2">
                Are you sure you want to mark this project as complete?
              </p>
              <p className="text-sm font-medium text-gray-800">
                "{projectToComplete.projectTitle}"
              </p>
              <p className="text-xs text-gray-500 mt-1">
                This will mark all steps as completed and move the project to completed status.
              </p>
            </div>

            <div className="flex space-x-2">
              <button
                className="flex-1 px-3 py-2 rounded-lg bg-gray-200 text-gray-700 font-medium hover:bg-gray-300 transition-colors text-sm"
                onClick={() => {
                  setShowCompletionModal(false);
                  setProjectToComplete(null);
                }}
              >
                Cancel
              </button>
              <button
                className="flex-1 px-3 py-2 rounded-lg bg-green-600 text-white font-medium hover:bg-green-700 transition-colors text-sm"
                onClick={confirmProjectCompletion}
                disabled={isCompleting}
              >
                {isCompleting ? "Completing..." : "Complete Project"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Project Rename Modal */}
      {showRenameModal && projectToRename && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl w-full max-w-xs p-4 shadow-xl">
            <h3 className="text-lg font-semibold text-gray-900 mb-3 text-center">
              Rename Project
            </h3>
            
            <div className="mb-4">
              <p className="text-sm text-gray-600 mb-3">
                Enter a new name for your project:
              </p>
              <input
                type="text"
                className="w-full border-2 border-blue-500 rounded-lg px-3 py-2 focus:outline-none focus:border-blue-500 transition-colors text-sm"
                placeholder="Enter new project name"
                value={newProjectName}
                onChange={(e) => setNewProjectName(e.target.value)}
                disabled={isRenaming}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && newProjectName.trim() && !isRenaming) {
                    handleRenameProject();
                  }
                }}
              />
            </div>

            <div className="flex space-x-2">
              <button
                className="flex-1 px-3 py-2 rounded-lg bg-gray-200 text-gray-700 font-medium hover:bg-gray-300 transition-colors text-sm"
                onClick={closeRenameModal}
                disabled={isRenaming}
              >
                Cancel
              </button>
              <button
                className={`flex-1 px-3 py-2 rounded-lg font-medium transition-colors text-sm ${
                  newProjectName.trim()
                    ? isRenaming
                      ? "bg-blue-300 text-white cursor-wait"
                      : "bg-blue-600 text-white hover:bg-blue-700"
                    : "bg-gray-200 text-gray-400 cursor-not-allowed"
                }`}
                onClick={handleRenameProject}
                disabled={!newProjectName.trim() || isRenaming}
              >
                {isRenaming ? "Renaming..." : "Rename"}
              </button>
            </div>
          </div>
        </div>
      )}
    </MobileWrapper>
  );
}