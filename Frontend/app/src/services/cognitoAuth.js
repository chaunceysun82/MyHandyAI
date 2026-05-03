const cognitoConfig = {
	region: process.env.REACT_APP_COGNITO_REGION || "us-east-2",
	userPoolId: process.env.REACT_APP_COGNITO_USER_POOL_ID || "us-east-2_KA6IF6XAe",
	clientId: process.env.REACT_APP_COGNITO_CLIENT_ID || "27qnru8d8lkf7244oobqg2p3bv",
	domain:
		process.env.REACT_APP_COGNITO_DOMAIN ||
		"https://us-east-2ka6if6xae.auth.us-east-2.amazoncognito.com",
	redirectUri:
		process.env.REACT_APP_COGNITO_REDIRECT_URI ||
		`${window.location.origin}/auth/callback`,
	logoutUri:
		process.env.REACT_APP_COGNITO_LOGOUT_URI ||
		`${window.location.origin}/login`,
	scopes: ["openid", "email", "profile"],
};

const tokenStorage = localStorage;

function base64UrlEncode(buffer) {
	const bytes = new Uint8Array(buffer);
	let binary = "";

	bytes.forEach((byte) => {
		binary += String.fromCharCode(byte);
	});

	return btoa(binary)
		.replace(/\+/g, "-")
		.replace(/\//g, "_")
		.replace(/=+$/, "");
}

function randomString(length = 96) {
	const bytes = new Uint8Array(length);
	window.crypto.getRandomValues(bytes);

	return base64UrlEncode(bytes);
}

async function createCodeChallenge(verifier) {
	const data = new TextEncoder().encode(verifier);
	const digest = await window.crypto.subtle.digest("SHA-256", data);

	return base64UrlEncode(digest);
}

function decodeJwtPayload(token) {
	const payload = token.split(".")[1];
	const normalized = payload.replace(/-/g, "+").replace(/_/g, "/");
	const json = decodeURIComponent(
		atob(normalized)
			.split("")
			.map((char) => `%${`00${char.charCodeAt(0).toString(16)}`.slice(-2)}`)
			.join("")
	);

	return JSON.parse(json);
}

export function getCognitoConfig() {
	return cognitoConfig;
}

export async function redirectToCognitoLogin() {
	const verifier = randomString();
	const challenge = await createCodeChallenge(verifier);
	const state = randomString(32);

	sessionStorage.setItem("cognitoCodeVerifier", verifier);
	sessionStorage.setItem("cognitoOAuthState", state);

	const params = new URLSearchParams({
		client_id: cognitoConfig.clientId,
		response_type: "code",
		scope: cognitoConfig.scopes.join(" "),
		redirect_uri: cognitoConfig.redirectUri,
		code_challenge_method: "S256",
		code_challenge: challenge,
		state,
	});

	window.location.assign(`${cognitoConfig.domain}/oauth2/authorize?${params}`);
}

export async function exchangeCodeForTokens(code, returnedState) {
	const verifier = sessionStorage.getItem("cognitoCodeVerifier");
	const expectedState = sessionStorage.getItem("cognitoOAuthState");

	if (!verifier) {
		throw new Error("Missing Cognito code verifier. Please start login again.");
	}

	if (expectedState && returnedState && expectedState !== returnedState) {
		throw new Error("Invalid Cognito login state. Please start login again.");
	}

	const body = new URLSearchParams({
		grant_type: "authorization_code",
		client_id: cognitoConfig.clientId,
		code,
		redirect_uri: cognitoConfig.redirectUri,
		code_verifier: verifier,
	});

	const response = await fetch(`${cognitoConfig.domain}/oauth2/token`, {
		method: "POST",
		headers: {
			"Content-Type": "application/x-www-form-urlencoded",
		},
		body,
	});

	if (!response.ok) {
		throw new Error("Could not finish Cognito login.");
	}

	const tokens = await response.json();
	storeCognitoTokens(tokens);

	sessionStorage.removeItem("cognitoCodeVerifier");
	sessionStorage.removeItem("cognitoOAuthState");

	return tokens;
}

export function storeCognitoTokens(tokens) {
	tokenStorage.setItem("cognitoAccessToken", tokens.access_token);
	tokenStorage.setItem("cognitoIdToken", tokens.id_token);

	if (tokens.refresh_token) {
		tokenStorage.setItem("cognitoRefreshToken", tokens.refresh_token);
	}
}

export function getCognitoIdToken() {
	return localStorage.getItem("cognitoIdToken") || sessionStorage.getItem("cognitoIdToken");
}

export function getCognitoAccessToken() {
	return (
		localStorage.getItem("cognitoAccessToken") ||
		sessionStorage.getItem("cognitoAccessToken")
	);
}

export function getCognitoUser() {
	const token = getCognitoIdToken();

	if (!token) {
		return null;
	}

	try {
		return decodeJwtPayload(token);
	} catch {
		return null;
	}
}

export function getCognitoTokenExpiration() {
	const user = getCognitoUser();

	if (!user?.exp) {
		return null;
	}

	return user.exp * 1000;
}

export function isCognitoAuthenticated() {
	const expiresAt = getCognitoTokenExpiration();

	return !!expiresAt && expiresAt > Date.now();
}

export function ensureValidCognitoSession() {
	if (getCognitoIdToken() && !isCognitoAuthenticated()) {
		clearAuthStorage();
		return false;
	}

	return isCognitoAuthenticated();
}

export function clearAuthStorage() {
	const keys = [
		"authToken",
		"cognitoAccessToken",
		"cognitoIdToken",
		"cognitoRefreshToken",
		"displayName",
		"userEmail",
		"chatMessages",
		"introShown",
	];

	keys.forEach((key) => {
		localStorage.removeItem(key);
		sessionStorage.removeItem(key);
	});
}

export function redirectToCognitoLogout() {
	clearAuthStorage();

	const params = new URLSearchParams({
		client_id: cognitoConfig.clientId,
		logout_uri: cognitoConfig.logoutUri,
	});

	window.location.assign(`${cognitoConfig.domain}/logout?${params}`);
}
