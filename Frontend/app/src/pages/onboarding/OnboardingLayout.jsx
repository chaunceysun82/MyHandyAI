import PrimaryButton from "../../components/onboarding/PrimaryButton";

const OnboardingLayout = ({
	children,
	currentStep = 1,
	totalSteps = 1,
	onNext,
	onBack,
	onSkip,
	primaryLabel,
	disableNext = false,
	showSkip = false,
}) => {
	const progress = (currentStep / totalSteps) * 100;

	return (
		<div className="p-4 max-w-md mx-auto min-h-screen flex flex-col">
			<div className="flex items-center justify-between mb-2">
				<button
					onClick={onBack}
					className="text-gray-500 hover:text-gray-700 text-xl">
					←
				</button>
				<span className="text-sm text-gray-500">
					{currentStep} of {totalSteps}
				</span>
			</div>

			<div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden mb-6">
				<div
					className="h-full bg-green-500 transition-all duration-300"
					style={{ width: `${progress}%` }}
				/>
			</div>

			{/* Main content area with proper height distribution */}
			<div className="flex-1 min-h-0">{children}</div>

			<div className="w-full max-w-sm mx-auto fixed bottom-8 left-0 right-0 px-6">
				{showSkip && (
					<button
						onClick={onSkip}
						className="text-sm py-6 text-gray-500  w-full text-center">
						Skip this question
					</button>
				)}
				<PrimaryButton
					label={primaryLabel ?? "Continue"}
					onClick={onNext}
					disabled={disableNext}
					className="bg-green-600 hover:bg-green-700"
				/>
			</div>
		</div>
	);
};

export default OnboardingLayout;
