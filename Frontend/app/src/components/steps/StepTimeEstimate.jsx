import React, { useState } from "react";
import { ClockIcon, CheckCircleIcon } from "@heroicons/react/24/outline";
import { submitStepFeedback } from "../../services/steps";

export default function StepTimeEstimate({ time, completed, projectId, stepNumber }) {
	const [feedback, setFeedback] = useState(null);
	const [submitting, setSubmitting] = useState(false);

	const handleFeedback = async (feedbackValue) => {
		if (submitting) return;
		
		setSubmitting(true);
		try {
			await submitStepFeedback(projectId, stepNumber, feedbackValue);
			setFeedback(feedbackValue);
		} catch (error) {
			console.error("Error submitting feedback:", error);
		} finally {
			setSubmitting(false);
		}
	};

	const handleFeedbackChange = (feedbackValue) => {
		// Allow users to change their feedback
		if (feedback === feedbackValue) {
			setFeedback(null); // Undo feedback
		} else {
			handleFeedback(feedbackValue);
		}
	};

	return (
		<div className="flex items-center justify-between">
			{/* Left side - Time estimate or completed status */}
			<div className="flex items-center gap-3">
				{/* Show completed badge when step is completed, otherwise show time estimate */}
				{completed ? (
					<div className="flex items-center gap-3 bg-green-100 rounded-lg py-1 px-3 w-fit">
						<CheckCircleIcon className="h-4 w-4 text-green-600" />
						<span className="text-[10px] font-medium text-green-700">
							Completed
						</span>
					</div>
				) : (
					<div className="flex items-center gap-3 bg-[#FFEFC5] rounded-lg py-1 px-3 w-fit">
						<ClockIcon className="h-4 w-4 text-gray-600" />
						<span className="text-[10px] font-medium text-gray-700">
							Estimated time: {time}
						</span>
					</div>
				)}
			</div>

			{/* Right side - Feedback buttons */}
			<div className="flex items-center gap-2">
				<span className="text-[10px] text-gray-500 font-medium">Feedback:</span>
				<div className="flex gap-1">
					<button
						onClick={() => handleFeedbackChange(1)}
						className={`w-7 h-7 rounded-full flex items-center justify-center transition-all duration-200 hover:scale-110 ${
							feedback === 1
								? "bg-[#1484A3] text-white border-2 border-[#1484A3] shadow-md"
								: "bg-[#E9FAFF] text-gray-400 hover:bg-[#1484A3] hover:text-white border border-gray-200 hover:border-[#1484A3]"
						} ${submitting ? "opacity-50" : ""}`}
						title="This step was helpful"
					>
						<svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
							<path d="M2 10.5a1.5 1.5 0 113 0v6a1.5 1.5 0 01-3 0v-6zM6 10.333v5.818a2 2 0 001.106 1.79l.05.025A4 4 0 008.943 18h5.416a2 2 0 001.962-1.608l1.2-6A2 2 0 0015.56 8H12V4a2 2 0 00-2-2 1 1 0 00-1 1v.667a4 4 0 01-.8 2.4L6.8 7.933a4 4 0 00-.8 2.4z" />
						</svg>
					</button>
					
					<button
						onClick={() => handleFeedbackChange(0)}
						className={`w-7 h-7 rounded-full flex items-center justify-center transition-all duration-200 hover:scale-110 ${
							feedback === 0
								? "bg-red-500 text-white border-2 border-red-500 shadow-md"
								: "bg-[#E9FAFF] text-gray-400 hover:bg-red-500 hover:text-white border border-gray-200 hover:border-red-500"
						} ${submitting ? "opacity-50" : ""}`}
						title="This step needs improvement"
					>
						<svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
							<path d="M18 9.5a1.5 1.5 0 11-3 0v-6a1.5 1.5 0 013 0v6zM14 9.667v-5.818a2 2 0 00-1.106-1.79l-.05-.025A4 4 0 0011.057 2H5.64a2 2 0 00-1.962 1.608l-1.2 6A2 2 0 004.44 12H8v4a2 2 0 002 2 1 1 0 001-1v-.667a4 4 0 01.8-2.4l1.4-1.866a4 4 0 00.8-2.4z" />
						</svg>
					</button>
				</div>
			</div>
		</div>
	);
}
