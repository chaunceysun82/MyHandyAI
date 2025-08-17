import React from "react";

export default function StepInstructions({ instructions }) {
	if (!instructions || instructions.length === 0) {
		return (
			<div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
				<h3 className="text-sm font-semibold text-gray-900 mb-3">Instructions:</h3>
				<p className="text-sm text-gray-700 leading-relaxed">
					Follow the step-by-step process carefully. Take your time and ensure each step is completed before moving to the next.
				</p>
			</div>
		);
	}

	return (
		<div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
			<h3 className="text-sm font-semibold text-gray-900 mb-3">Instructions:</h3>
			{Array.isArray(instructions) ? (
				<ol className="space-y-2">
					{instructions.map((instruction, index) => (
						<li key={index} className="flex items-start gap-3">
							<span className="w-6 h-6 bg-gray-200 text-gray-700 rounded-full flex items-center justify-center text-sm font-semibold flex-shrink-0">
								{index + 1}
							</span>
							<span className="text-sm text-gray-700 leading-relaxed flex-1">
								{instruction}
							</span>
						</li>
					))}
				</ol>
			) : (
				<p className="text-sm text-gray-700 leading-relaxed">{instructions}</p>
			)}
		</div>
	);
}
