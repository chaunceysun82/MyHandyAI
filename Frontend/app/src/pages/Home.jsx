import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import Header from "../components/Header";
import ProjectCard from "../components/ProjectCard";
import LoadingPlaceholder from "../components/LoadingPlaceholder";
import { fetchProjects } from "../services/projects";

export default function Home() {
  const navigate = useNavigate();

  // treat authToken as userId
  const token =
    localStorage.getItem("authToken") ||
    sessionStorage.getItem("authToken");
  const userName = "User"; // or decode token to get real name

  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!token) {
      navigate("/login", { replace: true });
      return;
    }

    fetchProjects(token)
      .then((data) => {
        setProjects(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error("Error fetching projects:", err);
        // fallback if endpoint isn’t ready
        if (err.message.includes("Method Not Allowed")) {
          setProjects([]);
          setLoading(false);
        } else {
          setError(err.message);
          setLoading(false);
        }
      });
  }, [token, navigate]);

  function handleSignOut() {
    localStorage.removeItem("authToken");
    sessionStorage.removeItem("authToken");
    navigate("/login", { replace: true });
  }

  if (loading) return <LoadingPlaceholder />;
  if (error)
    return <div className="p-4 text-red-500">Error loading projects: {error}</div>;

  return (
    <div className="max-w-md mx-auto p-4">
      {/* Header with avatar, greeting, gear & sign-out */}
      <Header userName={userName} onSignOut={handleSignOut} />

      {/* Call to Action */}
      <p className="text-lg font-medium mb-2">
        Need help solving household problem?
      </p>
      <button
        className="w-full bg-gray-300 py-2 rounded-lg font-semibold mb-6 flex items-center justify-center"
        onClick={() => navigate("/chat")}
      >
        <span className="text-2xl mr-2">+</span> Start New Project
      </button>

      {/* Ongoing Projects Section */}
      <h2 className="text-xl font-semibold mb-2">Ongoing Projects</h2>
      {projects.length === 0 ? (
        <div className="text-gray-500">You have no ongoing projects.</div>
      ) : (
        <div className="space-y-2 overflow-y-auto" style={{ maxHeight: "60vh" }}>
          {projects.map((p) => (
            <ProjectCard
              key={p._id}
              id={p._id}
              projectTitle={p.projectTitle}
              projectImages={p.projectImages}
              lastActivity={p.lastActivity}
              percentComplete={p.percentComplete}
              onClick={() => navigate(`/projects/${p._id}`)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
