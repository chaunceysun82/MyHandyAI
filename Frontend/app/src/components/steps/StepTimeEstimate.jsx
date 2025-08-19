import React from "react";
import { ClockIcon, CheckCircleIcon } from "@heroicons/react/24/outline";

export default function StepTimeEstimate({ time, completed }) {
	return (
		<div className="flex items-center gap-3">
			{/* Time Estimate - Always visible */}
			<div className="flex items-center gap-3 bg-gray-100 border border-gray-200 rounded-full py-1 px-2 w-fit">
				<ClockIcon className="h-4 w-4 text-gray-600" />
				<span className="text-[10px] font-medium text-gray-700">
					Estimated time: {time}
				</span>
			</div>

			{/* Completion Status - Only visible when completed is true */}
			{completed && (
				<div className="flex items-center gap-3 bg-green-100 border border-green-200 rounded-full py-1 px-2 w-fit">
					<CheckCircleIcon className="h-4 w-4 text-green-600" />
					<span className="text-[10px] font-medium text-green-700">
						Completed
					</span>
				</div>
			)}
		</div>
	);
}
