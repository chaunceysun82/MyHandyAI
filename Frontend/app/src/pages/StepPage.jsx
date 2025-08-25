import React, { useEffect, useState } from "react";
import { useLocation, useParams, useNavigate } from "react-router-dom";
import MobileWrapper from "../components/MobileWrapper";
import StepHeader from "../components/steps/StepHeader";
import StepFooter from "../components/steps/StepFooter";
import StepTimeEstimate from "../components/steps/StepTimeEstimate";
import StepMediaGuide from "../components/steps/StepMediaGuide";
import StepInstructions from "../components/steps/StepInstructions";
import StepToolsNeeded from "../components/steps/StepToolsNeeded";
import StepSafetyWarnings from "../components/steps/StepSafetyWarnings";
import StepTips from "../components/steps/StepTips";
import StepCompletionConfirmation from "../components/steps/StepCompletionConfirmation";
import { fetchSteps } from "../services/overview";
import { 
	extractSpecificStep, 
	transformStepData 
} from "../utilities/StepUtils";
import LoadingPlaceholder from "../components/LoadingPlaceholder";

export default function StepPage() {
	const { stepIndex, projectId } = useParams();
	const { state } = useLocation();
	const navigate = useNavigate();
	const [step, setStep] = useState(null);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState("");
	const [allSteps, setAllSteps] = useState([]);
	
	// Get the project video URL from navigation state
	const projectVideoUrl = state?.projectVideoUrl;
	
	// Debug: Log what we received from navigation
	console.log("StepPage: Received navigation state:", state);
	console.log("StepPage: Project video URL:", projectVideoUrl);

	// Function to refresh step data after completion updates
	const refreshStepData = async () => {
		try {
			const stepsData = await fetchSteps(projectId);
			if (stepsData) {
				setAllSteps(stepsData);
				
				// Update current step data
				const stepNumber = parseInt(stepIndex) || 1;
				const actualStepIndex = stepNumber - 1;
				const specificStep = extractSpecificStep(stepsData, actualStepIndex);
				
				if (specificStep) {
					const transformedStep = transformStepData(specificStep, stepNumber, stepsData);
					setStep(transformedStep);
				}
			}
		} catch (err) {
			console.error("Error refreshing step data:", err);
		}
	};

	// Fetch step data from backend using project_id and step number
	useEffect(() => {
		let cancelled = false;

		const fetchStepData = async () => {
			try {
				setLoading(true);
				setError("");

				// Fetch all steps data for the project
				const stepsData = await fetchSteps(projectId);
				
				if (cancelled) return;

				if (!stepsData) {
					setError("No steps data available for this project");
					setLoading(false);
					return;
				}

				// Store all steps for validation
				setAllSteps(stepsData);

				// Calculate the actual step index based on URL stepIndex
				// URL stepIndex 1 = first actual project step (index 0 in backend)
				// URL stepIndex 2 = second actual project step (index 1 in backend)
				const stepNumber = parseInt(stepIndex) || 1;
				const actualStepIndex = stepNumber - 1; // Convert UI step number to backend index
				
				console.log("StepPage: UI Step Number:", stepNumber);
				console.log("StepPage: Actual Step Index for API:", actualStepIndex);
				console.log("StepPage: Backend steps data:", stepsData);
				console.log("StepPage: Backend steps length:", Array.isArray(stepsData) ? stepsData.length : 'Not an array');
				
				// Get the specific step data using the calculated index
				const specificStep = extractSpecificStep(stepsData, actualStepIndex);
				
				if (specificStep) {
					console.log("StepPage: Extracted step data:", specificStep);
					console.log("StepPage: Step title:", specificStep.title);
					console.log("StepPage: Step instructions:", specificStep.instructions);
					
					// Transform the step data for display
					const transformedStep = transformStepData(specificStep, stepNumber, stepsData);
					console.log("StepPage: Transformed step data:", transformedStep);
					console.log("StepPage: Formatted instructions:", transformedStep.instructions);
					console.log("StepPage: Formatted tools:", transformedStep.toolsNeeded);
					console.log("StepPage: Formatted safety:", transformedStep.safety);
					console.log("StepPage: Formatted tips:", transformedStep.tips);
					
					setStep(transformedStep);
				} else {
					console.error("StepPage: Step not found at index:", actualStepIndex);
					console.error("StepPage: Available steps:", stepsData);
					setError(`Step ${stepNumber} not found`);
				}
				
			} catch (err) {
				if (!cancelled) {
					console.error("StepPage: Error fetching step data:", err);
					setError("Failed to load step details. Please try again.");
				}
			} finally {
				if (!cancelled) {
					setLoading(false);
				}
			}
		};

		fetchStepData();

		return () => {
			cancelled = true;
		};
	}, [projectId, stepIndex]);

	const handleBack = () => {
		// Always go back to Project Overview from any step page
		navigate(`/projects/${projectId}/overview`, {
			state: {
				projectId,
				projectName: state?.projectName || "Project",
				projectVideoUrl: projectVideoUrl
			}
		});
	};

	const handlePrev = () => {
		// Get current step number from URL params
		const currentStepFromURL = parseInt(stepIndex);
		
		// If we're on step 1, go to tools page
		// If we're on any other step, go to previous step
		if (currentStepFromURL === 1) {
			navigate(`/projects/${projectId}/tools`, {
				state: {
					projectId,
					projectName: state?.projectName || "Project",
					projectVideoUrl: projectVideoUrl
				}
			});
		} else {
			// Navigate to previous step
			const prevStepNumber = currentStepFromURL - 1;
			navigate(`/projects/${projectId}/steps/${prevStepNumber}`, {
				state: {
					projectId,
					projectName: state?.projectName || "Project",
					projectVideoUrl: projectVideoUrl
				}
			});
		}
	};

	const handleNext = () => {
		// Navigate to next step
		const currentStepNumber = parseInt(stepIndex);
		const totalSteps = step?.total || 0;
		const backendStepsCount = totalSteps - 1; // Subtract 1 because we added Tools step
		
		console.log("StepPage: handleNext called with:", {
			currentStepNumber,
			totalSteps,
			backendStepsCount,
			isLastStep: currentStepNumber >= backendStepsCount
		});
		
		if (currentStepNumber >= backendStepsCount) {
			// This is the last step, go to Project Completed page
			console.log("StepPage: Navigating to Project Completed page");
			navigate(`/projects/${projectId}/completed`, {
				state: {
					projectId,
					projectName: state?.projectName || "Project",
					projectVideoUrl: projectVideoUrl
				}
			});
		} else {
			// Navigate to next step
			const nextStepNumber = currentStepNumber + 1;
			console.log("StepPage: Navigating to next step:", nextStepNumber);
			navigate(`/projects/${projectId}/steps/${nextStepNumber}`, {
				state: {
					projectId,
					projectName: state?.projectName || "Project",
					projectVideoUrl: projectVideoUrl
				}
			});
		}
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
				<div className="min-h-screen flex items-center justify-center">
					<div className="text-center max-w-sm mx-auto px-4">
						<div className="text-red-500 text-6xl mb-4">⚠️</div>
						<h2 className="text-lg font-semibold text-gray-900 mb-2">Something went wrong</h2>
						<p className="text-gray-600 mb-6">{error}</p>
						<div className="space-y-3">
							<button 
								onClick={() => window.location.reload()} 
								className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
							>
								Try Again
							</button>
							<button 
								onClick={handleBack} 
								className="w-full px-4 py-2 bg-gray-200 text-gray-800 rounded-lg hover:bg-gray-300"
							>
								Go Back
							</button>
						</div>
					</div>
				</div>
			</MobileWrapper>
		);
	}

	if (!step) {
		return (
			<MobileWrapper>
				<div className="min-h-screen flex items-center justify-center">
					<div className="text-center">
						<p className="text-gray-600 mb-4">Step not found</p>
						<button onClick={handleBack} className="px-4 py-2 bg-blue-600 text-white rounded-lg">
							Go Back
						</button>
					</div>
				</div>
			</MobileWrapper>
		);
	}

	return (
		<MobileWrapper>
			<div className="flex flex-col h-screen bg-gray-50">
				{/* Header - Fixed at top */}
				<StepHeader
					stepNumber={parseInt(stepIndex)}
					totalSteps={step.total - 1}
					title={step.title}
					onBack={handleBack}
				/>

				{/* Main Content - Scrollable */}
				<main className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
					{/* Time Estimate */}
					<StepTimeEstimate time={step.time} completed={step.completed} />

					{/* Media Guide Section - Video and Image */}
					<StepMediaGuide 
						videoUrl={projectVideoUrl} 
						imageData={step.image || step.imageData || step.image_data} 
						title="Step Guide" 
					/>
					{/* Debug: Log step data for media */}
					{console.log("StepPage: Step data for media:", { 
						videoUrl: projectVideoUrl, 
						imageData: step.image || step.imageData || step.image_data,
						projectVideoUrl: projectVideoUrl,
						stepTitle: step.title,
						fullStep: step,
						stepImage: step.image,
						stepImageData: step.imageData,
						stepImageDataAlt: step.image_data
					})}

					{/* Instructions */}
					<StepInstructions instructions={step.instructions} />

					{/* Tools Needed */}
					<StepToolsNeeded toolsNeeded={step.toolsNeeded} />

					{/* Safety Warnings */}
					<StepSafetyWarnings safety={step.safety} />

					{/* Pro Tips */}
					<StepTips tips={step.tips} />

					{/* Step Completion Confirmation */}
					<StepCompletionConfirmation 
						projectId={projectId} 
						stepNumber={step.number} 
						stepCompleted={step.completed}
						allSteps={allSteps}
						currentStepIndex={parseInt(stepIndex)}
						onStepUpdate={refreshStepData}
						onProjectComplete={() => navigate(`/projects/${projectId}/completed`)}
					/>
				</main>

				{/* Footer - Fixed at bottom */}
				<StepFooter
					projectId={projectId}
					projectName={state?.projectName || "Project"}
					stepNumber={parseInt(stepIndex) + 1}
					stepTitle={step?.title || ""}
					totalSteps={step?.total || 0}
					projectVideoUrl={projectVideoUrl}
					onPrev={handlePrev}
					onNext={handleNext}
					isPrevDisabled={false}
					isNextDisabled={false}
					isNextFinal={(() => {
						if (!step || !step.total) return false;
						
						const currentStepNumber = parseInt(stepIndex);
						const backendStepsCount = step.total - 1; // Subtract 1 because we added Tools step
						const isLast = currentStepNumber >= backendStepsCount;
						
						console.log("StepPage: isNextFinal calculation:", {
							currentStepNumber,
							backendStepsCount,
							totalSteps: step.total,
							isLast
						});
						
						return isLast;
					})()}
					allSteps={allSteps}
					currentStepIndex={parseInt(stepIndex)}
					onStepUpdate={refreshStepData}
				/>
			</div>
		</MobileWrapper>
	);
}
