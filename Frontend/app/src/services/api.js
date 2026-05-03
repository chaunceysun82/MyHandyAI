import { getCognitoIdToken } from "./cognitoAuth";

export function authHeaders(extraHeaders = {}) {
	const token = getCognitoIdToken();

	return {
		...extraHeaders,
		...(token ? { Authorization: `Bearer ${token}` } : {}),
	};
}

export function jsonAuthHeaders(extraHeaders = {}) {
	return authHeaders({
		"Content-Type": "application/json",
		...extraHeaders,
	});
}

export function axiosAuthConfig(config = {}) {
	return {
		...config,
		headers: authHeaders(config.headers || {}),
	};
}
