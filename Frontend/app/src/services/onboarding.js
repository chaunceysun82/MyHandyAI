import axios from "axios";
import { signupUserWithOnboarding, updateUser, transformOnboardingAnswers } from "./auth";

const BASE_URL = process.env.REACT_APP_BASE_URL;

export const fetchOnboardingQuestions = async () => {
	try {
		const response = await axios.get(`${BASE_URL}/onboarding/`);
		console.log("Onboarding questions fetched:", response.data);
		return response.data; // Assuming backend returns the array directly
	} catch (error) {
		console.error("Error fetching onboarding questions:", error);
		throw error;
	}
};

export const submitOnboardingAnswers = async (answers) => {
	console.log("Submitting onboarding answers:", answers);
	
	// Check if this is a new signup with onboarding data
	const tempUserData = localStorage.getItem("tempUserData");
	
	if (tempUserData) {
		// This is a new signup - use combined signup approach
		try {
			const userData = JSON.parse(tempUserData);
			const result = await signupUserWithOnboarding(userData, answers);
			console.log("User created with onboarding data:", result);
			
			// Store the user ID for authentication
			if (result.id) {
				localStorage.setItem("authToken", result.id);
				localStorage.removeItem("tempUserData");
				console.log("User authenticated after combined signup");
			}
			
			return result;
		} catch (error) {
			console.error("Error in combined signup:", error);
			throw error;
		}
	} else {
		// This is an existing user updating their onboarding data
		const userId = localStorage.getItem("authToken") || sessionStorage.getItem("authToken");
		console.log("Updating existing user with onboarding data for userID:", userId);
		
		if (!userId) {
			console.error("No user ID found for onboarding submission");
			return;
		}

		try {
			// Transform answers to match user schema using the shared function from auth.js
			const userUpdateData = transformOnboardingAnswers(answers);
			console.log("Transformed user data:", userUpdateData);
			
			// Use the shared updateUser function
			const result = await updateUser(userId, userUpdateData);
			console.log("User updated successfully:", result);
			
			return result;
		} catch (error) {
			console.error("Error updating user with onboarding data:", error);
			throw error;
		}
	}
};
