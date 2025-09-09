import React from "react";
import { WrenchScrewdriverIcon } from "@heroicons/react/24/outline";

export default function StepToolsNeeded({ toolsNeeded }) {
	if (!toolsNeeded || toolsNeeded.length === 0) {
		return (
			<div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
				<h3 className="text-sm font-semibold text-gray-900 mb-3">Tools Needed:</h3>
				<p className="text-sm text-gray-700 leading-relaxed">
					No specific tools required for this step. Use common household items as needed.
				</p>
			</div>
		);
	}

	return (
		<div className="bg-white rounded-lg shadow-sm border-l-2 border-[#1484A3] p-4">
			<h3 className="text-sm font-semibold text-gray-900 mb-3">Tools Needed:</h3>
			{Array.isArray(toolsNeeded) ? (
				<ul className="space-y-2">
					{toolsNeeded.map((tool, index) => (
						<li key={index} className="flex items-start gap-3 min-h-[24px]">
							<div className="flex-shrink-0 w-6 h-6 bg-[#E9FAFF] rounded-full flex items-center justify-center">
								<WrenchScrewdriverIcon className="h-4 w-4 text-gray-600" />
							</div>
							<span className="text-sm text-gray-700 leading-relaxed flex-1">
								{tool}
							</span>
						</li>
					))}
				</ul>
			) : (
				<p className="text-sm text-gray-700 leading-relaxed">{toolsNeeded}</p>
			)}
		</div>
	);
}
