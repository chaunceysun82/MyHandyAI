import React from "react";
import { PlayIcon } from "@heroicons/react/24/outline";

export default function StepVideoGuide() {
	return (
		<div className="border-2 border-dashed border-gray-300 rounded-lg text-center p-4 mx-auto">
			<div className="w-8 h-8 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-2">
				<PlayIcon className="w-5 h-5 text-gray-500" />
			</div>
			<p className="text-xs text-gray-600 mb-1">Video Guide</p>
			<p className="text-[10px] text-gray-500">Coming Soon</p>
		</div>
	);
}
