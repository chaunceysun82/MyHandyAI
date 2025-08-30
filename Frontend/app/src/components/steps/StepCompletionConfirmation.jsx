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

	// Check if previous steps are completed (excluding tools step)
	const checkPreviousStepsCompleted = () => {
		// Ensure allSteps is an array before checking
		if (!Array.isArray(allSteps) || allSteps.length === 0) {
			console.warn('allSteps is not an array or is empty:', allSteps);
			return true; // Default to true to avoid blocking completion
		}
		
		if (currentStepIndex <= 1) return true; // First instruction step (step 1), no previous instruction steps to check
		
		// Check only instruction steps (skip tools step at index 0)
		for (let i = 1; i < currentStepIndex; i++) {
			if (!allSteps[i]?.completed) {
				return false;
			}
		}
		return true;
	};

	// Check if this is the final step (excluding tools step)
	const isFinalStep = () => {
		// Ensure allSteps is an array before filtering
		if (!Array.isArray(allSteps) || allSteps.length === 0) {
			console.warn('allSteps is not an array or is empty:', allSteps);
			return false;
		}
		
		// Filter out tools step and check if current step is the last instruction step
		const instructionSteps = allSteps.filter((step, index) => index > 0); // Skip tools step (index 0)
		return currentStepIndex === instructionSteps.length;
	};

	// Check if all instruction steps are completed
	const checkAllStepsCompleted = () => {
		// Ensure allSteps is an array before iterating
		if (!Array.isArray(allSteps) || allSteps.length === 0) {
			console.warn('allSteps is not an array or is empty:', allSteps);
			return false;
		}
		
		// Check all instruction steps (skip tools step at index 0)
		for (let i = 1; i < allSteps.length; i++) {
			if (!allSteps[i]?.completed) {
				return false;
			}
		}
		return true;
	};

	// Calculate remaining steps for congratulatory message
	const getRemainingStepsInfo = () => {
		if (!Array.isArray(allSteps) || allSteps.length === 0) {
			return { remaining: 0, total: 0 };
		}
		
		// Count remaining instruction steps (skip tools step at index 0)
		let remaining = 0;
		let total = 0;
		
		for (let i = 1; i < allSteps.length; i++) {
			total++;
			if (!allSteps[i]?.completed) {
				remaining++;
			}
		}
		
		return { remaining, total };
	};

	// Show congratulatory card when step is completed
	const showCongratulatoryMessage = (stepTitle) => {
		const { remaining, total } = getRemainingStepsInfo();
		const isFinalStepCompleted = remaining === 0;
		const currentStepNumber = total - remaining;
		
		// Get next step title
		let nextStepTitle = null;
		if (!isFinalStepCompleted && Array.isArray(allSteps)) {
			const nextStepIndex = currentStepIndex + 1;
			if (nextStepIndex < allSteps.length) {
				nextStepTitle = allSteps[nextStepIndex]?.title || `Step ${nextStepIndex + 1}`;
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
		
		// Auto-hide after 6 seconds
		setTimeout(() => {
			setShowCongratulatoryCard(false);
		}, 6000);
	};

	// Complete all remaining steps and finish project
	const completeAllStepsAndFinish = async () => {
		try {
			// Ensure allSteps is an array before iterating
			if (!Array.isArray(allSteps) || allSteps.length === 0) {
				console.warn('allSteps is not an array or is empty:', allSteps);
				// Just complete the current step if allSteps is invalid
				await toggleStepCompletion(projectId, stepNumber);
				if (onStepUpdate) onStepUpdate();
				if (onProjectComplete) onProjectComplete();
				return;
			}
			
			// Mark all incomplete instruction steps as completed (skip tools step at index 0)
			for (let i = 1; i < allSteps.length; i++) {
				if (!allSteps[i]?.completed) {
					await toggleStepCompletion(projectId, i + 1);
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
			const stepTitle = allSteps[currentStepIndex]?.title || `Step ${stepNumber}`;
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
					return;
				}

				// Check if this is the final step
				if (isFinalStep()) {
					// Show final step warning
					setValidationType('final');
					setPendingAction(() => () => completeAllStepsAndFinish());
					setShowValidationModal(true);
					return;
				}

				// Normal step completion
				await toggleStepCompletion(projectId, stepNumber);
				if (onStepUpdate) onStepUpdate();
				
				// Show congratulatory message
				const stepTitle = allSteps[currentStepIndex]?.title || `Step ${stepNumber}`;
				showCongratulatoryMessage(stepTitle);
			}
		} catch (error) {
			console.error('Error toggling step completion:', error);
			alert('Failed to update step completion. Please try again.');
		}
	};

	// Complete current step and mark previous incomplete steps as completed (excluding tools step)
	const completeStepWithPrevious = async () => {
		try {
			// Ensure allSteps is an array before iterating
			if (!Array.isArray(allSteps) || allSteps.length === 0) {
				console.warn('allSteps is not an array or is empty:', allSteps);
				// Just complete the current step if allSteps is invalid
				await toggleStepCompletion(projectId, stepNumber);
				if (onStepUpdate) onStepUpdate();
				return;
			}

			// Mark all previous incomplete instruction steps as completed (skip tools step at index 0)
			for (let i = 1; i < currentStepIndex; i++) {
				if (!allSteps[i]?.completed) {
					await toggleStepCompletion(projectId, i + 1);
				}
			}
			
			// Mark current step as completed
			await toggleStepCompletion(projectId, stepNumber);
			
			// Close modal and update UI
			setShowValidationModal(false);
			if (onStepUpdate) onStepUpdate();
			
			// Show congratulatory message
			const stepTitle = allSteps[currentStepIndex]?.title || `Step ${stepNumber}`;
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
									Step {completedStepData.stepNumber}/{completedStepData.total} ({completedStepData.stepTitle}) is complete!
									{completedStepData.nextStepTitle && (
										<> You can continue with {completedStepData.nextStepTitle}.</>
									)}
								</>
							)}
						</p>
						
						{/* Close Button */}
						<button
							onClick={() => {
								setShowCongratulatoryCard(false);
								// If this is the final step, navigate to project completion
								if (completedStepData.isFinalStep && onProjectComplete) {
									onProjectComplete();
								}
							}}
							className={`w-full py-2 px-4 font-medium rounded-lg transition-colors ${
								completedStepData.isFinalStep 
									? 'bg-green-500 text-white hover:bg-green-600'
									: 'bg-blue-500 text-white hover:bg-blue-600'
							}`}
						>
							{completedStepData.isFinalStep ? 'Finish Project' : 'Continue'}
						</button>
					</div>
				</div>
			)}
		</>
	);
}
