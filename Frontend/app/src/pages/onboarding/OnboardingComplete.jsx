import React from "react";
import { useNavigate } from "react-router-dom";
import OnboardingMessageScreen from "../../components/onboarding/OnBoardingMessage"; // adjust the path as needed
import "../../styles/animations/OnboardingComplete.css"; // keep animation styles

const OnboardingComplete = () => {
	const navigate = useNavigate();

	const TickAnimation = (
		<svg
			className="checkmark"
			xmlns="http://www.w3.org/2000/svg"
			viewBox="0 0 52 52">
			<circle
				className="checkmark__circle"
				cx="26"
				cy="26"
				r="25"
				fill="none"
			/>
			<path className="checkmark__check" fill="none" d="M14 27l7 7 16-16" />
		</svg>
	);

	return (
		<OnboardingMessageScreen
			icon={<div className="tick-container">{TickAnimation}</div>}
			title="You’re all set!"
			subtitle="From the information you’ve provided, we’ve set up a personalized system just for you."
			buttonText="Finish"
			onContinue={() => navigate("/home")}
		/>
	);
};

export default OnboardingComplete;
