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
	const authToken = localStorage.getItem("authToken") || sessionStorage.getItem("authToken");
	
	if (tempUserData) {
		// This is a new signup - user already exists in DB, just update with onboarding data
		try {
			const userData = JSON.parse(tempUserData);
			const userId = userData.userId;
			
			if (!userId) {
				throw new Error("User ID not found for onboarding update");
			}
			
			// Transform onboarding answers to user schema fields
			const transformedOnboardingData = transformOnboardingAnswers(answers);
			
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
	} else if (authToken) {
		// This could be a Google user or existing user updating their onboarding data
		try {
			// First, check if user exists in backend
			const userResponse = await fetch(`${BASE_URL}/users/${authToken}`);
			
			if (userResponse.ok) {
				// User exists, update with onboarding data
				console.log("Updating existing user with onboarding data for userID:", authToken);
				
				// Transform answers to match user schema using the shared function from auth.js
				const userUpdateData = transformOnboardingAnswers(answers);
				console.log("Transformed user data:", userUpdateData);
				
				// Use the shared updateUser function
				const result = await updateUser(authToken, userUpdateData);
				console.log("User updated successfully:", result);
				
				return result;
			} else {
				// User doesn't exist in backend, create new user with Google data
				console.log("Google user not found in backend, creating new user with onboarding data");
				
				// Get user info from localStorage/sessionStorage
				const displayName = localStorage.getItem("displayName") || sessionStorage.getItem("displayName") || "User";
				const email = localStorage.getItem("userEmail") || sessionStorage.getItem("userEmail") || "";
				
				// Create user data for Google user
				const googleUserData = {
					firstname: displayName.split(" ")[0] || displayName,
					lastname: displayName.split(" ").slice(1).join(" ") || "",
					email: email,
					googleId: authToken // Use Firebase UID as Google ID
				};
				
				// Transform onboarding answers
				const transformedOnboardingData = transformOnboardingAnswers(answers);
				
				// Combine user data with onboarding data
				const completeUserData = {
					...googleUserData,
					...transformedOnboardingData
				};
				
				console.log("Complete Google user data for creation:", completeUserData);
				
				// Create user in backend
				const createResponse = await fetch(`${BASE_URL}/users`, {
					method: "POST",
					headers: {
						"Content-Type": "application/json",
					},
					body: JSON.stringify(completeUserData),
				});
				
				if (!createResponse.ok) {
					const error = await createResponse.json();
					throw new Error(error.detail || "Failed to create Google user");
				}
				
				const result = await createResponse.json();
				console.log("Google user created successfully:", result);
				
				// Store user email for display in SideNavbar
				if (email) {
					localStorage.setItem("userEmail", email);
				}
				
				return result;
			}
		} catch (error) {
			console.error("Error handling Google user onboarding:", error);
			throw error;
		}
	} else {
		// No user data or auth token found
		console.error("No user data or auth token found for onboarding submission");
		throw new Error("No user data found for onboarding submission");
	}
};
