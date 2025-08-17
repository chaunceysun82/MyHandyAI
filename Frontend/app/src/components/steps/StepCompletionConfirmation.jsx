import React from "react";

export default function StepCompletionConfirmation({ projectId, stepNumber }) {
	const handleStepComplete = () => {
		console.log(`Project ID: ${projectId}, Step ${stepNumber} is complete`);
	};

	return (
		<div className="bg-white rounded-lg shadow-sm border border-gray-200 p-2">
			<div className="flex items-center justify-between">
				<span className="text-xs font-medium text-gray-900">
					Have you completed this step?
				</span>
				<button
					onClick={handleStepComplete}
					className="py-2 px-4 bg-gray-200 text-gray-900 rounded-lg text-sm font-medium hover:bg-gray-300 transition-colors"
				>
					Yes
				</button>
			</div>
		</div>
	);
}
