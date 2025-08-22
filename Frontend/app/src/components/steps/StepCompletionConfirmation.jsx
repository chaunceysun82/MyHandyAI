import React, { useState } from "react";
import { toggleStepCompletion } from "../../services/steps";
import StepValidationModal from "./StepValidationModal";

export default function StepCompletionConfirmation({ 
	projectId, 
	stepNumber, 
	stepCompleted, 
	allSteps, 
	currentStepIndex,
	onStepUpdate 
}) {
	const [showValidationModal, setShowValidationModal] = useState(false);
	const [validationType, setValidationType] = useState(null); // 'previous' or 'final'
	const [pendingAction, setPendingAction] = useState(null);

	// Check if previous steps are completed
	const checkPreviousStepsCompleted = () => {
		if (currentStepIndex === 0) return true; // First step, no previous steps to check
		
		for (let i = 0; i < currentStepIndex; i++) {
			if (!allSteps[i]?.completed) {
				return false;
			}
		}
		return true;
	};

	// Check if this is the final step (excluding tools step)
	const isFinalStep = () => {
		// Filter out tools step and check if current step is the last instruction step
		const instructionSteps = allSteps.filter(step => step.type !== 'tools');
		return currentStepIndex === instructionSteps.length - 1;
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
					setPendingAction(() => () => completeStepWithPrevious());
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

	// Complete current step and mark previous incomplete steps as completed
	const completeStepWithPrevious = async () => {
		try {
			// Mark all previous incomplete steps as completed
			for (let i = 0; i < currentStepIndex; i++) {
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
			return {
				title: "Final Step Warning",
				message: "This is the final step! Complete all steps and finish project?",
				confirmText: "Yes, Complete Project",
				cancelText: "No, Go Back"
			};
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
