import React, { useState } from "react";
import { toggleStepCompletion } from "../../services/steps";
import { completeProject } from "../../services/projects";
import StepValidationModal from "./StepValidationModal";

export default function StepCompletionConfirmation({ 
	projectId, 
	stepNumber, 
	stepCompleted, 
	allSteps, 
	currentStepIndex,
	onStepUpdate,
	onProjectComplete // New prop for navigation to project completion
}) {
	// Debug logging for allSteps
	console.log('StepCompletionConfirmation: allSteps prop:', {
		allSteps,
		isArray: Array.isArray(allSteps),
		length: Array.isArray(allSteps) ? allSteps.length : 'N/A',
		type: typeof allSteps
	});

	const [showValidationModal, setShowValidationModal] = useState(false);
	const [validationType, setValidationType] = useState(null); // 'previous' or 'final'
	const [pendingAction, setPendingAction] = useState(null);
	const [showCongratulatoryCard, setShowCongratulatoryCard] = useState(false);
	const [completedStepData, setCompletedStepData] = useState(null);

	// Check if previous steps are completed
	const checkPreviousStepsCompleted = () => {
		// Handle different data structures from the API
		let stepsArray = [];
		
		if (Array.isArray(allSteps)) {
			stepsArray = allSteps;
		} else if (allSteps?.steps_data?.steps && Array.isArray(allSteps.steps_data.steps)) {
			stepsArray = allSteps.steps_data.steps;
		} else if (allSteps?.steps && Array.isArray(allSteps.steps)) {
			stepsArray = allSteps.steps;
		}
		
		if (stepsArray.length === 0) {
			console.warn('No steps data available:', allSteps);
			return true; // Default to true to avoid blocking completion
		}
		
		if (currentStepIndex <= 1) return true; // First step, no previous steps to check
		
		// Check previous steps (currentStepIndex is 1-based, so check from 0 to currentStepIndex-2)
		for (let i = 0; i < currentStepIndex - 1; i++) {
			if (!stepsArray[i]?.completed) {
				return false;
			}
		}
		return true;
	};

	// Check if this is the final step
	const isFinalStep = () => {
		// Handle different data structures from the API
		let stepsArray = [];
		
		if (Array.isArray(allSteps)) {
			stepsArray = allSteps;
		} else if (allSteps?.steps_data?.steps && Array.isArray(allSteps.steps_data.steps)) {
			stepsArray = allSteps.steps_data.steps;
		} else if (allSteps?.steps && Array.isArray(allSteps.steps)) {
			stepsArray = allSteps.steps;
		}
		
		if (stepsArray.length === 0) {
			console.warn('No steps data available:', allSteps);
			return false;
		}

		console.log('isFinalStep check:', {
			currentStepIndex,
			stepsArrayLength: stepsArray.length
		});

		console.log('Steps Array:', stepsArray.map((s, i) => ({ index: i, title: s.title, completed: s.completed })));
		
		// Check if current step is the last step (currentStepIndex is 1-based)
		return currentStepIndex === stepsArray.length;
	};

	// Check if all steps are completed
	const checkAllStepsCompleted = () => {
		// Handle different data structures from the API
		let stepsArray = [];
		
		if (Array.isArray(allSteps)) {
			stepsArray = allSteps;
		} else if (allSteps?.steps_data?.steps && Array.isArray(allSteps.steps_data.steps)) {
			stepsArray = allSteps.steps_data.steps;
		} else if (allSteps?.steps && Array.isArray(allSteps.steps)) {
			stepsArray = allSteps.steps;
		}
		
		if (stepsArray.length === 0) {
			console.warn('No steps data available:', allSteps);
			return false;
		}
		
		// Check all steps
		for (let i = 0; i < stepsArray.length; i++) {
			if (!stepsArray[i]?.completed) {
				return false;
			}
		}
		return true;
	};

	// Calculate remaining steps for congratulatory message
	const getRemainingStepsInfo = () => {
		// Handle different data structures from the API
		let stepsArray = [];
		
		if (Array.isArray(allSteps)) {
			stepsArray = allSteps;
		} else if (allSteps?.steps_data?.steps && Array.isArray(allSteps.steps_data.steps)) {
			stepsArray = allSteps.steps_data.steps;
		} else if (allSteps?.steps && Array.isArray(allSteps.steps)) {
			stepsArray = allSteps.steps;
		}
		
		if (stepsArray.length === 0) {
			return { remaining: 0, total: 0 };
		}
		
		// Count instruction steps (the stepsArray contains only instruction steps, no tools step)
		let remaining = 0;
		let total = stepsArray.length;
		
		// Count remaining steps (excluding current step since it's being completed)
		// Note: currentStepIndex is 1-based from URL, but stepsArray is 0-based
		const actualCurrentIndex = currentStepIndex - 1;
		
		for (let i = 0; i < stepsArray.length; i++) {
			if (!stepsArray[i]?.completed && i !== actualCurrentIndex) {
				remaining++;
			}
		}
		
		console.log("🎯 getRemainingStepsInfo debug:", {
			stepsArrayLength: stepsArray.length,
			currentStepIndex,
			actualCurrentIndex,
			total,
			remaining,
			stepsArray: stepsArray.map((s, i) => ({ index: i, title: s.title, completed: s.completed }))
		});
		
		return { remaining, total };
	};

	// Show congratulatory card when step is completed
	const showCongratulatoryMessage = (stepTitle) => {
		const { remaining, total } = getRemainingStepsInfo();
		// Check if this is the final step BEFORE completion
		const isFinalStepCompleted = isFinalStep();
		// Calculate current step number correctly (currentStepIndex is 1-based from URL)
		const currentStepNumber = currentStepIndex;
		
		console.log("🎉 Step completion debug:", {
			currentStepIndex,
			currentStepNumber,
			remaining,
			total,
			isFinalStepCompleted,
			stepTitle,
			allStepsLength: Array.isArray(allSteps) ? allSteps.length : 'Not an array',
			allStepsStructure: allSteps
		});
		
		// Get next step title
		let nextStepTitle = null;
		if (!isFinalStepCompleted) {
			// Handle different data structures from the API
			let stepsArray = [];
			
			if (Array.isArray(allSteps)) {
				stepsArray = allSteps;
			} else if (allSteps?.steps_data?.steps && Array.isArray(allSteps.steps_data.steps)) {
				stepsArray = allSteps.steps_data.steps;
			} else if (allSteps?.steps && Array.isArray(allSteps.steps)) {
				stepsArray = allSteps.steps;
			}
			
			const nextStepIndex = currentStepIndex; // currentStepIndex is 1-based, next step is at same index
			if (nextStepIndex < stepsArray.length) {
				nextStepTitle = stepsArray[nextStepIndex]?.title || `Step ${nextStepIndex + 1}`;
			}
		}
		
		setCompletedStepData({
			stepTitle,
			stepNumber: currentStepNumber,
			total,
			nextStepTitle,
			isFinalStep: isFinalStepCompleted
		});
		setShowCongratulatoryCard(true);
		
		// Auto-hide after 3 seconds
		setTimeout(() => {
			setShowCongratulatoryCard(false);
			// If this is the final step, navigate to project completion
			if (isFinalStepCompleted && onProjectComplete) {
				console.log('Navigating to project completion page...', {
					stepTitle,
					stepNumber: currentStepNumber,
					total,
					nextStepTitle,
					isFinalStep: isFinalStepCompleted
				});
				onProjectComplete();
			}
		}, 4000);
	};

	// Complete all remaining steps and finish project
	const completeAllStepsAndFinish = async () => {
		try {
			// Handle different data structures from the API
			let allStepsArray = [];
			
			if (Array.isArray(allSteps)) {
				allStepsArray = allSteps;
			} else if (allSteps?.steps_data?.steps && Array.isArray(allSteps.steps_data.steps)) {
				allStepsArray = allSteps.steps_data.steps;
			} else if (allSteps?.steps && Array.isArray(allSteps.steps)) {
				allStepsArray = allSteps.steps;
			}
			
			if (allStepsArray.length === 0) {
				console.warn('No steps data available:', allSteps);
				// Just complete the current step if allSteps is invalid
				await toggleStepCompletion(projectId, stepNumber);
				if (onStepUpdate) onStepUpdate();
				if (onProjectComplete) onProjectComplete();
				return;
			}
			
			// Mark all incomplete steps as completed
			for (let i = 0; i < allStepsArray.length; i++) {
				if (!allStepsArray[i]?.completed) {
					await toggleStepCompletion(projectId, i + 1); // Step numbers are 1-based
				}
			}
			
			// Mark current step as completed
			await toggleStepCompletion(projectId, stepNumber);
			
			// Call the project completion API to mark entire project as complete
			console.log('Marking entire project as complete via API...');
			try {
				await completeProject(projectId);
				console.log('Project completion API call successful');
			} catch (apiError) {
				console.error('Error calling project completion API:', apiError);
				// Continue with navigation even if API fails
				alert('Warning: Project completion API failed, but steps were completed. You may need to refresh the page.');
			}
			
			// Close modal and update UI
			setShowValidationModal(false);
			if (onStepUpdate) onStepUpdate();
			
			// Show congratulatory message for final step completion
			// Handle different data structures from the API
			let finalStepsArray = [];
			if (Array.isArray(allSteps)) {
				finalStepsArray = allSteps;
			} else if (allSteps?.steps_data?.steps && Array.isArray(allSteps.steps_data.steps)) {
				finalStepsArray = allSteps.steps_data.steps;
			} else if (allSteps?.steps && Array.isArray(allSteps.steps)) {
				finalStepsArray = allSteps.steps;
			}
			
			const actualStepIndex = currentStepIndex - 1; // Convert 1-based to 0-based
			const stepTitle = finalStepsArray[actualStepIndex]?.title || `Step ${stepNumber}`;
			showCongratulatoryMessage(stepTitle);
			
			// Navigate to project completion page after a short delay
			setTimeout(() => {
				if (onProjectComplete) {
					onProjectComplete();
				}
			}, 3000); // Show congratulatory card for 3 seconds before navigating
			
		} catch (error) {
			console.error('Error completing all steps:', error);
			alert('Failed to complete all steps. Please try again.');
		}
	};

	const handleStepComplete = async () => {
		try {
			if (stepCompleted) {
				console.log(`Project ID: ${projectId}, Step ${stepNumber} - Undoing completion`);
				await toggleStepCompletion(projectId, stepNumber);
				if (onStepUpdate) onStepUpdate();
			} else {
				console.log(`Project ID: ${projectId}, Step ${stepNumber} is complete`);
				
				// Check if previous steps are completed
				const previousStepsCompleted = checkPreviousStepsCompleted();
				
				if (!previousStepsCompleted) {
					// Show validation modal for incomplete previous steps
					setValidationType('previous');
					setPendingAction(() => () => completeStepWithPrevious());
					setShowValidationModal(true);
					console.log('Previous steps validation modal shown');
					return;
				}

				// Check if this is the final step
				if (isFinalStep()) {
					// Show final step warning
					setValidationType('final');
					setPendingAction(() => () => completeAllStepsAndFinish());
					setShowValidationModal(true);
					console.log('Final step validation modal shown');
					return;
				}

				// Normal step completion
				await toggleStepCompletion(projectId, stepNumber);
				if (onStepUpdate) onStepUpdate();
				
				// Show congratulatory message
				// Handle different data structures from the API
				let normalStepsArray = [];
				if (Array.isArray(allSteps)) {
					normalStepsArray = allSteps;
				} else if (allSteps?.steps_data?.steps && Array.isArray(allSteps.steps_data.steps)) {
					normalStepsArray = allSteps.steps_data.steps;
				} else if (allSteps?.steps && Array.isArray(allSteps.steps)) {
					normalStepsArray = allSteps.steps;
				}
				
				console.log('🎯 handleStepComplete debug:', {
					normalStepsArray,
					currentStepIndex,
					stepNumber
				});
				// Show congratulatory message
				const actualStepIndex = currentStepIndex - 1; // Convert 1-based to 0-based
				const stepTitle = normalStepsArray[actualStepIndex]?.title || `Step ${stepNumber}`;
				showCongratulatoryMessage(stepTitle);
			}
		} catch (error) {
			console.error('Error toggling step completion:', error);
			alert('Failed to update step completion. Please try again.');
		}
	};

	// Complete current step and mark previous incomplete steps as completed
	const completeStepWithPrevious = async () => {
		try {
			// Handle different data structures from the API
			let previousStepsArray = [];
			
			if (Array.isArray(allSteps)) {
				previousStepsArray = allSteps;
			} else if (allSteps?.steps_data?.steps && Array.isArray(allSteps.steps_data.steps)) {
				previousStepsArray = allSteps.steps_data.steps;
			} else if (allSteps?.steps && Array.isArray(allSteps.steps)) {
				previousStepsArray = allSteps.steps;
			}
			
			if (previousStepsArray.length === 0) {
				console.warn('No steps data available:', allSteps);
				// Just complete the current step if allSteps is invalid
				await toggleStepCompletion(projectId, stepNumber);
				if (onStepUpdate) onStepUpdate();
				return;
			}

			// Mark all previous incomplete steps as completed
			// currentStepIndex is 1-based, so check from 0 to currentStepIndex-2
			for (let i = 0; i < currentStepIndex - 1; i++) {
				if (!previousStepsArray[i]?.completed) {
					await toggleStepCompletion(projectId, i + 1); // Step numbers are 1-based
				}
			}
			
			// Mark current step as completed
			await toggleStepCompletion(projectId, stepNumber);
			
			// Close modal and update UI
			setShowValidationModal(false);
			if (onStepUpdate) onStepUpdate();
			
			// Show congratulatory message
			// Handle different data structures from the API
			let previousStepsArray2 = [];
			if (Array.isArray(allSteps)) {
				previousStepsArray2 = allSteps;
			} else if (allSteps?.steps_data?.steps && Array.isArray(allSteps.steps_data.steps)) {
				previousStepsArray2 = allSteps.steps_data.steps;
			} else if (allSteps?.steps && Array.isArray(allSteps.steps)) {
				previousStepsArray2 = allSteps.steps;
			}
			
			console.log('🎯 completeStepWithPrevious debug:', {
				previousStepsArray2,
				currentStepIndex,
				stepNumber
			});

			// Show congratulatory message
			const actualStepIndex = currentStepIndex - 1; // Convert 1-based to 0-based
			const stepTitle = previousStepsArray2[actualStepIndex]?.title || `Step ${stepNumber}`;
			showCongratulatoryMessage(stepTitle);
			
		} catch (error) {
			console.error('Error completing steps:', error);
			alert('Failed to complete steps. Please try again.');
		}
	};

	const handleModalConfirm = () => {
		if (pendingAction) {
			pendingAction();
		}
	};

	const handleModalClose = () => {
		setShowValidationModal(false);
		setPendingAction(null);
	};

	// Get modal content based on validation type
	const getModalContent = () => {
		if (validationType === 'previous') {
			return {
				title: "Previous Steps Not Completed",
				message: `Step ${stepNumber - 1} is not completed. Mark both steps complete?`,
				confirmText: "Yes, Mark Both Complete",
				cancelText: "No, Go Back"
			};
		} else if (validationType === 'final') {
			// Check if all steps are already completed
			const allCompleted = checkAllStepsCompleted();
			if (allCompleted) {
				return {
					title: "Project Completion",
					message: "All steps are completed! Ready to finish this project? This will mark the entire project as complete.",
					confirmText: "Yes, Complete Project",
					cancelText: "No, Go Back"
				};
			} else {
				return {
					title: "Final Step - Complete All Steps",
					message: "This is the final step! Some previous steps are not completed. Would you like to mark all remaining steps as complete and finish the project? This will mark the entire project as complete.",
					confirmText: "Yes, Complete All Steps & Finish",
					cancelText: "No, Go Back"
				};
			}
		}
		return {};
	};

	return (
		<>
			<div className="bg-white rounded-lg shadow-sm border border-gray-200 p-2">
				<div className="flex items-center justify-between">
					<span className="text-xs font-medium text-gray-900">
						{stepCompleted 
							? "Step completed! Want to undo?" 
							: "Have you completed this step?"
						}
					</span>
					<button
						onClick={handleStepComplete}
						className={`py-2 px-4 rounded-lg text-sm font-medium transition-colors ${
							stepCompleted
								? "bg-yellow-200 text-yellow-800 hover:bg-yellow-300"
								: "bg-gray-200 text-gray-900 hover:bg-gray-300"
						}`}
					>
						{stepCompleted ? "Undo" : "Yes"}
					</button>
				</div>
			</div>

			{/* Validation Modal */}
			<StepValidationModal
				isOpen={showValidationModal}
				onClose={handleModalClose}
				onConfirm={handleModalConfirm}
				{...getModalContent()}
			/>

			{/* Congratulatory Card */}
			{showCongratulatoryCard && completedStepData && (
				<div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
					<div className="bg-white rounded-2xl p-6 max-w-xs w-full mx-4 text-center shadow-2xl">
						{/* Celebration Icon */}
						<div className="w-12 h-12 flex items-center justify-center mx-auto mb-4">
							<span className="text-4xl">🎉</span>
						</div>
						
						{/* Congratulations Message */}
						<h3 className="text-lg font-bold text-gray-900 mb-3">
							{completedStepData.isFinalStep ? 'Congratulations!' : 'Well Done!'}
						</h3>
						
						{/* Step Completion Info */}
						<p className="text-sm text-gray-700 mb-4 leading-relaxed">
							{completedStepData.isFinalStep ? (
								<>You are done with your DIY project! All steps have been completed successfully.</>
							) : (
								<>
									Step {completedStepData.stepNumber}/{completedStepData.total} {completedStepData.stepTitle} is complete!
									{completedStepData.nextStepTitle && (
										<> You can continue with Step {completedStepData.stepNumber + 1}/{completedStepData.total} {completedStepData.nextStepTitle}.</>
									)}
								</>
							)}
						</p>
					</div>
				</div>
			)}
		</>
	);
}
