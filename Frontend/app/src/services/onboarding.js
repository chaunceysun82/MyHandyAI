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
	console.log("Answers type:", typeof answers);
	console.log("Answers keys:", Object.keys(answers));
	
	// Check if this is a new signup with onboarding data
	const tempUserData = localStorage.getItem("tempUserData");
	const userId = localStorage.getItem("authToken") || sessionStorage.getItem("authToken");
	
	console.log("Onboarding submission - checking user data:", {
		hasTempUserData: !!tempUserData,
		hasUserId: !!userId,
		tempUserData: tempUserData ? "Present" : "Not present",
		userId: userId ? "Present" : "Not present"
	});
	
	if (tempUserData) {
		// This is a new signup (email or Google) - user already exists in DB, just update with onboarding data
		try {
			const userData = JSON.parse(tempUserData);
			const userId = userData.userId;
			
			if (!userId) {
				throw new Error("User ID not found for onboarding update");
			}
			
			// Transform onboarding answers to user schema fields
			const transformedOnboardingData = transformOnboardingAnswers(answers);
			console.log("Transformed onboarding data:", transformedOnboardingData);
			
			// Update existing user with onboarding data using PUT
			const result = await updateUser(userId, transformedOnboardingData);
			console.log("User updated with onboarding data:", result);
			
			// Store the user ID for authentication
			localStorage.setItem("authToken", userId);
			
			// Store user email for display in SideNavbar
			if (userData.email) {
				localStorage.setItem("userEmail", userData.email);
			}
			
			localStorage.removeItem("tempUserData");
			console.log("User authenticated after onboarding completion");
			
			return result;
		} catch (error) {
			console.error("Error updating user with onboarding data:", error);
			throw error;
		}
	} else if (userId) {
		// This is an existing user (email or Google) updating their onboarding data
		try {
			// First, check if user exists in backend
			const userResponse = await fetch(`${BASE_URL}/users/${userId}`);
			
			if (userResponse.ok) {
				// User exists, update with onboarding data
				console.log("Updating existing user with onboarding data for userID:", userId);
				
				// Transform answers to match user schema using the shared function from auth.js
				const userUpdateData = transformOnboardingAnswers(answers);
				console.log("Transformed user data:", userUpdateData);
				
				// Use the shared updateUser function
				const result = await updateUser(userId, userUpdateData);
				console.log("User updated successfully:", result);
				
				return result;
			} else {
				// User doesn't exist in backend - this shouldn't happen for existing users
				throw new Error("User not found in backend");
			}
		} catch (error) {
			console.error("Error updating existing user with onboarding data:", error);
			throw error;
		}
	} else {
		// No user data or user ID found
		console.error("No user data or user ID found for onboarding submission");
		throw new Error("No user data found for onboarding submission");
	}
};
