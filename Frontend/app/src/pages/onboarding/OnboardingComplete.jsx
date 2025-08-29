import React, { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import OnboardingMessageScreen from "../../components/onboarding/OnBoardingMessage"; // adjust the path as needed
import "../../styles/animations/OnboardingComplete.css"; // keep animation styles

const OnboardingComplete = () => {
	const navigate = useNavigate();

	useEffect(() => {
		// Clean up any temporary data
		const tempUserData = localStorage.getItem("tempUserData");
		if (tempUserData) {
			localStorage.removeItem("tempUserData");
			console.log("Cleaned up temp user data");
		}

		// Clean up all onboarding custom items from localStorage
		const keysToRemove = [];
		for (let i = 0; i < localStorage.length; i++) {
			const key = localStorage.key(i);
			if (key && key.startsWith('onboarding_custom_')) {
				keysToRemove.push(key);
			}
		}
		
		keysToRemove.forEach(key => {
			localStorage.removeItem(key);
			console.log(`Cleaned up onboarding custom items: ${key}`);
		});
	}, []);

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

	const handleFinish = () => {
		console.log("Onboarding completed, navigating to home");
		
		// Set flag to indicate user is coming from onboarding
		localStorage.setItem("fromOnboarding", "true");
		
		// For Google users, ensure proper token is set
		const tempGoogleAuthToken = localStorage.getItem("tempGoogleAuthToken");
		if (tempGoogleAuthToken) {
			// Update authToken with the final backend user ID
			const finalAuthToken = localStorage.getItem("authToken");
			if (finalAuthToken && finalAuthToken !== tempGoogleAuthToken) {
				localStorage.setItem("authToken", finalAuthToken);
			}
			localStorage.removeItem("tempGoogleAuthToken");
		}
		
		navigate("/home");
	};

	return (
		<OnboardingMessageScreen
			icon={<div className="tick-container">{TickAnimation}</div>}
			title="You're all set!"
			subtitle="From the information you've provided, we've set up a personalized system just for you."
			buttonText="Finish"
			onContinue={handleFinish}
		/>
	);
};

export default OnboardingComplete;
