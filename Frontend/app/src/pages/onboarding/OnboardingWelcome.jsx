// /pages/onboarding/OnboardingWelcome.jsx
import React from "react";
import { useNavigate } from "react-router-dom";
import OnboardingMessageScreen from "../../components/onboarding/OnBoardingMessage";

const OnboardingWelcome = () => {
	const navigate = useNavigate();

	return (
		<OnboardingMessageScreen
			icon=""
			title="👋 Welcome to MyHandyAI"
			subtitle="Let’s get you set up!"
			buttonText="Continue"
			onContinue={() => navigate("/onboarding/1")}
		/>
	);
};

export default OnboardingWelcome;
