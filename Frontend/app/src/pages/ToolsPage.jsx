import React, { useEffect, useState } from "react";
import { useParams, useLocation, useNavigate } from "react-router-dom";
import ToolsLayout from "../components/steps/ToolsLayout";
import ToolsGrid from "../components/tools/ToolGrid";
import LoadingPlaceholder from "../components/LoadingPlaceholder";
import MobileWrapper from "../components/MobileWrapper";
import { fetchProjectTools, mockTools, transformToolsData } from "../services/tools";
import { fetchSteps } from "../services/overview";
import StepVideoGuide from "../components/steps/StepVideoGuide"; // Add this import

export default function ToolsPage() {
	const { projectId } = useParams();
	const location = useLocation();
	const navigate = useNavigate();
	const [tools, setTools] = useState([]);
	const [rawData, setRawData] = useState(null);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState("");
	const [totalSteps, setTotalSteps] = useState(1);
	const [showRawData, setShowRawData] = useState(false);
	
	// Filter state
	const [activeFilter, setActiveFilter] = useState("all"); // "all", "required", "optional"
	
	// Selection state
	const [selectedTools, setSelectedTools] = useState(new Set());
	const [isSelectionMode, setIsSelectionMode] = useState(false);
	
	// Get the project video URL from navigation state
	const projectVideoUrl = location.state?.projectVideoUrl;
	
	// Get userName from navigation state or localStorage
	const userName = location.state?.userName || localStorage.getItem("displayName") || sessionStorage.getItem("displayName") || "User";

	// const userId = location.state?.userId;
	// console.log("User ID:", userId);

	useEffect(() => {
		let cancelled = false;
		(async function run() {
			setLoading(true);
			setError("");
			try {
				console.log("ToolsPage: Fetching tools for project:", projectId);
				
				const rawTools = await fetchProjectTools(projectId);
				
				if (cancelled) return;

				console.log("ToolsPage: Raw tools data:", rawTools);
				
				const transformedTools = transformToolsData(rawTools);
				console.log("ToolsPage: Transformed tools:", transformedTools);
				
				// Log individual tool structure
				transformedTools.forEach((tool, index) => {
					console.log(`Tool ${index}:`, {
						name: tool.name,
						_id: tool._id,
						id: tool.id,
						price: tool.price,
						priceMin: tool.priceMin,
						priceMax: tool.priceMax,
						price_range: tool.price_range,
						required: tool.required
					});
				});
				
				setTools(transformedTools);
				setRawData(rawTools);
				
				// Get total steps for header
				try {
					const stepsData = await fetchSteps(projectId);
					if (stepsData && !cancelled) {
						setTotalSteps(stepsData.length || 1);
					}
				} catch (err) {
					console.log("ToolsPage: Error fetching steps:", err);
					setTotalSteps(1);
				}
				
				setLoading(false);
			} catch (e) {
				if (!cancelled) {
					console.error("ToolsPage: Error in useEffect:", e);
					setError("Couldn't load tools.");
					// Fallback to mock tools for development
					console.log("Using mock tools as fallback");
					setTools(mockTools);
					setTotalSteps(5);
					setLoading(false);
				}
			}
		})();

		return () => {
			cancelled = true;
		};
	}, [projectId]);

	// Debug effect to track selection changes and cost updates
	useEffect(() => {
		console.log("Selection changed - recalculating costs");
		const { totalMin, totalMax } = calculateTotalCost();
		console.log("Updated costs:", { totalMin, totalMax, selectedCount: selectedTools.size });
	}, [selectedTools, tools]);

	const handleBack = () => {
		navigate(`/projects/${projectId}/overview`, {
			state: {
				projectId,
				projectName: location.state?.projectName || "Project",
				projectVideoUrl: projectVideoUrl,
				userName: userName // Pass userName back to overview
			}
		});
	};

	const handlePrev = () => {
		// Navigate back to Project Overview since Tools is the first step
		navigate(`/projects/${projectId}/overview`, {
			state: {
				projectId,
				projectName: location.state?.projectName || "Project",
				projectVideoUrl: projectVideoUrl,
				userName: userName // Pass userName back to overview
			}
		});
	};

	const handleNext = () => {
		// Navigate to the first actual step (step 1, since tools is step 0)
		navigate(`/projects/${projectId}/steps/1`, { 
			state: { 
				projectVideoUrl,
				userName: userName // Pass userName to next step
			} 
		});
	};

	// Filter tools based on active filter
	const filteredTools = tools.filter(tool => {
		if (activeFilter === "all") return true;
		if (activeFilter === "required") return tool.required === true;
		if (activeFilter === "optional") return tool.required === false;
		return true;
	});

	// Handle tool selection
	const handleToolSelection = (toolId) => {
		if (!isSelectionMode) return; // Only allow selection in selection mode
		
		console.log("Tool selection toggled:", toolId);
		console.log("Current selectedTools before:", Array.from(selectedTools));
		
		setSelectedTools(prev => {
			const newSet = new Set(prev);
			if (newSet.has(toolId)) {
				newSet.delete(toolId);
				console.log("Removed tool:", toolId);
			} else {
				newSet.add(toolId);
				console.log("Added tool:", toolId);
			}
			console.log("New selectedTools:", Array.from(newSet));
			return newSet;
		});
	};

	// Calculate total cost of selected tools
	const calculateTotalCost = () => {
		let totalMin = 0;
		let totalMax = 0;
		
		console.log("calculateTotalCost called with selectedTools:", Array.from(selectedTools));
		console.log("Available tools:", tools.map(t => ({ name: t.name, _id: t._id, priceMin: t.priceMin, priceMax: t.priceMax, price: t.price })));
		
		selectedTools.forEach(toolId => {
			const tool = tools.find(t => {
				// Try multiple possible ID fields
				return t._id === toolId || t.id === toolId || t.tool_id === toolId;
			});
			
			if (tool) {
				console.log("Calculating cost for tool:", tool.name, "Price data:", {
					price: tool.price,
					priceMin: tool.priceMin,
					priceMax: tool.priceMax,
					price_range: tool.price_range,
					_id: tool._id,
					id: tool.id
				});
				
				// Handle different price formats
				if (tool.priceMin !== undefined && tool.priceMax !== undefined && tool.priceMin !== null && tool.priceMax !== null) {
					const min = Number(tool.priceMin) || 0;
					const max = Number(tool.priceMax) || 0;
					if (min > 0 || max > 0) {
						totalMin += min;
						totalMax += max;
						console.log(`Added ${min}-${max} for ${tool.name}`);
					}
				} else if (tool.price !== undefined && tool.price !== null) {
					const price = Number(tool.price) || 0;
					if (price > 0) {
						totalMin += price;
						totalMax += price;
						console.log(`Added ${price} for ${tool.name}`);
					}
				} else if (tool.price_range) {
					// Handle price range string like "$15 - $40"
					const rangeMatch = tool.price_range.match(/\$(\d+(?:\.\d+)?)\s*-\s*\$(\d+(?:\.\d+)?)/);
					if (rangeMatch) {
						const min = Number(rangeMatch[1]) || 0;
						const max = Number(rangeMatch[2]) || 0;
						if (min > 0 || max > 0) {
							totalMin += min;
							totalMax += max;
							console.log(`Added ${min}-${max} from range for ${tool.name}`);
						}
					}
				}
			} else {
				console.log("Tool not found for ID:", toolId);
			}
		});
		
		console.log("Total cost calculation result:", { totalMin, totalMax, selectedTools: Array.from(selectedTools) });
		return { totalMin, totalMax };
	};

	// Get selected tools count and calculate cost - this will recalculate on every render
	const selectedCount = selectedTools.size;
	const totalTools = tools.length;
	const { totalMin, totalMax } = calculateTotalCost();
	
	console.log("ToolsPage render state:", {
		selectedCount,
		totalTools,
		selectedTools: Array.from(selectedTools),
		totalMin,
		totalMax,
		toolsLength: tools.length,
		isSelectionMode
	});

	if (loading) {
		return (
			<MobileWrapper>
				<LoadingPlaceholder />
			</MobileWrapper>
		);
	}

	if (error) {
		return (
			<MobileWrapper>
				<div className="min-h-screen flex items-center justify-center p-4">
					<div className="text-center">
						<div className="text-red-600 mb-4">{error}</div>
						<button
							onClick={handleBack}
							className="px-4 py-2 bg-gray-200 rounded-lg"
						>
							Go Back
						</button>
					</div>
				</div>
			</MobileWrapper>
		);
	}

	return (
		<MobileWrapper>
			<ToolsLayout
				stepNumber={0} // Changed from 1 to 0 to display "Tools" instead of "Step 1/6"
				totalSteps={totalSteps}
				title="Prepare Tools and Materials"
				subtitle="Don't have these? Tap any item to order it easily."
				onBack={handleBack}
				onPrev={handlePrev}
				onNext={handleNext}
				projectId={projectId}
				projectName={location.state?.projectName || "Project"}
				projectVideoUrl={projectVideoUrl}
				userName={userName} // Pass userName prop
			>
				<div className="space-y-4">
					{/* Sticky Cost Estimation Section - Only the selection banner */}
					{selectedCount > 0 && (
						<div className="sticky top-0 z-10 pb-3 pt-2 -mx-4 px-4">
							<div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
								<div className="flex items-center justify-between">
									<div className="text-sm text-blue-800">
										<span className="font-medium">{selectedCount}</span> of {totalTools} items selected
									</div>
									<div className="text-sm text-blue-800 font-medium">
										Est. cost: ${totalMin.toFixed(0)}
									</div>
								</div>
							</div>
						</div>
					)}

					{/* Filter Buttons and Action Buttons - Normal flow */}
					<div className="space-y-3">
						{/* Filter Buttons Row */}
						<div className="flex gap-2">
							<button
								onClick={() => setActiveFilter("all")}
								className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
									activeFilter === "all"
										? "bg-blue-600 text-white"
										: "bg-gray-200 text-gray-700 hover:bg-gray-300"
								}`}
							>
								All Items
							</button>
							<button
								onClick={() => setActiveFilter("required")}
								className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
									activeFilter === "required"
										? "bg-blue-600 text-white"
										: "bg-gray-200 text-gray-700 hover:bg-gray-300"
								}`}
							>
								Required
							</button>
							<button
								onClick={() => setActiveFilter("optional")}
								className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
									activeFilter === "optional"
										? "bg-blue-600 text-white"
										: "bg-gray-200 text-gray-700 hover:bg-gray-300"
								}`}
							>
								Optional
							</button>
						</div>
						
						{/* Action Buttons Row */}
						<div className="flex gap-2">
							{/* View Cost Button - Always Visible */}
							<button
								onClick={() => {
									if (!isSelectionMode) {
										// Enable selection mode
										setIsSelectionMode(true);
										console.log("Selection mode enabled");
									} else {
										// Toggle back to selection mode (deselect all and go back)
										setIsSelectionMode(false);
										setSelectedTools(new Set());
										console.log("Selection mode disabled, back to Select Tools");
									}
								}}
								className={`px-4 py-1.5 text-xs font-medium rounded-lg transition-colors ${
									isSelectionMode 
										? "bg-green-600 text-white hover:bg-green-700" 
										: "bg-gray-200 text-black hover:bg-gray-300"
								}`}
							>
								{isSelectionMode ? "View Cost" : "Select Tools"}
							</button>
							
							{/* Clear All Button - Only visible in selection mode */}
							{isSelectionMode && selectedCount > 0 && (
								<button
									onClick={() => {
										console.log("Clearing all selections");
										setSelectedTools(new Set());
									}}
									className="px-3 py-1.5 bg-red-500 text-white text-xs font-medium rounded-lg hover:bg-red-600 transition-colors"
								>
									Clear All
								</button>
							)}
						</div>
					</div>

					
					{/* Tools Grid */}
					{filteredTools.length > 0 ? (
						<ToolsGrid 
							tools={filteredTools} 
							selectedTools={selectedTools}
							onToolSelection={handleToolSelection}
							isSelectionMode={isSelectionMode}
						/>
					) : (
						<div className="text-center py-6 mt-20">
							<div className="text-gray-500 mb-2">
								{activeFilter === "all" 
									? "No tools information available"
									: `No ${activeFilter} tools found`
								}
							</div>
							<div className="text-xs text-gray-400">
								{activeFilter === "all" 
									? "Tools will be populated once project details are generated"
									: "Try selecting a different filter or check back later"
								}
							</div>
						</div>
					)}
				</div>
			</ToolsLayout>
		</MobileWrapper>
	);
}
