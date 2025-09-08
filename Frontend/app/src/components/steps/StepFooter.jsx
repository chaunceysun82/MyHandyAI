import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { toggleStepCompletion } from "../../services/steps";
import { completeProject } from "../../services/projects";
import ChatWindow2 from "../Chat/ChatWindow2";
import {ReactComponent as Bot} from '../../assets/Bot.svg';

export default function StepFooter({ 
	projectId, 
	projectName, 
	stepNumber, 
	stepTitle, 
	totalSteps,
	projectVideoUrl,
	onPrev, 
	onNext,
	userId,
	userName, // Add userName prop
	isPrevDisabled = false,
	isNextDisabled = false,
	isNextFinal = false,
	allSteps = [], // Add this prop to check step completion
	currentStepIndex = 0, // Add this prop to know current step position
	onStepUpdate = null // Add this prop to refresh step data after completion
}) {
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
	const navigate = useNavigate();
	const [showProjectCompletionModal, setShowProjectCompletionModal] = useState(false);
	const [isCompleting, setIsCompleting] = useState(false);
	const [openModal, setOpenModal] = useState(false);

	const URL = process.env.REACT_APP_BASE_URL;
	
	console.log("User ID:", userId);

	// Check if all instruction steps are completed (excluding tools step)
	const checkAllStepsCompleted = () => {
		console.log("StepFooter: checkAllStepsCompleted called with allSteps:", allSteps);
		console.log("StepFooter: allSteps type:", typeof allSteps);
		console.log("StepFooter: allSteps length:", allSteps?.length);
		console.log("StepFooter: allSteps structure:", JSON.stringify(allSteps, null, 2));
		
		if (!allSteps || allSteps.length === 0) {
			console.log("StepFooter: No steps data available");
			return false;
		}
		
		// Check all instruction steps (skip tools step at index 0)
		for (let i = 1; i < allSteps.length; i++) {
			const step = allSteps[i];
			console.log(`StepFooter: Checking step ${i}:`, step);
			console.log(`StepFooter: Step ${i} completed property:`, step?.completed);
			console.log(`StepFooter: Step ${i} full structure:`, JSON.stringify(step, null, 2));
			
			if (!step) {
				console.log(`StepFooter: Step ${i} is undefined`);
				return false;
			}
			
			if (!step.completed) {
				console.log(`StepFooter: Step ${i} is not completed, returning false`);
				return false;
			}
		}
		console.log("StepFooter: All steps are completed, returning true");
		return true;
	};

	// Complete all remaining steps before finishing project
	const completeAllRemainingSteps = async () => {
		setIsCompleting(true);
		try {
			console.log("StepFooter: Starting to complete all remaining steps");
			console.log("StepFooter: allSteps array:", allSteps);
			console.log("StepFooter: allSteps type:", typeof allSteps);
			console.log("StepFooter: allSteps length:", allSteps?.length);
			console.log("StepFooter: allSteps structure:", JSON.stringify(allSteps, null, 2));
			console.log("StepFooter: currentStepIndex:", currentStepIndex);
			console.log("StepFooter: projectId:", projectId);
			
			// Get all steps that need to be completed
			const stepsToComplete = [];
			
			// Check all instruction steps (skip tools step at index 0)
			for (let i = 1; i < allSteps.length; i++) {
				const step = allSteps[i];
				console.log(`StepFooter: Checking step ${i}:`, step);
				console.log(`StepFooter: Step ${i} completed property:`, step?.completed);
				console.log(`StepFooter: Step ${i} full structure:`, JSON.stringify(step, null, 2));
				
				if (!step?.completed) {
					// Calculate the actual step number for the API call
					// If this is step index 1, it should be step number 2 in the backend
					const stepNumber = i + 1;
					stepsToComplete.push(stepNumber);
					console.log(`StepFooter: Step ${i} (backend step ${stepNumber}) needs completion`);
				} else {
					console.log(`StepFooter: Step ${i} is already completed`);
				}
			}
			
			console.log("StepFooter: Steps to complete:", stepsToComplete);
			
			if (stepsToComplete.length === 0) {
				console.log("StepFooter: No steps need completion, all are already done");
			} else {
				// Mark all incomplete steps as completed
				for (const stepNumber of stepsToComplete) {
					console.log(`StepFooter: Marking step ${stepNumber} as completed`);
					try {
						const result = await toggleStepCompletion(projectId, stepNumber);
						console.log(`StepFooter: Step ${stepNumber} completion result:`, result);
					} catch (stepError) {
						console.error(`StepFooter: Error completing step ${stepNumber}:`, stepError);
						// Continue with other steps even if one fails
					}
				}
			}
			
			// Refresh step data if callback provided
			if (onStepUpdate) {
				console.log("StepFooter: Refreshing step data");
				onStepUpdate();
			}
			
			// Call the project completion API to mark entire project as complete
			console.log("StepFooter: Marking entire project as complete via API...");
			try {
				await completeProject(projectId);
				console.log("StepFooter: Project completion API call successful");
			} catch (apiError) {
				console.error("StepFooter: Error calling project completion API:", apiError);
				// Continue with navigation even if API fails
				alert('Warning: Project completion API failed, but steps were completed. You may need to refresh the page.');
			}
			
			console.log("StepFooter: All steps completed, navigating to project completion");
			// Navigate to project completion page
			navigate(`/projects/${projectId}/completed`);
			
		} catch (error) {
			console.error('Error completing all steps:', error);
			alert('Failed to complete all steps. Please try again.');
		} finally {
			setIsCompleting(false);
			setShowProjectCompletionModal(false);
		}
	};

	const handleChatClick = () => {
		// navigate("/chat", { 
		// 	state: { 
		// 		projectId, 
		// 		projectName: projectName || "Project",
		// 		from: "step",
		// 		stepNumber: stepNumber,
		// 		stepTitle: stepTitle
		// 	}
		// });
		setOpenModal(true);
	};

	const handlePrevClick = () => {
		onPrev();
	};

	const handleNextClick = () => {
		console.log("StepFooter: handleNextClick called", {
			isNextFinal,
			allSteps,
			currentStepIndex,
			projectId
		});
		
		if (isNextFinal) {
			console.log("StepFooter: This is the final step, showing project completion confirmation");
			// This is the final step - show project completion confirmation modal
			setShowProjectCompletionModal(true);
		} else {
			console.log("StepFooter: Normal next step navigation");
			// Normal next step navigation
			onNext();
		}
	};

	const handleProjectCompletionConfirm = () => {
		console.log("StepFooter: User confirmed project completion");
		// Complete all remaining steps and finish project
		completeAllRemainingSteps();
	};

	const handleProjectCompletionCancel = () => {
		console.log("StepFooter: User cancelled project completion");
		setShowProjectCompletionModal(false);
	};

	// Add effect to log modal state changes
	useEffect(() => {
		console.log("StepFooter: Project completion modal state changed:", showProjectCompletionModal);
	}, [showProjectCompletionModal]);

	return (
		<>
			<div className="px-4 pb-4 space-y-3 border-t bg-white">
				{/* Assistant prompt pill */}
			<button onClick={handleChatClick} className="rounded-xl w-full shadow-xl border justify-center items-center gap-[10px] flex border-gray-200 bg-[#1484A3] transition-all ease-in-out duration-200 hover:bg-[#026e8c] px-3 py-2 mt-2 text-[12px] text-white font-light">
				<Bot width = {20} height = {20} />
				<span>Hi {getFirstName(userName)}, Need MyHandyAI Assistant?</span>
			</button>

			{openModal && (
				<ChatWindow2
					isOpen={openModal}
					projectId={projectId}
					onClose={() => setOpenModal(false)}
					URL={URL}
					stepNumber={stepNumber}
					userName={userName}
				/>
			)}

				{/* Bottom Navigation */}
				<div className="grid grid-cols-2 gap-3">
					<button
						onClick={handlePrevClick}
						disabled={isPrevDisabled}
						className={`py-2 rounded-lg font-regular ${
							isPrevDisabled
								? "bg-gray-100 text-gray-400 cursor-not-allowed"
								: "bg-[#E9FAFF] text-[12px] shadow-md hover:bg-[#d9f7ff] transition-all erase-in-out duration-300"
						}`}>
						Previous
					</button>
					<button
						onClick={handleNextClick}
						disabled={isNextDisabled || isCompleting}
						className={`py-2 rounded-lg font-regular ${
							isNextDisabled || isCompleting
								? "bg-gray-100 text-gray-400 cursor-not-allowed"
								: "bg-[#E9FAFF] text-[12px] text-black shadow-md hover:bg-[#d9f7ff] transition-all erase-in-out duration-300"
						}`}>
						{isCompleting ? "Completing..." : (isNextFinal ? "Finish" : "Next Step")}
					</button>
				</div>
			</div>

			{/* Project Completion Confirmation Modal */}
			{console.log("StepFooter: Rendering project completion modal with showProjectCompletionModal:", showProjectCompletionModal)}
			{showProjectCompletionModal && (
				<div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
					<div className="bg-white rounded-lg p-4 max-w-xs w-full mx-4">
						{/* Header */}
						<div className="text-center mb-3">
							<div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-2">
								<span className="text-xl">🎉</span>
							</div>
							<h3 className="text-base font-semibold text-gray-900 mb-1">
								Ready to Finish Project?
							</h3>
							<p className="text-xs text-gray-600 leading-relaxed">
								{checkAllStepsCompleted() 
									? "All steps are completed! Ready to finish this project?"
									: "Some steps are not completed yet. Would you like to mark all remaining steps as complete and finish the project?"
								}
							</p>
						</div>

						{/* Buttons */}
						<div className="flex gap-2">
							<button
								onClick={handleProjectCompletionCancel}
								disabled={isCompleting}
								className="flex-1 py-2 px-3 border border-gray-300 rounded-lg text-xs font-medium text-gray-700 hover:bg-gray-50 transition-colors disabled:opacity-50"
							>
								No, Go Back
							</button>
							<button
								onClick={handleProjectCompletionConfirm}
								disabled={isCompleting}
								className="flex-1 py-2 px-3 bg-green-600 text-white rounded-lg text-xs font-medium hover:bg-green-700 transition-colors disabled:opacity-50"
							>
								{isCompleting ? "Completing..." : "Yes, Finish Project"}
							</button>
						</div>
					</div>
				</div>
			)}
		</>
	);
}
