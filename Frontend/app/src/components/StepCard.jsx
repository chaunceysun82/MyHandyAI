// StepCard.jsx
import { truncateWords, truncateUntilWord } from "../utilities/text.js";

export default function StepCard({
	index,
	icon,
	title,
	subtitle,
	time,
	onClick,
	imageUrl,
	status, // new prop for project status
}) {
	const short = truncateWords(subtitle, 7);
	const isToolsStep = title === "Tools Required";

	// Status color + icon mapping
	const statusStyles = {
		"Not Started": {
			classes: "bg-gray-300 text-gray-700",
			icon: "⏳", // hourglass not started
		},
		pending: {
			classes: "bg-yellow-200 text-yellow-800",
			icon: "🔄", // progress arrows
		},
		Complete: {
			classes: "bg-green-200 text-green-800",
			icon: "✅", // check mark
		},
	};

	const { classes, icon: statusIcon } =
		statusStyles[status] || statusStyles["Not Started"];

	return (
		<button
			onClick={onClick}
			className="w-full text-left px-3 py-3 rounded-2xl bg-[#E5E5E5] hover:bg-gray-300 transition-colors p-3 flex items-center gap-3">
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
				{/* Time + Status Row */}
				<div className="flex gap-2 mb-1 flex-wrap">
					{time && (
						<div className="inline-flex items-center text-[10px] text-gray-600 bg-[#F6F0E0] px-2 py-0.5 rounded-md">
							⏱ {truncateUntilWord(time, "minutes")}
						</div>
					)}

					{!isToolsStep && status && (
						<div
							className={`inline-flex items-center text-[10px] px-2 py-0.5 rounded-md ${classes}`}>
							<span className="mr-1">{statusIcon}</span> {status}
						</div>
					)}

					{isToolsStep && (
						<div className="inline-flex items-center text-[10px] px-2 py-0.5 rounded-md bg-blue-100 text-blue-800">
							<span className="mr-1">📋</span> View Tools
						</div>
					)}
				</div>

				<div className="text-sm font-semibold leading-tight">{title}</div>
				<div className="text-xs text-gray-600">{short}...</div>
			</div>

			{/* Step Number - Hide for tools step */}
			{!isToolsStep && (
				<div className="shrink-0">
					<span className="inline-flex items-center text-xs px-2 py-1 rounded-full bg-white border border-gray-300">
						Step {index} <span className="ml-1">›</span>
					</span>
				</div>
			)}

			{/* Tools step shows different indicator */}
			{isToolsStep && (
				<div className="shrink-0">
					<span className="inline-flex items-center text-xs px-2 py-1 rounded-full bg-white border border-gray-300">
						Step 1 <span className="ml-1">›</span>
					</span>
				</div>
			)}
		</button>
	);
}
