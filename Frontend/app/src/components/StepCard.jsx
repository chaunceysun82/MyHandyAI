// StepCard.jsx
import { truncateWords, truncateUntilChar } from "../utilities/text.js";

export default function StepCard({
	index,
	icon,
	title,
	subtitle,
	time,
	onClick,
	imageUrl,
	completed, 
	status,
}) {
	const short = truncateWords(subtitle, 7);
	const isToolsStep = title === "Tools and Materials";

	// Debug logging
	console.log("StepCard:", { title, completed, isToolsStep });

	// Status color + icon mapping for completed state
	const completedStatus = {
		classes: "bg-green-200 text-green-800",
		icon: "✅", // check mark
	};

	return (
		<button
			onClick={onClick}
			className="w-full text-left px-3 py-3 rounded-2xl bg-[#E5E5E5] hover:bg-gray-300 transition-colors p-3 flex items-center gap-3 border-l-4"
			style={{ borderLeftColor: '#10B981' }}>
			{/* Step Image */}
			<div className="w-14 h-14 rounded-lg overflow-hidden flex items-center justify-center bg-[#F6F0E0]">
				{imageUrl ? (
					<img src={imageUrl} alt="" className="w-full h-full object-cover" />
				) : (
					<span className="text-2xl">{icon || "🧰"}</span>
				)}
			</div>

			{/* Step Text */}
			<div className="flex-1">
							{/* Title with Step Number */}
			<div className="text-sm font-semibold leading-tight text-gray-900 mb-1">
				<span className="pb-0.5 line-clamp-2">
					{!isToolsStep ? (
						<>
							<span className="text-gray-500 flex-shrink-0">Step {index}: </span>
							{title}
						</>
					) : (
						title
					)}
				</span>
			</div>
				
				{/* Description */}
				<div className="text-xs text-gray-600 mb-2">{short}...</div>

				{/* Status Row - Time, Completed, or Tools badge */}
				<div className="flex gap-2 flex-wrap">
					{/* Show time only when NOT completed and NOT tools step */}
					{!isToolsStep && !completed && time && (
						<div className="inline-flex items-center text-[10px] text-gray-600 bg-[#F6F0E0] px-2 py-0.5 rounded-md">
							⏱ {truncateUntilChar(time, " ")} min
						</div>
					)}

					{/* Show completed status only when completed is true and NOT tools step */}
					{!isToolsStep && completed && (
						<div
							className={`inline-flex items-center text-[10px] px-2 py-0.5 rounded-md ${completedStatus.classes}`}>
							<span className="mr-1">{completedStatus.icon}</span> Complete
						</div>
					)}

					{/* Show tools badge for tools step */}
					{isToolsStep && (
						<div className="inline-flex items-center text-[10px] px-2 py-0.5 rounded-md bg-blue-100 text-blue-800">
							<span className="mr-1">📋</span> View Tools
						</div>
					)}
				</div>
			</div>

			{/* Navigation Arrow - Right side */}
			<div className="shrink-0">
				<span className="inline-flex items-center text-xs px-2 py-1 rounded-full bg-white border border-gray-300">
					{isToolsStep ? "Tools" : `Step ${index}`} <span className="ml-1">›</span>
				</span>
			</div>
		</button>
	);
}
