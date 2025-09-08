// EstimatedBreakdown.jsx
import React from "react";
import {ReactComponent as Information} from '../assets/information.svg';

export default function EstimatedBreakdown({ stats }) {
	const rows = [
		{ label: "Estimated time duration", value: stats.duration },
		{ label: "Estimated Cost: Tools + materials", value: stats.cost },
		{ label: "Skill level", value: stats.skill },
	];

	return (
		<section>
			<div className="flex items-center text-[16px] font-medium text-[black]">
				Estimated Breakdown

				<span className="ml-3 text-gray-400 text-xs">
					<Information width = {14} height = {14} />
				</span>
			</div>

			<div className="mt-2 rounded-2xl border border-gray-200 bg-[#E9FAFF]">
				{rows.map((item, index) => (
					<div
						key={index}
						className={`flex justify-between items-center px-4 py-2 text-sm ${
							index !== rows.length - 1 ? "border-b border-gray-300" : ""
						}`}>
						<span className="text-[#000000] text-[12px]">{item.label}</span>
						<span className="font-medium text-[#000000] text-[12px]">{item.value}</span>
					</div>
				))}
			</div>
		</section>
	);
}
