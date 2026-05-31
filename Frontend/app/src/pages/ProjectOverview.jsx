// src/pages/ProjectOverview.jsx
import React, { useEffect, useMemo, useState, useRef } from "react";
import { useNavigate, useParams, useLocation } from "react-router-dom";
import { fetchEstimations, fetchProject, fetchSteps } from "../services/overview";
import StepCard from "../components/StepCard";
import EstimatedBreakdown from "../components/EstimationBreakdown";
import ChatWindow2 from "../components/Chat/ChatWindow2";
import defaultTools from "../assets/default_tools.svg";
import {ReactComponent as Bot} from '../assets/Bot.svg';


export default function ProjectOverview() {

	const URL = process.env.REACT_APP_BASE_URL;

	const navigate = useNavigate();
	const { projectId } = useParams();
	const { state } = useLocation();
	const location = useLocation();


	const {userId} = location.state || {};

	const userName = state?.userName || localStorage.getItem("displayName") || sessionStorage.getItem("displayName") || "User";
	
	// Helper function to extract first name
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

	const [openModal, setOpenModal] = useState(false);

	const [loading, setLoading] = useState(true);
	const [steps, setSteps] = useState([]);
	const [estimations, setEstimations] = useState(null);
	const [error, setError] = useState("");
	const [projectVideoUrl, setProjectVideoUrl] = useState(null); // Store the project-level YouTube URL
	const [previewImageUrl, setPreviewImageUrl] = useState(null);
	
	// Refs for scrollable sections
	const stepsContainerRef = useRef(null);
	const toolsSectionRef = useRef(null);

	useEffect(() => {
		let cancelled = false;
		(async function run() {
			setLoading(true);
			setError("");
			try {
				
				const [rawSteps, rawEst, rawProject] = await Promise.all([
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
					fetchProject(projectId).catch((err) => {
						console.log("ProjectOverview: Error fetching project:", err);
						return null;
					}),
				]);

				if (cancelled) return;

				const videoUrl = extractProjectVideoUrl(rawSteps);
				setProjectVideoUrl(videoUrl);
				
				const normalizedSteps = normSteps(rawSteps);
				const normalizedEstimations = normEstimations(rawEst);
				
				setSteps(normalizedSteps);
				setEstimations(normalizedEstimations);
				setPreviewImageUrl(rawProject?.result_preview_image?.url || null);
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
		() => (loading ? [] : steps),
		[loading, steps]
	);
	const stats = useMemo(() => {
		
		if (estimations) {
			const mins = Number(estimations.minutes || 0);
			
			const result = {
				duration:
					estimations.duration || (mins ? `${mins} Minutes` : "30 Minutes"),
				cost:
					estimations.cost || "$20.00",
				skill: estimations.skill || "Beginner–Intermediate",
			};
			
			return result;
		}

		const mins = steps
			.map((s) => extractMinutes(s.time))
			.filter(Boolean)
			.reduce((a, b) => a + b, 0);

		const result = {
			duration: mins ? `${mins} Minutes` : "30 Minutes",
			cost: "$20.00",
			skill: "Beginner–Intermediate",
		};
		
		return result;
	}, [estimations, steps]);

	const handleClose = () => navigate("/home");

	const openAssistant = () => {

		// Have a modal open up with the chat assistant
		console.log("User ID", userId);
		console.log("Project ID", projectId);
		setOpenModal(true);
	};
		// navigate("/chat", { state: { projectId, from: "overview" } });


	// const handleClose = () => navigate("/home");

	// const openAssistant = () =>
	// 	navigate("/chat", { state: { projectId, from: "overview" } });
	const goPrev = () => navigate(-1);

	const goNext = () => {
		// Always navigate to Step 1 (Tools Required) when Next Step is clicked
		if (displayedSteps.length > 0) {
			navigate(`/projects/${projectId}/tools`, {
				state: { 
					projectId, 
					stepIndex: 0,
					projectVideoUrl: projectVideoUrl, // Add this line to pass video URL
					userName: userName // Pass userName to tools page
				}
			});
		}
	};

	const goToStep = (stepIndex) => {
		// Check if this is the tools step (first step with tools icon)
		if (stepIndex === 0 && displayedSteps[0]?.key === "tools-step") {
			navigate(`/projects/${projectId}/tools`, { 
				state: { 
					projectId, 
					stepIndex: 0,
					projectVideoUrl: projectVideoUrl, // Pass video URL
					userName: userName // Pass userName to tools page
				}
			});
		} else {
			// Navigate to step page - StepPage will fetch data from backend
			// IMPORTANT: Step indexing adjustment for "Tools Required"
			// - UI shows: Step 1 (Tools), Step 2 (First project step), Step 3 (Second project step)...
			// - URL should be: /tools, /steps/1, /steps/2, /steps/3...
			// - So Step 2 in UI = /steps/1, Step 3 in UI = /steps/2, etc.
			const stepNumber = stepIndex; // stepIndex 0 = tools, 1 = first project step, 2 = second project step
			
			navigate(`/projects/${projectId}/steps/${stepNumber}`, {
				state: { 
					projectId,
					projectName: state?.projectName || "Project",
					projectVideoUrl: projectVideoUrl, // Pass video URL
					userName: userName // Pass userName to step page
				}
			});
		}
	};

	const previewCard = (
		<ResultPreviewCard
			loading={loading}
			imageUrl={previewImageUrl}
			onOpen={() => previewImageUrl && window.open(previewImageUrl, "_blank")}
		/>
	);

	return (
		<div className="min-h-screen bg-[#fffef6]">
			<div className="mx-auto flex h-screen w-full max-w-6xl flex-col">
				<div className="sticky top-0 z-20 bg-[#fffef6]">
					<div className="px-4 pb-3 pt-5 lg:px-8 lg:pb-5 lg:pt-7">
						<div className="relative flex items-center justify-center lg:justify-start">
							<h1 className="text-[20px] font-semibold lg:text-[28px]">Project Overview</h1>
							<button
								aria-label="Close"
								onClick={handleClose}
								className="absolute right-0 rounded px-2 py-1 text-3xl leading-none hover:bg-gray-100">
								×
							</button>
						</div>
					</div>
				</div>

				<div className="flex-1 overflow-y-auto">
					<div className="grid gap-6 px-4 pb-6 lg:grid-cols-[minmax(280px,360px)_minmax(0,1fr)] lg:px-8 lg:pb-8">
						<div className="lg:sticky lg:top-20 lg:self-start">
							<div className="space-y-3 pb-2 pt-3 lg:pb-8 lg:pt-0">
								<div>
									{loading ? (
										<div className="animate-pulse">
											<div className="h-20 rounded-lg bg-gray-200"></div>
										</div>
									) : (
										<EstimatedBreakdown stats={stats} />
									)}
								</div>

								<div ref={toolsSectionRef}>
									{loading ? (
										<div className="animate-pulse">
											<div className="h-20 rounded-lg bg-gray-200"></div>
										</div>
									) : (
										<StepCard
											key="tools-step"
											index={0}
											icon="🧰"
											title="Tools and Materials"
											subtitle="List of tools needed for this project"
											time=""
											status=""
											imageUrl={defaultTools}
											completed={false}
											onClick={() => goToStep(0)}
										/>
									)}
								</div>

								<div className="hidden lg:block">
									{previewCard}
								</div>
							</div>
						</div>

						<div className="min-w-0 pt-0 lg:pt-3">
							<div className="pb-4">
								{loading ? (
									<div className="animate-pulse">
										<div className="mb-2 h-4 w-48 rounded bg-gray-200"></div>
										<div className="h-3 w-64 rounded bg-gray-200"></div>
									</div>
								) : (
									<>
										<h2 className="mb-1 text-md font-bold text-gray-900 lg:text-xl">Step-by-step guidance</h2>
										<p className="text-[10px] text-gray-600 lg:text-sm">
											Based on our conversation, here is your {displayedSteps.length > 0 ? displayedSteps.length - 1 : 0} step solution:
										</p>
									</>
								)}
							</div>

							{error && (
								<div className="mt-2">
									<div className="rounded-lg border border-red-200 bg-red-50 p-2 text-[12px] text-red-600">
										{error}
									</div>
								</div>
							)}

							<div ref={stepsContainerRef}>
								<div className="space-y-3 pb-4">
									{loading ? (
										<>
											{[...Array(4)].map((_, i) => (
												<div key={i} className="animate-pulse">
													<div className="flex w-full items-center gap-3 rounded-2xl bg-gray-200 px-3 py-3">
														<div className="h-14 w-14 rounded-lg bg-gray-300"></div>
														<div className="flex-1">
															<div className="mb-1 flex gap-2">
																<div className="h-4 w-16 rounded-md bg-gray-300"></div>
																<div className="h-4 w-20 rounded-md bg-gray-300"></div>
															</div>
															<div className="mb-2 h-4 w-32 rounded bg-gray-300"></div>
															<div className="h-3 w-40 rounded bg-gray-300"></div>
														</div>
														<div className="shrink-0">
															<div className="h-6 w-16 rounded-full bg-gray-300"></div>
														</div>
													</div>
												</div>
											))}
										</>
									) : (
										displayedSteps
											.filter((s, i) => i > 0)
											.map((s, i) => {
												const actualStepIndex = i + 1;

												return (
													<StepCard
														key={s.key || actualStepIndex}
														index={actualStepIndex}
														icon={s.icon}
														title={s.title}
														subtitle={s.subtitle}
														time={s.time}
														status={s.status}
														imageUrl={null}
														completed={s.completed}
														onClick={() => goToStep(actualStepIndex)}
													/>
												);
											})
									)}
								</div>
							</div>

							<div className="mt-2 lg:hidden">
								{previewCard}
							</div>
						</div>
					</div>
				</div>

				<div className="border-t bg-[white]">
					<div className="mx-auto w-full max-w-6xl space-y-3 px-4 pb-4 lg:px-8 lg:pb-6">
						<button onClick={openAssistant} className="mt-2 flex w-full items-center justify-center gap-[10px] rounded-xl border border-gray-200 bg-[#1484A3] px-3 py-2 text-[12px] font-light text-white shadow-xl transition-all duration-200 ease-in-out hover:bg-[#026e8c]">
							<Bot width = {20} height = {20} />
							<span>Hi {getFirstName(userName)}, Need MyHandyAI Assistant?</span>
						</button>

						{openModal && (
							<ChatWindow2
								isOpen={openModal}
								projectId={projectId}
								onClose={() => setOpenModal(false)}
								URL={URL}
								stepNumber={-1}
							/>
						)}

						<div className="grid grid-cols-2 gap-3">
							<button
								onClick={goPrev}
								className="rounded-lg bg-[#E9FAFF] py-2 text-[12px] font-regular shadow-md transition-all duration-200 ease-in-out hover:bg-[#d9f7ff]">
								Previous
							</button>
							<button
								onClick={goNext}
								className="rounded-lg bg-[#E9FAFF] py-2 text-[12px] font-regular text-black shadow-md transition-all duration-200 ease-in-out hover:bg-[#d9f7ff]">
								Next Step
							</button>
						</div>
					</div>
				</div>
			</div>
		</div>
	);
}

function ResultPreviewCard({ imageUrl, loading, onOpen }) {
	if (loading) {
		return (
			<div className="animate-pulse rounded-3xl border-l-4 border-[#288AA5] bg-white p-4 shadow-lg">
				<div className="mb-3 h-4 w-36 rounded bg-gray-200"></div>
				<div className="aspect-[4/3] rounded-2xl bg-gray-200"></div>
			</div>
		);
	}

	if (!imageUrl) {
		return null;
	}

	return (
		<button
			type="button"
			onClick={onOpen}
			className="group w-full overflow-hidden rounded-3xl border-l-4 border-[#288AA5] bg-white text-left shadow-lg transition-all duration-200 hover:-translate-y-0.5 hover:shadow-[0_16px_32px_-18px_rgba(20,132,163,0.65)]"
		>
			<div className="p-4">
				<div className="mb-3 flex items-center justify-between gap-3">
					<div>
						<h3 className="text-base font-semibold text-gray-900">Project Preview</h3>
						<p className="text-xs text-gray-500">A visual estimate of the finished result</p>
					</div>
					<span className="rounded-full bg-[#E9FAFF] px-3 py-1 text-xs text-[#066580]">
						View
					</span>
				</div>
				<img
					src={imageUrl}
					alt="Generated project preview"
					className="aspect-[4/3] w-full rounded-2xl object-cover transition-transform duration-300 group-hover:scale-[1.02]"
				/>
			</div>
		</button>
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

// Helper function to round minutes to nearest 10
function roundMinutesToNearestTen(minutes) {
	if (!minutes || minutes <= 0) return 10; // Minimum 10 minutes
	return Math.round(minutes / 10) * 10;
}

// Helper function to round cost to nearest 10
function roundCostToNearestTen(amount) {
	if (!amount || amount <= 0) return 10; // Minimum $10
	return Math.round(amount / 10) * 10;
}

// Helper function to format rounded duration
function formatRoundedDuration(minutes) {
	const roundedMinutes = roundMinutesToNearestTen(minutes);
	
	if (roundedMinutes >= 60) {
		const hours = Math.floor(roundedMinutes / 60);
		const remainingMinutes = roundedMinutes % 60;
		
		if (remainingMinutes === 0) {
			return `${hours}hr`;
		} else {
			return `${hours}hr ${remainingMinutes}min`;
		}
	} else {
		return `${roundedMinutes}min`;
	}
}

function normEstimations(api) {
	
	if (!api) {
		return null;
	}

	if (
		"minutes" in api ||
		"duration" in api ||
		"cost" in api ||
		"skill" in api
	) {
		return api;
	}

	const ed = api.estimation_data || api.est || api.data || {};
	const t = ed.total_estimated_time || {};
	const c = ed.total_estimated_cost || {};
	const s = ed.summary || {};

	const minutes = t.minutes ?? ed.total_est_time_min ?? api.total_est_time_min;
	const roundedMinutes = roundMinutesToNearestTen(minutes);
	const duration = formatRoundedDuration(roundedMinutes);

	let cost = "";
	if (typeof c.amount === "number") {
		const roundedAmount = roundCostToNearestTen(c.amount);
		const currency = (c.currency || "USD").toUpperCase();
		try {
			cost = new Intl.NumberFormat("en-US", {
				style: "currency",
				currency,
				maximumFractionDigits: 0, // No decimal places for rounded values
			}).format(roundedAmount);
		} catch {
			cost = `$${roundedAmount}`;
		}
	}

	const skill = s.complexity_level || s.complexity || api.skill || "";

	const result = { minutes, duration, cost, skill };
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
			title: "Tools and Materials",
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
	
	let result = 0;
	if (m[3]) {
		result = parseInt(m[3], 10) || 0;
	} else if (m[1] && m[2]) {
		result = Math.round((+m[1] + +m[2]) / 2);
	} else if (m[1]) {
		result = +m[1];
	}
	
	// Round to nearest 10 minutes
	return roundMinutesToNearestTen(result);
}

function pickIcon(i) {
	return ["🧰", "📏", "✏️", "🔩", "🪞"][i % 5];
}

// Helper function to extract YouTube URL from steps data
function extractProjectVideoUrl(steps) {
	
	if (!steps) {
		return null;
	}

	// Check if steps has a steps_data object with youtube field
	if (steps.steps_data && steps.steps_data.youtube) {
		return steps.steps_data.youtube;
	}

	// Check if steps has a direct youtube field
	if (steps.youtube) {
		return steps.youtube;
	}

	// Look for any step that has a video URL
	if (Array.isArray(steps)) {
		for (const step of steps) {
			if (step.videoUrl || step.video_url || step.youtube) {
				return step.videoUrl || step.video_url || step.youtube;
			}
		}
	}

	return null;
}
