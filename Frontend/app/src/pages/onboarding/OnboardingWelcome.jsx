// /pages/onboarding/OnboardingWelcome.jsx
import React from "react";
import { useNavigate } from "react-router-dom";
import OnboardingMessageScreen from "../../components/onboarding/OnBoardingMessage";

const OnboardingWelcome = () => {
	const navigate = useNavigate();

	const handleBack = () => {
		// Clear auth token so user can go back to login
		localStorage.removeItem("authToken");
		sessionStorage.removeItem("authToken");
		// Always go to login page and replace history
		navigate("/login", { replace: true });
	};

	return (
		<div className="min-h-screen flex flex-col px-6 pt-20 pb-24 relative">
			{/* Back button */}
			<button
				onClick={handleBack}
				className="absolute top-6 left-6 text-gray-500 hover:text-gray-700 text-xl">
				←
			</button>
			
			<OnboardingMessageScreen
				icon=""
				title="👋 Welcome to MyHandyAI"
				subtitle="Let's get you set up!"
				buttonText="Continue"
				onContinue={() => navigate("/onboarding/1")}
			/>
		</div>
	);
};

export default OnboardingWelcome;
