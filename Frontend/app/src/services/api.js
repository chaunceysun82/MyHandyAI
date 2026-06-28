import { clearAuthStorage, ensureValidCognitoSession, getCognitoIdToken } from "./cognitoAuth";

export function normalizeApiBaseUrl(url) {
	return String(url || "").replace(/\/+$/, "");
}

export function authHeaders(extraHeaders = {}) {
	if (!ensureValidCognitoSession()) {
		clearAuthStorage();
		if (!window.location.pathname.startsWith("/login")) {
			window.location.assign("/login");
		}
		return extraHeaders;
	}

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
