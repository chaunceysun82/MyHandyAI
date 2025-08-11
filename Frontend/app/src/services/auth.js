
const BASE_URL = process.env.REACT_APP_BASE_URL;

if (!BASE_URL) {
	throw new Error("REACT_APP_BASE_URL is not defined in environment variables");
}

export async function loginUser(email, password) {
	try {
		const response = await fetch(`${BASE_URL}/login`, {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify({ email, password }),
		});

		if (!response.ok) {
			alert("Invalid credentials. Please try again");
			console.log("Invalid credentials.");
			const errorData = await response.json();
			throw new Error(errorData.detail || "Login failed");
		}

		const data = await response.json();
		return data; // { message: "Login successful", id: "..." }
	} catch (error) {
		throw new Error(error.message || "Login error");
	}
}

// New function for combined signup with onboarding data
export async function signupUserWithOnboarding(userData, onboardingAnswers) {
	try {
		// Transform onboarding answers to user schema fields
		const transformedOnboardingData = transformOnboardingAnswers(onboardingAnswers);
		
		// Combine user data with onboarding data
		const completeUserData = {
			...userData,
			...transformedOnboardingData
		};

		console.log("Complete user data for signup:", completeUserData);

		const response = await fetch(`${BASE_URL}/users`, {
			method: "POST",
			headers: {
				"Content-Type": "application/json",
			},
			body: JSON.stringify(completeUserData),
		});

		if (!response.ok) {
			const error = await response.json();
			throw new Error(error.detail || "Signup failed");
		}

		return await response.json();
	} catch (error) {
		throw error;
	}
}

export async function updateUser(userId, userData) {
	try {
		const response = await fetch(`${BASE_URL}/users/${userId}`, {
			method: "PUT",
			headers: {
				"Content-Type": "application/json",
			},
			body: JSON.stringify(userData),
		});

		if (!response.ok) {
			const error = await response.json();
			throw new Error(error.detail || "Update failed");
		}

		return await response.json();
	} catch (error) {
		throw error;
	}
}

// Helper function to transform onboarding answers to user schema format
export const transformOnboardingAnswers = (onboardingAnswers) => {
	const userData = {};
	
	Object.entries(onboardingAnswers).forEach(([questionId, answer]) => {
		if (typeof answer === 'string') {
			handleStringAnswer(answer, userData);
		} else if (Array.isArray(answer)) {
			userData.tools = answer.join(', ');
		} else if (typeof answer === 'object' && answer.country) {
			userData.country = answer.country;
			userData.state = answer.state;
		} else if (typeof answer === 'number') {
			userData.confidence = answer;
		}
	});
	
	return userData;
};

// Helper function to handle string answers
export const handleStringAnswer = (answer, userData) => {
	const lowerAnswer = answer.toLowerCase();
	
	if (lowerAnswer.includes('experience') || lowerAnswer.includes('level')) {
		userData.experienceLevel = answer;
	} else if (lowerAnswer.includes('confidence') || lowerAnswer.includes('confident')) {
		const confidenceMap = {
			'not confident at all': 1,
			'slightly confident': 2,
			'somewhat confident': 3,
			'confident': 4,
			'very confident': 5
		};
		userData.confidence = confidenceMap[lowerAnswer] || 3;
	} else if (lowerAnswer.includes('describe') || lowerAnswer.includes('about')) {
		userData.describe = answer;
	} else if (lowerAnswer.includes('tools') || lowerAnswer.includes('equipment')) {
		userData.tools = answer;
	} else if (lowerAnswer.includes('projects') || lowerAnswer.includes('interested')) {
		userData.interestedProjects = answer;
	} else if (lowerAnswer.includes('country')) {
		userData.country = answer;
	} else if (lowerAnswer.includes('state') || lowerAnswer.includes('province')) {
		userData.state = answer;
	} else {
		// Default case - try to infer the field based on the answer content
		if (!userData.describe && (lowerAnswer.length > 20 || lowerAnswer.includes(' '))) {
			userData.describe = answer;
		} else if (!userData.tools && (lowerAnswer.includes('tool') || lowerAnswer.includes('equipment'))) {
			userData.tools = answer;
		} else if (!userData.interestedProjects && (lowerAnswer.includes('project') || lowerAnswer.includes('interested'))) {
			userData.interestedProjects = answer;
		}
	}
};
