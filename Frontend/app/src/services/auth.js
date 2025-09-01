
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

export async function getUserById(userId) {
  const res = await fetch(`${BASE_URL}/users/${userId}`);
  if (!res.ok) {
    let msg = res.statusText;
    try { msg = (await res.json()).detail || msg; } catch {}
    throw new Error(msg);
  }
  return res.json(); // { _id, firstname, lastname, ... }
}

// Check if email already exists in database
export async function checkEmailExists(email) {
	// Since backend doesn't have a dedicated email check endpoint,
	// we'll let the backend handle email existence during actual signup
	// This prevents the complex create/delete logic that can cause issues
	return false;
}

// Create user during signup (before onboarding)
export async function createUserDuringSignup(userData) {
	try {
		const response = await fetch(`${BASE_URL}/users`, {
			method: "POST",
			headers: {
				"Content-Type": "application/json",
			},
			body: JSON.stringify(userData),
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

// Check if user has completed onboarding
export function hasCompletedOnboarding(user) {
	// Check if user has the essential onboarding fields
	// These fields are typically set during onboarding completion
	const onboardingFields = [
		'experienceLevel',
		'confidence', 
		'tools',
		'interestedProjects',
		'country',
		'state'
	];
	
	// User has completed onboarding if they have at least 3 of these fields
	// and the fields have meaningful values (not just empty strings or null)
	const completedFields = onboardingFields.filter(field => {
		const value = user[field];
		return value && 
			   value !== "" && 
			   value !== null && 
			   value !== undefined &&
			   (typeof value === 'string' ? value.trim().length > 0 : true);
	});
	
	// Also check if user has a describe field as it's often filled during onboarding
	if (user.describe && user.describe.trim().length > 0) {
		completedFields.push('describe');
	}
	
	// User has completed onboarding if they have at least 3 meaningful onboarding fields
	return completedFields.length >= 3;
}