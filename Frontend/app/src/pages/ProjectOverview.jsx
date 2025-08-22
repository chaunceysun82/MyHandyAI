// src/pages/ProjectOverview.jsx
import React, { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams, useLocation } from "react-router-dom";
import { fetchEstimations, fetchSteps } from "../services/overview";
import StepCard from "../components/StepCard";
import EstimatedBreakdown from "../components/EstimationBreakdown";

export default function ProjectOverview() {
	const navigate = useNavigate();
	const { projectId } = useParams();
	const { state } = useLocation();
	const userName = state?.userName || "User";

	const [loading, setLoading] = useState(true);
	const [steps, setSteps] = useState([]);
	const [estimations, setEstimations] = useState(null);
	const [error, setError] = useState("");
	const [projectVideoUrl, setProjectVideoUrl] = useState(null); // Store the project-level YouTube URL

	useEffect(() => {
		let cancelled = false;
		(async function run() {
			setLoading(true);
			setError("");
			try {
				console.log("ProjectOverview: Fetching data for project:", projectId);
				
				const [rawSteps, rawEst] = await Promise.all([
					fetchSteps(projectId).catch((err) => {
						console.log("ProjectOverview: Error fetching steps:", err);
						return null;
					}),
					fetchEstimations(projectId).catch((err) => {
						console.log("ProjectOverview: Error fetching estimations:", err);
						// Return fallback estimation data if API fails
						return {
							minutes: 30,
							duration: "30 Minutes",
							cost: "$20.00",
							skill: "Beginner–Intermediate"
						};
					}),
				]);

				if (cancelled) return;

				console.log("ProjectOverview: Raw steps data:", rawSteps);
				console.log("ProjectOverview: Raw estimations data:", rawEst);
				
				// Extract YouTube URL from raw API response
				const videoUrl = extractProjectVideoUrl(rawSteps);
				console.log("ProjectOverview: Extracted YouTube URL:", videoUrl);
				setProjectVideoUrl(videoUrl);
				
				const normalizedSteps = normSteps(rawSteps);
				const normalizedEstimations = normEstimations(rawEst);
				
				console.log("ProjectOverview: Normalized steps:", normalizedSteps);
				console.log("ProjectOverview: Normalized estimations:", normalizedEstimations);
				
				setSteps(normalizedSteps);
				setEstimations(normalizedEstimations);
				setLoading(false);
			} catch (e) {
				if (!cancelled) {
					console.error("ProjectOverview: Error in useEffect:", e);
					setError("Couldn't load project overview.");
					setSteps(normSteps(null));
					setEstimations(null);
					setLoading(false);
				}
			}
		})();

		return () => {
			cancelled = true;
		};
	}, [projectId]);

	const displayedSteps = useMemo(
		() => (loading ? withTools(defaultSteps) : steps),
		[loading, steps]
	);
	const stats = useMemo(() => {
		console.log("ProjectOverview: Calculating stats with:", { estimations, steps });
		
		if (estimations) {
			const mins = Number(estimations.minutes || 0);
			console.log("ProjectOverview: Using estimations data, minutes:", mins);
			
			const result = {
				duration:
					estimations.duration || (mins ? `${mins} Minutes` : "30 Minutes"),
				cost:
					estimations.cost || "$20.00",
				skill: estimations.skill || "Beginner–Intermediate",
			};
			
			console.log("ProjectOverview: Stats from estimations:", result);
			return result;
		}

		console.log("ProjectOverview: No estimations, calculating from steps");
		const mins = steps
			.map((s) => extractMinutes(s.time))
			.filter(Boolean)
			.reduce((a, b) => a + b, 0);

		const result = {
			duration: mins ? `${mins} Minutes` : "30 Minutes",
			cost: "$20.00",
			skill: "Beginner–Intermediate",
		};
		
		console.log("ProjectOverview: Stats from steps:", result);
		return result;
	}, [estimations, steps]);

	const handleClose = () => navigate("/home");
	const openAssistant = () =>
		navigate("/chat", { state: { projectId, from: "overview" } });
	const goPrev = () => navigate(-1);
	const goNext = () => {
		// Always navigate to Step 1 (Tools Required) when Next Step is clicked
		if (displayedSteps.length > 0) {
			console.log("ProjectOverview: Navigating to Step 1 (Tools Required)");
			console.log("ProjectOverview: Video URL for tools page:", projectVideoUrl);
			console.log("ProjectOverview: Navigation state being passed:", {
				projectId,
				stepIndex: 0,
				projectVideoUrl: projectVideoUrl
			});
			navigate(`/projects/${projectId}/tools`, {
				state: { 
					projectId, 
					stepIndex: 0,
					projectVideoUrl: projectVideoUrl // Add this line to pass video URL
				}
			});
		}
	};

	const goToStep = (stepIndex) => {
		// Check if this is the tools step (first step with tools icon)
		if (stepIndex === 0 && displayedSteps[0]?.key === "tools-step") {
			console.log("ProjectOverview: Navigating to tools page");
			console.log("ProjectOverview: Video URL for tools page:", projectVideoUrl);
			navigate(`/projects/${projectId}/tools`, { 
				state: { 
					projectId, 
					stepIndex: 0,
					projectVideoUrl: projectVideoUrl // Pass video URL
				}
			});
		} else {
			// Navigate to step page - StepPage will fetch data from backend
			// IMPORTANT: Step indexing adjustment for "Tools Required"
			// - UI shows: Step 1 (Tools), Step 2 (First project step), Step 3 (Second project step)...
			// - URL should be: /tools, /steps/1, /steps/2, /steps/3...
			// - So Step 2 in UI = /steps/1, Step 3 in UI = /steps/2, etc.
			const stepNumber = stepIndex; // stepIndex 0 = tools, 1 = first project step, 2 = second project step
			console.log("ProjectOverview: Navigating to step", stepNumber);
			console.log("ProjectOverview: Project ID:", projectId);
			
			console.log("ProjectOverview: Video URL for step page:", projectVideoUrl);
			console.log("ProjectOverview: Navigation state:", { 
				projectId,
				projectName: state?.projectName || "Project",
				projectVideoUrl: projectVideoUrl
			});
			
			navigate(`/projects/${projectId}/steps/${stepNumber}`, {
				state: { 
					projectId,
					projectName: state?.projectName || "Project",
					projectVideoUrl: projectVideoUrl // Pass video URL
				}
			});
		}
	};

	return (
		<div className="min-h-screen flex justify-center bg-white">
			<div className="w-full max-w-md flex flex-col h-screen">
				{/* Header */}
				<div className="sticky top-0 z-10 bg-white pt-5 pb-3 px-4">
					<div className="flex items-center justify-center relative">
						<h1 className="text-[16px] font-semibold">Project Overview</h1>
						<button
							aria-label="Close"
							onClick={handleClose}
							className="absolute right-0 text-xl leading-none px-2 py-1 rounded hover:bg-gray-100">
							×
						</button>
					</div>
				</div>

				{/* Estimated Breakdown */}
				<div className="px-4">
					<EstimatedBreakdown stats={stats} />
				</div>

				{/* Intro text */}
				<div className="px-4">
					<p className="text-[11px] text-gray-500 mt-3">
						Based on our conversation, here is your {displayedSteps.length} step
						solution:
					</p>
				</div>

				{/* Error banner */}
				{error && (
					<div className="px-4 mt-2">
						<div className="text-[12px] text-red-600 bg-red-50 border border-red-200 rounded-lg p-2">
							{error}
						</div>
					</div>
				)}

				{/* Scrollable Steps list */}
				<div className="flex-1 overflow-y-auto px-4 mt-3">
					<div className="space-y-3 pb-4">
						{displayedSteps.map((s, i) => {
							console.log("ProjectOverview: Rendering step:", { 
								title: s.title, 
								completed: s.completed, 
								status: s.status,
								index: i 
							});
							return (
								<StepCard
									key={s.key || i}
									index={i}
									icon={s.icon}
									title={s.title}
									subtitle={s.subtitle}
									time={s.time}
									status={s.status}
									imageUrl={s.imageUrl}
									completed={s.completed}
									onClick={() => goToStep(i)}
								/>
							);
						})}
					</div>
				</div>

				{/* Fixed Bottom Section */}
				<div className="px-4 pb-4 space-y-3">
					{/* Assistant prompt pill */}
					<div className="rounded-xl border border-gray-200 bg-gray-50 px-3 py-2 text-[12px] text-gray-600 flex items-center justify-between">
						<span>Hi "{userName}", Need MyHandyAI Assistant?</span>
						<button
							onClick={openAssistant}
							className="ml-3 px-3 py-1 rounded-lg bg-[#6FCBAE] text-white text-[12px] font-semibold">
							Ask
						</button>
					</div>

					{/* Bottom Navigation */}
					<div className="grid grid-cols-2 gap-3">
						<button
							onClick={goPrev}
							className="py-2 rounded-lg border border-gray-300 bg-gray-50 text-sm font-medium">
							Previous
						</button>
						<button
							onClick={goNext}
							className="py-2 rounded-lg bg-black text-white text-sm font-semibold">
							Next Step
						</button>
					</div>
				</div>
			</div>
		</div>
	);
}

