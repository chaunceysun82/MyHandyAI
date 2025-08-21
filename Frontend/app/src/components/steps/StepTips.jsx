import React from "react";
import { LightBulbIcon } from "@heroicons/react/24/outline";

export default function StepTips({ tips }) {
	if (!tips || tips.length === 0) {
		return (
			<div className="bg-green-50 border border-green-200 rounded-lg p-3">
				<div className="flex items-start gap-3">
					<div className="w-6 h-6 bg-green-100 rounded-full flex items-center justify-center flex-shrink-0">
						<LightBulbIcon className="h-4 w-4 text-green-600" />
					</div>
					<div className="flex-1">
						<h3 className="text-xs font-semibold text-green-800 mb-1">Tips:</h3>
						<p className="text-xs text-green-700 leading-relaxed">
							Take your time and don't rush. Quality work takes patience. If something doesn't feel right, stop and reassess. It's better to do it right than to do it fast.
						</p>
					</div>
				</div>
			</div>
		);
	}

	return (
		<div className="bg-green-50 border border-green-200 rounded-lg p-3">
			<div className="flex items-start gap-3">
				<div className="w-6 h-6 bg-green-100 rounded-full flex items-center justify-center flex-shrink-0">
					<LightBulbIcon className="h-4 w-4 text-green-600" />
				</div>
				<div className="flex-1">
					<h3 className="text-xs font-semibold text-green-800 mb-1">Tips:</h3>
					{Array.isArray(tips) ? (
						<ul className="space-y-1">
							{tips.map((tip, index) => (
								<li key={index} className="flex items-start gap-2">
									<span className="text-green-600 text-xs mt-0.5">•</span>
									<span className="text-xs text-green-700 leading-relaxed">{tip}</span>
								</li>
							))}
						</ul>
					) : (
						<p className="text-xs text-green-700 leading-relaxed">{tips}</p>
					)}
				</div>
			</div>
		</div>
	);
}
