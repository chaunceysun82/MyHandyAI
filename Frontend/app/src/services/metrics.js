import { normalizeApiBaseUrl } from "./api";

const BASE_URL = normalizeApiBaseUrl(process.env.REACT_APP_BASE_URL);

const VISITOR_KEY = "metricsVisitorId";
const SESSION_KEY = "metricsSessionId";
const DEDUPE_PREFIX = "metricsDeduped";

function createId(prefix) {
	return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

function getStorageUserId() {
	return localStorage.getItem("authToken") || sessionStorage.getItem("authToken") || null;
}

export function getVisitorId() {
	let visitorId = localStorage.getItem(VISITOR_KEY);
	if (!visitorId) {
		visitorId = createId("visitor");
		localStorage.setItem(VISITOR_KEY, visitorId);
	}
	return visitorId;
}

export function getMetricsSessionId() {
	let sessionId = sessionStorage.getItem(SESSION_KEY);
	if (!sessionId) {
		sessionId = createId("session");
		sessionStorage.setItem(SESSION_KEY, sessionId);
	}
	return sessionId;
}

function getDedupedKey(key) {
	return `${DEDUPE_PREFIX}:${key}`;
}

export function hasTrackedMetric(key) {
	return sessionStorage.getItem(getDedupedKey(key)) === "true";
}

export function markMetricTracked(key) {
	sessionStorage.setItem(getDedupedKey(key), "true");
}

export async function trackMetric(eventType, payload = {}) {
	if (!BASE_URL) {
		return null;
	}

	const body = {
		eventType,
		userId: payload.userId ?? getStorageUserId(),
		projectId: payload.projectId ?? null,
		stepNumber: payload.stepNumber ?? null,
		path: payload.path ?? window.location.pathname,
		sessionId: payload.sessionId ?? getMetricsSessionId(),
		visitorId: payload.visitorId ?? getVisitorId(),
		metadata: payload.metadata ?? {},
	};

	try {
		const response = await fetch(`${BASE_URL}/logs`, {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify(body),
			keepalive: true,
		});

		if (!response.ok) {
			throw new Error(`Failed to track metric: ${response.status}`);
		}

		return await response.json();
	} catch (error) {
		console.warn("[metrics] tracking failed", error);
		return null;
	}
}

export async function trackMetricOnce(key, eventType, payload = {}) {
	if (hasTrackedMetric(key)) {
		return null;
	}

	markMetricTracked(key);
	const result = await trackMetric(eventType, payload);
	return result;
}