// -------------------- Helpers --------------------

const defaultSteps = [
	{
		icon: "📏",
		title: "Locate Studs",
		subtitle: "Find wall studs for secure mounting",
		time: "10–15 min",
		status: "Complete",
		completed: true,
	},
	{
		icon: "✏️",
		title: "Mark Mounting Points",
		subtitle: "Measure and mark bracket positions",
		time: "10–15 min",
		status: "In Progress",
		completed: false,
	},
	{
		icon: "🔩",
		title: "Install Brackets",
		subtitle: "Drill holes and mount wall brackets",
		time: "15–20 min",
		status: "Not Started",
		completed: false,
	},
	{
		icon: "🪞",
		title: "Attach Mirror to Wall",
		subtitle: "Hang mirror securely on brackets",
		time: "5–10 min",
		status: "Not Started",
		completed: false,
	},
];

function normEstimations(api) {
	console.log("ProjectOverview: normEstimations called with:", api);
	
	if (!api) {
		console.log("ProjectOverview: No estimation data provided");
		return null;
	}

	if (
		"minutes" in api ||
		"duration" in api ||
		"cost" in api ||
		"skill" in api
	) {
		console.log("ProjectOverview: Using direct estimation data");
		return api;
	}

	console.log("ProjectOverview: Processing nested estimation data structure");
	const ed = api.estimation_data || api.est || api.data || {};
	const t = ed.total_estimated_time || {};
	const c = ed.total_estimated_cost || {};
	const s = ed.summary || {};

	console.log("ProjectOverview: Extracted data:", { ed, t, c, s });

	const minutes = t.minutes ?? ed.total_est_time_min ?? api.total_est_time_min;
	const duration =
		t.human_readable || (minutes ? `${minutes} Minutes` : undefined);

	let cost = "";
	if (typeof c.amount === "number") {
		const currency = (c.currency || "USD").toUpperCase();
		try {
			cost = new Intl.NumberFormat("en-US", {
				style: "currency",
				currency,
				maximumFractionDigits: 2,
			}).format(c.amount);
		} catch {
			cost = `$${c.amount.toFixed(2)}`;
		}
	}

	const skill = s.complexity_level || s.complexity || api.skill || "";

	const result = { minutes, duration, cost, skill };
	console.log("ProjectOverview: Final normalized estimations:", result);
	return result;
}

