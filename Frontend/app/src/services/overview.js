// src/services/overview.js
import { authHeaders, normalizeApiBaseUrl } from "./api";

const API = normalizeApiBaseUrl(process.env.REACT_APP_BASE_URL);
const log = (...args) => console.log("[Overview]", ...args);

async function safeJson(res) {
	try {
		return await res.json();
	} catch {
		return null;
	}
}
function errMsg(res, body) {
	if (!body) return res.statusText;
	if (typeof body === "string") return body;
	return body.detail || JSON.stringify(body);
}


export async function fetchEstimations(projectId) {
	const url = `${API}/generation/estimation/${encodeURIComponent(projectId)}`;
	const res = await fetch(url, {
		headers: authHeaders(),
	});
	const body = await safeJson(res);

	log("fetchEstimations:response", { url, status: res.status });
	log("fetchEstimations:payload", body);

	if (!res.ok) throw new Error(errMsg(res, body));

	return body;
}

export async function fetchProject(projectId) {
	const url = `${API}/project/${encodeURIComponent(projectId)}`;
	const res = await fetch(url, {
		headers: authHeaders(),
	});
	const body = await safeJson(res);

	log("fetchProject:response", { url, status: res.status });
	log("fetchProject:payload", body);

	if (!res.ok) throw new Error(errMsg(res, body));
	return body;
}

// ---------- Steps ----------
export async function fetchSteps(projectId) {
	// let url = `${API}/projects/steps/${encodeURIComponent(projectId)}`;
	// let res = await fetch(url);
	// let body = await safeJson(res);

	// log("fetchSteps:response(saved)", { url, status: res.status });
	// if (res.ok && body) {
	// 	log("fetchSteps:payload(saved)", body);
	// 	return body;
	// }

	let url = `${API}/generation/steps/${encodeURIComponent(projectId)}`;
	let res = await fetch(url, {
		headers: authHeaders(),
	});
	let body = await safeJson(res);

	log("fetchSteps:response(generated)", { url, status: res.status });
	log("fetchSteps:generated", body);

	if (!res.ok) throw new Error(errMsg(res, body));
	return body;
}
