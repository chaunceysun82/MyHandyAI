// src/pages/ProjectOverview.jsx
import React, { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams, useLocation } from "react-router-dom";
import { fetchEstimations, fetchSteps } from "../services/overview";

export default function ProjectOverview() {
  const navigate = useNavigate();
  const { id: projectId } = useParams();
  const { state } = useLocation(); 
  const userName = state?.userName || "User";

  const [loading, setLoading] = useState(true);
  const [steps, setSteps] = useState([]);
  const [estimations, setEstimations] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    (async () => {
      setLoading(true);
      setError("");
      try {
        const [rawSteps, rawEst] = await Promise.all([
          fetchSteps(projectId).catch(() => null),
          fetchEstimations(projectId).catch(() => null),
        ]);

        if (cancelled) return;

        setSteps(normSteps(rawSteps));
        setEstimations(normEstimations(rawEst));
        setLoading(false);
      } catch (e) {
        if (!cancelled) {
          console.error(e);
          setError("Couldn’t load project overview.");
          setSteps(defaultSteps);
          setEstimations(null);
          setLoading(false);
        }
      }
    })();

    return () => { cancelled = true; };
  }, [projectId]);

  
  const stats = useMemo(() => {
    if (estimations) {
      const mins = Number(estimations.minutes || 0);
      return {
        duration: estimations.duration || (mins ? `${mins} Minutes` : "30 Minutes"),
        cost: estimations.cost || "$20.00",
        // use complexity level for skill display
        skill: estimations.skill || "Beginner–Intermediate",
      };
    }

    const mins = steps
      .map((s) => extractMinutes(s.time))
      .filter(Boolean)
      .reduce((a, b) => a + b, 0);

    return {
      duration: mins ? `${mins} Minutes` : "30 Minutes",
      cost: "$20.00",
      skill: "Beginner–Intermediate",
    };
  }, [estimations, steps]);

  const handleClose = () => navigate(-1);
  const openAssistant = () =>
    navigate("/chat", { state: { projectId, from: "overview" } });
  const goPrev = () => navigate(-1);
  const goNext = () => {
    if (steps.length > 0) {
      alert("Next: open Step 1 details (placeholder).");
    }
  };

  return (
    <div className="min-h-screen flex justify-center bg-white">
      
      <div className="w-full max-w-md px-4 pb-8">
        {/* Header */}
        <div className="sticky top-0 z-10 bg-white pt-5 pb-3">
          <div className="flex items-center justify-center relative">
            <h1 className="text-[16px] font-semibold">Project Overview</h1>
            <button
              aria-label="Close"
              onClick={handleClose}
              className="absolute right-0 text-xl leading-none px-2 py-1 rounded hover:bg-gray-100"
            >
              ×
            </button>
          </div>
        </div>

        {/* Estimated Breakdown */}
        <section>
          <div className="flex items-center text-[13px] font-semibold">
            Estimated Breakdown
            <span className="ml-1 text-gray-400 text-xs">ⓘ</span>
          </div>

          <div className="mt-2 rounded-2xl border border-gray-200 bg-gray-50 p-3 space-y-2">
            <StatRow label="Estimated time duration" value={stats.duration} />
            <StatRow label="Estimated Cost: Tools + materials" value={stats.cost} />
            <StatRow label="Skill level" value={stats.skill} />
          </div>
        </section>

        {/* Intro text */}
        <p className="text-[11px] text-gray-500 mt-3">
          Based on our conversation, here is your {steps.length || 5} step solution:
        </p>

        {/* Error banner */}
        {error && (
          <div className="mt-2 text-[12px] text-red-600 bg-red-50 border border-red-200 rounded-lg p-2">
            {error}
          </div>
        )}

        {/* Steps list */}
        <div className="mt-3 space-y-3">
          {(loading ? defaultSteps : steps).map((s, i) => (
            <StepCard
              key={s.key || i}
              index={i + 1}
              icon={s.icon}
              title={s.title}
              subtitle={s.subtitle}
              time={s.time}
              onClick={() => alert(`(Placeholder) Open details for Step ${i + 1}`)}
            />
          ))}
        </div>

        {/* Assistant prompt pill */}
        <div className="mt-4 rounded-xl border border-gray-200 bg-gray-50 px-3 py-2 text-[12px] text-gray-600 flex items-center justify-between">
          <span>Hi “{userName}”, Need MyHandyAI Assistant?</span>
          <button
            onClick={openAssistant}
            className="ml-3 px-3 py-1 rounded-lg bg-[#6FCBAE] text-white text-[12px] font-semibold"
          >
            Ask
          </button>
        </div>

        
        <div className="mt-3 grid grid-cols-2 gap-3">
          <button
            onClick={goPrev}
            className="py-2 rounded-lg border border-gray-300 bg-gray-50 text-sm font-medium"
          >
            Previous
          </button>
          <button
            onClick={goNext}
            className="py-2 rounded-lg bg-black text-white text-sm font-semibold"
          >
            Next Step
          </button>
        </div>
      </div>
    </div>
  );
}


