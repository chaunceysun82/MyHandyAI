// Or your backend URL

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

export async function signupUser({ firstname, lastname, email, password }) {
	try {
		const response = await fetch(`${BASE_URL}/users`, {
			method: "POST",
			headers: {
				"Content-Type": "application/json",
			},
			body: JSON.stringify({ firstname, lastname, email, password }),
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
