import React from "react";
import { toggleStepCompletion } from "../../services/steps";

export default function StepCompletionConfirmation({ projectId, stepNumber, stepCompleted }) {
	const handleStepComplete = async () => {
		try {
			if (stepCompleted) {
				console.log(`Project ID: ${projectId}, Step ${stepNumber} - Undoing completion`);
			} else {
				console.log(`Project ID: ${projectId}, Step ${stepNumber} is complete`);
			}
			
			// Call the API service to toggle completion
			await toggleStepCompletion(projectId, stepNumber);
			
			// Refresh the page to show updated status
			window.location.reload();
			
		} catch (error) {
			console.error('Error toggling step completion:', error);
			alert('Failed to update step completion. Please try again.');
		}
	};

	return (
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
	);
}
