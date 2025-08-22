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
	
	// Get the project video URL from navigation state
	const projectVideoUrl = location.state?.projectVideoUrl;

	// const userId = location.state?.userId;
	// console.log("User ID:", userId);

	useEffect(() => {
		const fetchData = async () => {
			try {
				setLoading(true);
				setError("");
				
				// Fetch both tools and steps data
				const [toolsData, stepsData] = await Promise.all([
					fetchProjectTools(projectId),
					fetchSteps(projectId)
				]);

				// Process tools data
				if (toolsData && toolsData.tools_data && toolsData.tools_data.tools) {
					setRawData(toolsData);
					const transformedTools = transformToolsData(toolsData);
					setTools(transformedTools);
				} else if (toolsData && Array.isArray(toolsData) && toolsData.length > 0) {
					setRawData(toolsData);
					setTools(toolsData);
				} else {
					console.log("No tools found in backend, using mock data");
					setTools(mockTools);
				}

				// Process steps data to get total count
				if (stepsData) {
					let backendSteps = 0;
					if (Array.isArray(stepsData)) {
						backendSteps = stepsData.length;
					} else if (stepsData?.steps_data?.steps && Array.isArray(stepsData.steps_data.steps)) {
						backendSteps = stepsData.steps_data.steps.length;
					} else if (stepsData?.steps && Array.isArray(stepsData.steps)) {
						backendSteps = stepsData.steps.length;
					}
					// Add 1 for the "Tools Required" step that's always shown first
					setTotalSteps(backendSteps + 1);
				}

			} catch (err) {
				console.error("Error fetching data from backend:", err);
				// Fallback to mock data for development
				console.log("Using mock tools data as fallback");
				setTools(mockTools);
				setTotalSteps(5); // Default fallback
			} finally {
				setLoading(false);
			}
		};

		fetchData();
	}, [projectId]);

	const handleBack = () => {
		navigate(`/projects/${projectId}/overview`, {
			state: {
				projectId,
				projectName: location.state?.projectName || "Project",
				projectVideoUrl: projectVideoUrl
			}
		});
	};

	const handlePrev = () => {
		// Navigate back to Project Overview since Tools is the first step
		navigate(`/projects/${projectId}/overview`, {
			state: {
				projectId,
				projectName: location.state?.projectName || "Project",
				projectVideoUrl: projectVideoUrl
			}
		});
	};

	const handleNext = () => {
		// Navigate to the first actual step (step 1, since tools is step 0)
		navigate(`/projects/${projectId}/steps/1`, { state: { projectVideoUrl } });
	};

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
				title="Tools Required"
				onBack={handleBack}
				onPrev={handlePrev}
				onNext={handleNext}
				projectId={projectId}
				projectName={location.state?.projectName || "Project"}
				projectVideoUrl={projectVideoUrl}
			>
				<div className="space-y-4">
					{/* Video Guide Section
					{projectVideoUrl && (
						<StepVideoGuide videoUrl={projectVideoUrl} title="Project Video Guide" />
					)} */}
					
					{/* Tools Grid */}
					{tools.length > 0 ? (
						<ToolsGrid tools={tools} />
					) : (
						<div className="text-center py-6">
							<div className="text-gray-500 mb-2">No tools information available</div>
							<div className="text-xs text-gray-400">
								Tools will be populated once project details are generated
							</div>
						</div>
					)}
				</div>
			</ToolsLayout>
		</MobileWrapper>
	);
}