function normSteps(raw) {
	if (!raw) return withTools(defaultSteps);

	if (Array.isArray(raw) && raw.length && "title" in raw[0]) {
		const normalized = raw.map((s, i) => ({
			key: s.key || s._id || s.id || `step-${i}`,
			title: s.title,
			subtitle: s.subtitle || "Tap to see details",
			time: s.time || "",
			icon: s.icon || pickIcon(i + 1),
			completed: s.completed || false, // Add completed field
		}));
		return withTools(normalized);
	}

	const arr =
		raw?.steps_data?.steps || raw?.steps || (Array.isArray(raw) ? raw : []);
	if (!Array.isArray(arr) || !arr.length) return withTools(defaultSteps);

	const normalized = arr.map((s, i) => ({
		key: s._id || s.id || `step-${i}`,
		title: s.title || s.step_title || `Step ${i + 1}`,
		subtitle: s.summary || s.description || "Tap to see details",
		time: s.time_text || (s.est_time_min ? `${s.est_time_min} min` : ""),
		icon: pickIcon(i + 1),
		completed: s.completed || false, // Add completed field
	}));

	return withTools(normalized);
}

function withTools(steps) {
	return [
		{
			key: "tools-step",
			icon: "🧰",
			title: "Tools Required",
			subtitle: "List of tools needed for this project",
			time: "",
			completed: false, // Tools step is never completed
		},
		...steps,
	];
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

// Helper function to extract YouTube URL from steps data
function extractProjectVideoUrl(steps) {
	console.log("ProjectOverview: extractProjectVideoUrl called with:", steps);
	
	if (!steps) {
		console.log("ProjectOverview: No steps data provided");
		return null;
	}

	// Check if steps has a steps_data object with youtube field
	if (steps.steps_data && steps.steps_data.youtube) {
		console.log("ProjectOverview: Found YouTube URL in steps_data:", steps.steps_data.youtube);
		return steps.steps_data.youtube;
	}

	// Check if steps has a direct youtube field
	if (steps.youtube) {
		console.log("ProjectOverview: Found YouTube URL directly:", steps.youtube);
		return steps.youtube;
	}

	// Look for any step that has a video URL
	if (Array.isArray(steps)) {
		for (const step of steps) {
			if (step.videoUrl || step.video_url || step.youtube) {
				console.log("ProjectOverview: Found YouTube URL in step:", step.videoUrl || step.video_url || step.youtube);
				return step.videoUrl || step.video_url || step.youtube;
			}
		}
	}

	console.log("ProjectOverview: No YouTube URL found");
	return null;
}