function StatRow({ label, value }) {
  return (
    <div className="flex items-center justify-between bg-white rounded-xl px-3 py-2">
      <span className="text-[11px] text-gray-500">{label}</span>
      <span className="text-[11px] font-medium">{value}</span>
    </div>
  );
}

function StepCard({ index, icon, title, subtitle, time, onClick }) {
  
  const short = truncateWords(subtitle, 7);

  return (
    <button
      onClick={onClick}
      className="w-full text-left rounded-xl bg-gray-100 hover:bg-gray-200 transition-colors p-3 flex items-center gap-3"
    >
      
      <div className="w-14 h-14 rounded-lg bg-white flex items-center justify-center text-2xl">
        <span aria-hidden="true">{icon || "🧰"}</span>
      </div>

      
      <div className="flex-1">
        {time ? (
          <div className="mb-0.5 inline-flex items-center text-[11px] text-gray-500">
            <span className="mr-1">⏱</span> {time}
          </div>
        ) : null}
        <div className="text-[13px] font-semibold leading-tight">{title}</div>
        <div className="text-[11px] text-gray-500">{short}</div>
      </div>

      
      <div className="shrink-0">
        <span className="inline-flex items-center text-[11px] px-2 py-1 rounded-full bg-white border border-gray-300">
          Step {index} <span className="ml-1">›</span>
        </span>
      </div>
    </button>
  );
}



const defaultSteps = [
  { icon: "🧰", title: "Prepare Tools and Materials", subtitle: "& tools needed", time: "" },
  { icon: "📏", title: "Locate Studs", subtitle: "Find wall studs for secure mounting", time: "10–15 min" },
  { icon: "✏️", title: "Mark Mounting Points", subtitle: "Measure and mark bracket positions", time: "10–15 min" },
  { icon: "🔩", title: "Install Brackets", subtitle: "Drill holes and mount wall brackets", time: "15–20 min" },
  { icon: "🪞", title: "Attach Mirror to Wall", subtitle: "Hang mirror securely on brackets", time: "5–10 min" },
];

function truncateWords(text, count = 7) {
  if (!text) return "";
  const words = String(text).trim().split(/\s+/);
  if (words.length <= count) return text;
  return words.slice(0, count).join(" ") + "…";
}


function normEstimations(api) {
  if (!api) return null;

  
  if ("minutes" in api || "duration" in api || "cost" in api || "skill" in api) {
    return api;
  }

  const ed = api.estimation_data || api.est || api.data || {};
  const t = ed.total_estimated_time || {};
  const c = ed.total_estimated_cost || {};
  const s = ed.summary || {};

  const minutes = t.minutes ?? ed.total_est_time_min ?? api.total_est_time_min;
  const duration = t.human_readable || (minutes ? `${minutes} Minutes` : undefined);

  let cost = "";
  if (typeof c.amount === "number") {
    const currency = (c.currency || "USD").toUpperCase();
    try {
      cost = new Intl.NumberFormat("en-US", { style: "currency", currency, maximumFractionDigits: 2 }).format(c.amount);
    } catch {
      cost = `$${c.amount.toFixed(2)}`;
    }
  }

  // use complexity as skill
  const skill = s.complexity_level || s.complexity || api.skill || "";

  return { minutes, duration, cost, skill };
}


function normSteps(raw) {
  if (!raw) return defaultSteps;

  
  if (Array.isArray(raw) && raw.length && ("title" in raw[0])) {
    return raw.map((s, i) => ({
      key: s.key || s._id || s.id || `step-${i}`,
      title: s.title,
      subtitle: s.subtitle || "Tap to see details",
      time: s.time || "",
      icon: s.icon || pickIcon(i),
    }));
  }

  const arr = raw?.steps_data?.steps || raw?.steps || (Array.isArray(raw) ? raw : []);
  if (!Array.isArray(arr) || !arr.length) return defaultSteps;

  return arr.map((s, i) => ({
    key: s._id || s.id || `step-${i}`,
    title: s.title || s.step_title || `Step ${i + 1}`,
    subtitle: s.summary || s.description || "Tap to see details",
    time: s.time_text || (s.est_time_min ? `${s.est_time_min} min` : ""),
    icon: pickIcon(i),
  }));
}

function extractMinutes(text) {
  if (!text || typeof text !== "string") return 0;
  const m = text.match(/(\d+)\s*(?:–|-)?\s*(\d+)?\s*min|(\d+)\s*Minutes/i);
  if (!m) return 0;
  if (m[3]) return parseInt(m[3], 10) || 0;
  if (m[1] && m[2]) return Math.round((+m[1] + +m[2]) / 2);
  if (m[1]) return +m[1];
  return 0;
}

function pickIcon(i) {
  return ["🧰", "📏", "✏️", "🔩", "🪞"][i % 5];
}
