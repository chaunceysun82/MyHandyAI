import StepHeader from "./StepHeader";
import StepFooter from "./StepFooter";

export default function ToolsLayout({
	stepNumber,
	totalSteps,
	title,
	children,
	onBack,
	onPrev,
	onNext,
	projectId,
	projectName,
}) {
	return (
		<div className="flex flex-col h-screen bg-gray-50">
			{/* Header */}
			<StepHeader
				stepNumber={stepNumber}
				totalSteps={totalSteps}
				title={title}
				onBack={onBack}
			/>

			{/* Middle Content */}
			<main className="flex-1 overflow-y-auto p-4">{children}</main>

			{/* Footer */}
			<StepFooter 
				projectId={projectId}
				projectName={projectName}
				stepNumber={stepNumber}
				stepTitle={title}
				totalSteps={totalSteps}
				onPrev={onPrev} 
				onNext={onNext}
				isPrevDisabled={false} // Enable previous button to go back to overview
				isNextDisabled={false}
				isNextFinal={false}
			/>
		</div>
	);
}
