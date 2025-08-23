// src/pages/ProjectCompleted.jsx
import React, { useEffect, useState } from "react";
import { useNavigate, useParams, useLocation } from "react-router-dom";
import MobileWrapper from "../components/MobileWrapper";
import { getCompletionMessage, submitFeedback } from "../services/feedback";

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
      <div className="min-h-screen bg-white">
        {/* Header */}
        <div className="sticky top-0 z-10 bg-white pt-5 pb-3 px-4">
          <div className="flex items-center justify-center relative">
            <h1 className="text-[16px] font-semibold">Project Completed</h1>
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
          <div className="flex justify-center mb-6">
            <div className="w-24 h-24 bg-gradient-to-br from-yellow-400 to-purple-500 rounded-full flex items-center justify-center">
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
          <div className="bg-gray-50 rounded-lg p-4 mb-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-3">Rating & Review</h3>

            {/* Star Rating */}
            <div className="flex justify-center mb-4">
              {[1,2,3,4,5].map((n) => (
                <button
                  key={n}
                  onClick={() => handleRatingClick(n)}
                  className={`text-2xl mx-1 transition-colors ${
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
              className="w-full p-3 border border-gray-300 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-green-500"
              rows={3}
            />
          </div>

          {/* Helper / Error */}
          <div className="space-y-2 mb-4">
            <p className="text-gray-600 text-center">
              If you need to go back and edit your steps, or revisit any parts you feel stuck on, we're here to help!
            </p>
            {error && (
              <div className="text-center text-red-600 text-sm">{error}</div>
            )}
          </div>

          {/* Go Back / Finish */}
          <div className="grid grid-cols-2 gap-3 mb-4">
            <button
              onClick={handleGoBack}
              className="py-3 px-4 border border-green-500 bg-white text-black rounded-lg font-medium hover:bg-gray-50"
            >
              Go back
            </button>
            <button
              onClick={handleFinish}
              disabled={saving}
              className={`py-3 px-4 text-white rounded-lg font-medium ${
                saving ? "bg-green-300" : "bg-green-600 hover:bg-green-700"
              }`}
            >
              {saving ? "Saving…" : "Finish"}
            </button>
          </div>

          {/* Share / All Projects */}
          <div className="grid grid-cols-2 gap-3 mb-3">
            <button
              onClick={handleShareSuccess}
              className="p-4 border border-gray-200 rounded-lg bg-white hover:bg-gray-50"
            >
              <div className="flex flex-col items-center">
                <span className="text-2xl mb-2">✅</span>
                <span className="font-medium text-gray-900">Share Success</span>
                <span className="text-sm text-gray-500">Show off your work</span>
              </div>
            </button>

            <button
              onClick={handleAllProjects}
              className="p-4 border border-gray-200 rounded-lg bg-white hover:bg-gray-50"
            >
              <div className="flex flex-col items-center">
                <span className="text-2xl mb-2">📁</span>
                <span className="font-medium text-gray-900">All Projects</span>
                <span className="text-sm text-gray-500">View history</span>
              </div>
            </button>
          </div>

          {/* Done */}
          <button
            onClick={handleDone}
            disabled={saving}
            className="w-full py-3 px-4 bg-gray-900 text-white rounded-lg font-medium hover:bg-gray-800"
          >
            {saving ? "Saving…" : "Done"}
          </button>
        </div>
      </div>
    </MobileWrapper>
  );
}