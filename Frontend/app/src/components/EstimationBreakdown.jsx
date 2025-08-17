// EstimatedBreakdown.jsx
import React from "react";

export default function EstimatedBreakdown({ stats }) {
	const rows = [
		{ label: "Estimated time duration", value: stats.duration },
		{ label: "Estimated Cost: Tools + materials", value: stats.cost },
		{ label: "Skill level", value: stats.skill },
	];

	return (
		<section>
			<div className="flex items-center text-[13px] font-semibold">
				Estimated Breakdown
				<span className="ml-1 text-gray-400 text-xs">ⓘ</span>
			</div>

			<div className="mt-2 rounded-2xl border border-gray-200 bg-gray-100">
				{rows.map((item, index) => (
					<div
						key={index}
						className={`flex justify-between items-center px-4 py-2 text-sm ${
							index !== rows.length - 1 ? "border-b border-gray-300" : ""
						}`}>
						<span className="text-gray-700">{item.label}</span>
						<span className="font-medium">{item.value}</span>
					</div>
				))}
			</div>
		</section>
	);
}
