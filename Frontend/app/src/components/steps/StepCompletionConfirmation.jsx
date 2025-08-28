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
			
			// Navigate to project completion page
			if (onProjectComplete) {
				onProjectComplete();
			}
			
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
		</>
	);
}
