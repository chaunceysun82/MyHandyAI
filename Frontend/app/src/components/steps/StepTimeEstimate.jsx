import React from "react";
import { ClockIcon } from "@heroicons/react/24/outline";

export default function StepTimeEstimate({ time }) {
	return (
		<div className="flex items-center gap-3 bg-gray-100 border border-gray-200 rounded-full py-1 px-2 w-fit">
			<ClockIcon className="h-4 w-4 text-gray-600" />
			<span className="text-[10px] font-medium text-gray-700">
				Estimated time: {time}
			</span>
		</div>
	);
}
