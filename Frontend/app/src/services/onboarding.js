import axios from "axios";

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

// export const submitOnboardingAnswers = async (userId, answers) => {
// 	try {
// 		const response = await axios.post(`${BASE_URL}/onboarding/submit`, {
// 			userId,
// 			answers,
// 		});

// 		return response.data;
// 	} catch (error) {
// 		console.error("Error submitting onboarding answers:", error);
// 		throw error;
// 	}
// };

export const submitOnboardingAnswers = async (answers) => {
	console.log("Submitting onboarding answers:", answers);
};
