// src/pages/Feedback.jsx
import React, { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { getCompletionMessage, submitFeedback } from "../services/feedback";

export default function Feedback() {
  const navigate = useNavigate();
  const { id: projectId } = useParams();

  const [loading, setLoading]   = useState(true);
  const [apiMsg, setApiMsg]     = useState("All done! Your project looks great.");
  const [rating, setRating]     = useState(0);
  const [hover, setHover]       = useState(0);
  const [comments, setComments] = useState("");
  const [error, setError]       = useState("");
  const [saving, setSaving]     = useState(false);

  useEffect(() => {
    let alive = true;
    (async () => {
      setError("");
      setLoading(true);
      try {
        const { message } = await getCompletionMessage(projectId);
        if (alive) setApiMsg(message || apiMsg);
      } catch (e) {
        console.warn("completion-message:", e);
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => { alive = false; };
  }, [projectId]);

  const onFinish = async () => {
    if (!rating) {
      setError("Please select a rating.");
      return;
    }
    setError("");
    setSaving(true);
    try {
      await submitFeedback(projectId, { rating, comments });
      navigate("/home"); // or a “All Projects” page
    } catch (e) {
      setError(e.message || "Could not save feedback.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="min-h-screen flex justify-center bg-white">
      <div className="w-full max-w-md px-4 py-6 pb-8">
        {/* Top bar */}
        <div className="flex items-center justify-center relative">
          <h1 className="text-[16px] font-semibold">Project Completed</h1>
          <button
            aria-label="Close"
            onClick={() => navigate(-1)}
            className="absolute right-0 text-xl leading-none px-2 py-1 rounded hover:bg-gray-100"
          >
            ×
          </button>
        </div>

        {/* Confetti / emoji */}
        <div className="flex justify-center mt-4">
          <div className="w-28 h-28 rounded-full bg-gray-100 flex items-center justify-center text-5xl">
            🎉
          </div>
        </div>

        {/* Congrats */}
        <div className="text-center mt-4">
          <h2 className="text-lg font-bold">Congratulations!</h2>
          <p className="text-sm text-gray-600 mt-1">
            {loading ? "Generating a short note…" : apiMsg}
          </p>
        </div>

        {/* Card: Rating & Review */}
        <div className="mt-5 rounded-xl border border-gray-200 p-4">
          <div className="text-center text-sm font-semibold">Rating & Review</div>

          {/* Stars */}
          <div className="mt-3 flex justify-center space-x-3">
            {[1,2,3,4,5].map(n => (
              <button
                key={n}
                type="button"
                aria-label={`Rate ${n} star${n>1?"s":""}`}
                onMouseEnter={() => setHover(n)}
                onMouseLeave={() => setHover(0)}
                onClick={() => setRating(n)}
                className="text-2xl"
              >
                <span className={(hover || rating) >= n ? "text-yellow-400" : "text-gray-300"}>★</span>
              </button>
            ))}
          </div>

          {/* Prompt */}
          <div className="mt-4">
            <label className="block text-xs text-gray-600 mb-1">
              How was your experience fixing this issue?
            </label>
            <input
              type="text"
              placeholder="Write us a feedback..."
              value={comments}
              onChange={(e) => setComments(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm bg-gray-50 focus:bg-white focus:outline-none"
            />
          </div>
        </div>

        {/* Helper pill */}
        <div className="mt-3 rounded-xl border border-gray-200 bg-gray-50 p-3 text-[12px] text-gray-600">
          If you need to go back and edit your steps, or revisit any part you felt stuck on, we're here to help!
        </div>

        {/* Error */}
        {error && (
          <div className="mt-3 text-red-600 text-sm">{error}</div>
        )}

        {/* Main actions */}
        <div className="mt-3 grid grid-cols-2 gap-3">
          <button
            onClick={() => navigate(-1)}
            className="py-2 rounded-lg border border-gray-300 bg-gray-50 text-sm font-medium"
          >
            Go back
          </button>
          <button
            onClick={onFinish}
            disabled={saving}
            className={`py-2 rounded-lg text-white text-sm font-semibold ${saving ? "bg-green-300" : "bg-[#6FCBAE] hover:opacity-90"}`}
          >
            {saving ? "Saving…" : "Finish"}
          </button>
        </div>

        {/* Secondary actions */}
        <div className="mt-4 grid grid-cols-2 gap-3">
          <button
            onClick={() => alert("(Placeholder) Share success")}
            className="rounded-xl border border-gray-200 bg-white px-3 py-3 text-center"
          >
            <div className="text-xl mb-1">🏆</div>
            <div className="text-xs font-semibold">Share Success</div>
            <div className="text-[11px] text-gray-500">Show off your work</div>
          </button>

          <button
            onClick={() => navigate("/home")}
            className="rounded-xl border border-gray-200 bg-white px-3 py-3 text-center"
          >
            <div className="text-xl mb-1">📁</div>
            <div className="text-xs font-semibold">All Projects</div>
            <div className="text-[11px] text-gray-500">View history</div>
          </button>
        </div>

        {/* Start New Project */}
        <button
          onClick={() => navigate("/home")}
          className="mt-4 w-full bg-black text-white text-sm font-semibold rounded-lg py-2"
        >
          Start New Project
        </button>
      </div>
    </div>
  );
}
