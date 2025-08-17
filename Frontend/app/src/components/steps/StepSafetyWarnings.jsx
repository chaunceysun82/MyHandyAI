import React from "react";
import { ExclamationTriangleIcon } from "@heroicons/react/24/outline";

export default function StepSafetyWarnings({ safety }) {
	if (!safety || safety.length === 0) {
		return (
			<div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
				<div className="flex items-start gap-3">
					<div className="w-6 h-6 bg-yellow-100 rounded-full flex items-center justify-center flex-shrink-0">
						<ExclamationTriangleIcon className="h-4 w-4 text-yellow-600" />
					</div>
					<div className="flex-1">
						<h3 className="text-xs font-semibold text-yellow-800 mb-1">Safety:</h3>
						<p className="text-xs text-yellow-700 leading-relaxed">
							Always wear appropriate safety equipment, work in a well-ventilated area, and keep your workspace clean and organized. If you're unsure about any step, consult a professional.
						</p>
					</div>
				</div>
			</div>
		);
	}

	return (
		<div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
			<div className="flex items-start gap-3">
				<div className="w-6 h-6 bg-yellow-100 rounded-full flex items-center justify-center flex-shrink-0">
					<ExclamationTriangleIcon className="h-4 w-4 text-yellow-600" />
				</div>
				<div className="flex-1">
					<h3 className="text-xs font-semibold text-yellow-800 mb-1">Safety:</h3>
					{Array.isArray(safety) ? (
						<ul className="space-y-1">
							{safety.map((warning, index) => (
								<li key={index} className="flex items-start gap-2">
									<span className="text-yellow-600 text-xs mt-0.5">•</span>
									<span className="text-xs text-yellow-700 leading-relaxed">{warning}</span>
								</li>
							))}
						</ul>
					) : (
						<p className="text-xs text-yellow-700 leading-relaxed">{safety}</p>
					)}
				</div>
			</div>
		</div>
	);
}
