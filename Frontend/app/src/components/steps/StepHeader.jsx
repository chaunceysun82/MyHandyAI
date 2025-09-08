// components/StepHeader.jsx
import React from "react";

export default function StepHeader({
	stepNumber,
	totalSteps,
	title, // e.g., "Prepare Tools and Materials"
	subtitle, // e.g., "Don't have these? Tap any item to order it easily."
	onBack,
	className = "", // lets you pass extra classes if needed
}) {
	// Check if this is the tools step (stepNumber === 0)
	const isToolsStep = stepNumber === 0;

	return (
		// bg-transparent so it matches the page; no border
		<header className={`relative bg-transparent ${className}`}>
			<div className="h-16 flex items-center px-4">
				{/* Left: Back button */}
				<button
					onClick={onBack}
					aria-label="Go back"
					className="relative z-10 inline-flex h-9 w-9 items-center justify-center rounded-full hover:bg-black/5 active:bg-black/10">
					<svg
						viewBox="0 0 24 24"
						className="h-6 w-6 text-gray-900"
						fill="none"
						stroke="currentColor"
						strokeWidth="2"
						aria-hidden="true">
						<path
							d="M15 18l-6-6 6-6"
							strokeLinecap="round"
							strokeLinejoin="round"
						/>
					</svg>
				</button>

				{/* Center: Step number or Tools text */}
				<div className="flex-1 flex justify-center">
					<span className="text-lg font-semibold text-gray-900">
						{isToolsStep ? "Tools and Materials" : `Step ${stepNumber}/${totalSteps}`}
					</span>
				</div>

				{/* Right: Spacer for symmetry */}
				<div className="w-9 h-9" />
			</div>

			{/* Title in separate row below */}
			{(title || subtitle) && (
				<div className="px-4 pb-2">
					<div className="text-center">
						<p className="text-[16px] leading-5 font-medium text-gray-700 mb-[-4px]">{title}</p>
						{/* Subtitle */}
						{subtitle && (
							<p className="text-sm text-gray-500 leading-4">{subtitle}</p>
						)}
					</div>
				</div>
			)}
		</header>
	);
}
