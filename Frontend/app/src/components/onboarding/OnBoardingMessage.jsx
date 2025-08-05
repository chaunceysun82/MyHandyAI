import React from "react";
import PrimaryButton from "./PrimaryButton"; // Adjust the path if needed

const OnboardingMessageScreen = ({
	icon,
	title,
	subtitle,
	buttonText = "Continue",
	onContinue,
	disabled,
}) => {
	return (
		<div className="min-h-screen flex flex-col px-6 pt-20 pb-24 relative">
			<div className="flex flex-col items-center text-center justify-center flex-1">
				{icon && (
					<div className="text-5xl mb-6">
						{typeof icon === "string" ? <span>{icon}</span> : icon}
					</div>
				)}

				<h1 className="text-2xl font-semibold text-gray-900 mb-2">{title}</h1>

				{subtitle && <p className="text-gray-500 max-w-xs mb-12">{subtitle}</p>}
			</div>

			<div className="w-full max-w-sm mx-auto fixed bottom-12 left-0 right-0 px-6">
				<PrimaryButton
					label={buttonText}
					onClick={onContinue}
					disabled={disabled}
					className="hover:bg-green-700 transition text-white"
				/>
			</div>
		</div>
	);
};

export default OnboardingMessageScreen;
