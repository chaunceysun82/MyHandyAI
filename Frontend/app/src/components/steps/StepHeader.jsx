// components/StepHeader.jsx
import React from "react";

export default function StepHeader({
	stepNumber,
	totalSteps,
	title, // e.g., "Prepare Tools and Materials"
	onBack,
	className = "", // lets you pass extra classes if needed
}) {
	return (
		// bg-transparent so it matches the page; no border
		<header className={`relative bg-transparent ${className}`}>
			<div className="h-16 flex items-center px-4">
				{/* Back button */}
				<button
					onClick={onBack}
					aria-label="Go back"
					className="relative z-10 -ml-1 inline-flex h-9 w-9 items-center justify-center rounded-full hover:bg-black/5 active:bg-black/10">
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

				{/* Centered title stack */}
				<div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
					<h2 className="text-[22px] leading-6 font-extrabold text-gray-900">
						Step {stepNumber}/{totalSteps}
					</h2>
					{title && (
						<p className="mt-1 text-[14px] leading-4 text-gray-500">{title}</p>
					)}
				</div>

				{/* Right spacer for symmetry */}
				<div className="w-9 h-9" />
			</div>
		</header>
	);
}
