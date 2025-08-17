import React from "react";
import { useNavigate } from "react-router-dom";

export default function StepFooter({ 
	projectId, 
	projectName, 
	stepNumber, 
	stepTitle, 
	totalSteps,
	onPrev, 
	onNext,
	isPrevDisabled = false,
	isNextDisabled = false,
	isNextFinal = false
}) {
	const navigate = useNavigate();

	const handleChatClick = () => {
		navigate("/chat", { 
			state: { 
				projectId, 
				projectName: projectName || "Project",
				from: "step",
				stepNumber: stepNumber,
				stepTitle: stepTitle
			}
		});
	};

	return (
		<div className="px-4 pb-4 space-y-3">
			{/* Assistant prompt pill */}
			<div className="rounded-xl border border-gray-200 bg-gray-50 px-3 py-2 text-[12px] text-gray-600 flex items-center justify-between">
				<span>Hi "User", Need MyHandyAI Assistant?</span>
				<button
					onClick={handleChatClick}
					className="ml-3 px-3 py-1 rounded-lg bg-[#6FCBAE] text-white text-[12px] font-semibold">
					Ask
				</button>
			</div>

			{/* Bottom Navigation */}
			<div className="grid grid-cols-2 gap-3">
				<button
					onClick={onPrev}
					disabled={isPrevDisabled}
					className={`py-2 rounded-lg font-medium ${
						isPrevDisabled
							? "bg-gray-100 text-gray-400 cursor-not-allowed"
							: "border border-gray-300 bg-gray-50 text-sm"
					}`}>
					Previous
				</button>
				<button
					onClick={onNext}
					disabled={isNextDisabled}
					className={`py-2 rounded-lg font-medium ${
						isNextDisabled
							? "bg-gray-100 text-gray-400 cursor-not-allowed"
							: isNextFinal
							? "bg-green-600 text-white hover:bg-green-700"
							: "bg-black text-white text-sm font-semibold"
					}`}>
					{isNextFinal ? "Finish" : "Next Step"}
				</button>
			</div>
		</div>
	);
}
