// src/pages/ProjectCompleted.jsx
import React, { useEffect, useState } from "react";
import { useNavigate, useParams, useLocation } from "react-router-dom";
import MobileWrapper from "../components/MobileWrapper";
import { getCompletionMessage, submitFeedback } from "../services/feedback";
import { ReactComponent as ShareSuccess } from '../assets/share_success.svg';
import { ReactComponent as AllProjects } from '../assets/all_projects.svg';

export default function ProjectCompleted() {
  const navigate = useNavigate();
  const params = useParams();
  const projectId = params.projectId || params.id;
  const { state } = useLocation();
  const projectName = state?.projectName || "Project";

  const [rating, setRating] = useState(0);
  const [feedback, setFeedback] = useState("");
  const [loadingMsg, setLoadingMsg] = useState(true);
  const [completionMsg, setCompletionMsg] = useState(
    `All done! Your ${projectName.toLowerCase()} should be installed and looking great.`
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  
  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const { message } = await getCompletionMessage(projectId);
        if (alive && message) setCompletionMsg(message);
      } catch (e) {
        // keep fallback text; no hard error
        console.warn("completion-message:", e?.message || e);
      } finally {
        if (alive) setLoadingMsg(false);
      }
    })();
    return () => { alive = false; };
  }, [projectId]);

  const handleClose = () => navigate("/home");
  const handleGoBack = () => {
    // Navigate back to Project Overview, preserving any existing state
    navigate(`/projects/${projectId}/overview`, {
      state: {
        projectId,
        projectName: projectName || "Project",
        ...state // Pass through any existing state including projectVideoUrl if it exists
      }
    });
  };

  // Send feedback to backend using the same API service
  async function saveFeedbackAndGo(target = "/home") {
    if (!rating) {
      setError("Please select a rating before continuing.");
      return;
    }
    setError("");
    setSaving(true);
    try {
      await submitFeedback(projectId, { rating, comments: feedback.trim() });
      navigate(target);
    } catch (e) {
      setError(e.message || "Could not save feedback.");
    } finally {
      setSaving(false);
    }
  }

  const handleFinish = () => saveFeedbackAndGo("/home");
  const handleDone   = () => saveFeedbackAndGo("/home");

  const handleShareSuccess = () =>
    alert("(Placeholder) Share to social / copy link");

  const handleAllProjects = () => navigate("/home");

  const handleRatingClick = (n) => setRating(n);

  return (
    <MobileWrapper>
      <div className="min-h-screen bg-[#fffef6]">
        {/* Header */}
        <div className="sticky top-0 z-10 bg-white pt-3 pb-1 px-4">
          <div className="flex items-center justify-center relative">
            <h1 className="text-[18px] font-semibold">Project Completed</h1>
            <button
              aria-label="Close"
              onClick={handleClose}
              className="absolute right-0 text-xl leading-none px-2 py-1 rounded hover:bg-gray-100"
            >
              ×
            </button>
          </div>
        </div>

        {/* Main Content */}
        <div className="flex-1 px-4 py-6">
          {/* Celebration Icon */}
          <div className="flex justify-center mb-4">
            <div className="w-24 h-24 rounded-full flex items-center justify-center" style={{backgroundColor: '#E3F2FD'}}>
              <span className="text-4xl">🎉</span>
            </div>
          </div>

          {/* Congratulations Text */}
          <div className="text-center mb-8">
            <h2 className="text-2xl font-bold text-gray-900 mb-2">Congratulations!</h2>
            <p className="text-gray-600">
              {loadingMsg ? "Finishing up…" : completionMsg}
            </p>
          </div>

          {/* Rating & Review Section */}
          <div className="rounded-lg border-l-2 border-[#1484A3] p-4 mb-4 shadow-md" style={{backgroundColor: '#ffffff'}}>
            <h3 className="text-lg font-semibold text-center text-gray-900 mb-1">Rating & Review</h3>

            {/* Star Rating */}
            <div className="flex justify-center mb-2">
              {[1,2,3,4,5].map((n) => (
                <button
                  key={n}
                  onClick={() => handleRatingClick(n)}
                  className={`text-2xl mx-1 transition-colors hover:scale-110 ${
                    n <= rating ? "text-yellow-400" : "text-gray-300"
                  }`}
                  aria-label={`Rate ${n} star${n>1?"s":""}`}
                >
                  ★
                </button>
              ))}
            </div>

            <p className="text-center text-gray-600 mb-3">
              How was your experience fixing this issue?
            </p>

            {/* Feedback Input */}
            <textarea
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
              placeholder="Write us a feedback..."
              className="w-full p-3 border border-gray-300 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 shadow-sm"
              rows={2}
            />
          </div>

          {/* Helper Text & Navigation */}
          <div className="rounded-lg border-l-2 border-[#1484A3] px-4 py-2 mb-4 bg-white shadow-md">
            <p className="text-gray-600 text-center text-sm mb-4">
              If you need to go back and edit your steps, or revisit any parts you feel stuck on, we're here to help!
            </p>
            {error && (
              <div className="text-center text-red-600 text-sm mb-4">{error}</div>
            )}
            
            {/* Go Back / Finish */}
            <div className="grid grid-cols-2 gap-3">
              <button
                onClick={handleGoBack}
                className="py-3 px-4 border border-gray-300 bg-white text-gray-900 rounded-lg font-medium hover:bg-gray-50 shadow-sm hover:shadow-md transition-shadow"
              >
                Go back
              </button>
              <button
                onClick={handleFinish}
                disabled={saving}
                className={`py-3 px-4 rounded-lg font-medium shadow-sm hover:shadow-md transition-shadow ${
                  saving ? "bg-[#E9FAFF]" : "bg-[#E9FAFF] hover:bg-[#D1F2FF]"
                }`}
              >
                {saving ? "Saving…" : "Finish"}
              </button>
            </div>
          </div>

          {/* Share / All Projects */}
          <div className="grid grid-cols-2 gap-3 mb-4">
            <button
              onClick={handleShareSuccess}
              className="p-2 border border-gray-200 rounded-lg bg-[#E9FAFF] hover:bg-gray-50 shadow-sm hover:shadow-md transition-shadow"
            >
              <div className="flex flex-col items-center">
                <div className="w-8 h-8 mb-1 flex items-center justify-center">
                  <ShareSuccess className="w-6 h-6" />
                </div>
                <span className="font-medium text-gray-900">Share Success</span>
                <span className="text-sm text-gray-500">Show off your work</span>
              </div>
            </button>

            <button
              onClick={handleAllProjects}
              className="p-2 border border-gray-200 rounded-lg bg-[#E9FAFF] hover:bg-gray-50 shadow-sm hover:shadow-md transition-shadow"
            >
              <div className="flex flex-col items-center">
                <div className="w-8 h-8 mb-1 flex items-center justify-center">
                  <AllProjects className="w-6 h-6" />
                </div>
                <span className="font-medium text-gray-900">All Projects</span>
                <span className="text-sm text-gray-500">View history</span>
              </div>
            </button>
          </div>

          {/* Start New Project */}
          <button
            onClick={() => navigate("/home")}
            className="w-full py-3 px-4 text-white rounded-xl font-medium hover:opacity-90 shadow-md hover:shadow-lg transition-shadow"
            style={{backgroundColor: '#1484A3'}}
          >
            Start New Project
          </button>
        </div>
      </div>
    </MobileWrapper>
  );
}