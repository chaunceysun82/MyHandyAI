// src/services/tools.js
const API = process.env.REACT_APP_BASE_URL;
const log = (...args) => console.log("[Tools]", ...args);

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

export async function fetchProjectTools(projectId) {
	try {
		// First try to get tools from the project steps endpoint
		// const url = `${API}/projects/steps/${encodeURIComponent(projectId)}`;
		// const res = await fetch(url);
		// const body = await safeJson(res);

		// log("fetchProjectTools:response", { url, status: res.status });
		// log("fetchProjectTools:payload", body);

		// if (res.ok && body) {
		// 	// Extract tools from the project data if available
		// 	const tools = extractToolsFromProject(body);
		// 	if (tools && tools.length > 0) {
		// 		return tools;
		// 	}
		// }

		// Fallback: try to get tools from generation endpoint
		const genUrl = `${API}/generation/tools/${encodeURIComponent(projectId)}`;
		const genRes = await fetch(genUrl);
		const genBody = await safeJson(genRes);

		log("fetchProjectTools:generation_response", { url: genUrl, status: genRes.status });
		log("fetchProjectTools:generation_payload", genBody);

		if (!genRes.ok) {
			throw new Error(errMsg(genRes, genBody));
		}

		return genBody;
	} catch (error) {
		log("fetchProjectTools:error", error);
		throw error;
	}
}

function extractToolsFromProject(projectData) {
	// Try to extract tools from various possible locations in the project data
	const tools = [];
	
	// Check if tools are directly in the project data
	if (projectData.tools && Array.isArray(projectData.tools)) {
		return projectData.tools;
	}
	
	// Check if tools are in steps data
	if (projectData.steps_data && projectData.steps_data.tools) {
		return projectData.steps_data.tools;
	}
	
	// Check if tools are embedded in individual steps
	if (projectData.steps && Array.isArray(projectData.steps)) {
		projectData.steps.forEach(step => {
			if (step.tools && Array.isArray(step.tools)) {
				tools.push(...step.tools);
			}
		});
	}
	
	return tools;
}

// Transform backend tools data to frontend format
export function transformToolsData(backendData) {
	if (!backendData || !backendData.tools_data || !backendData.tools_data.tools) {
		return [];
	}

	return backendData.tools_data.tools.map(tool => ({
		name: tool.name || "Unknown Tool",
		description: tool.description || "",
		price: tool.price || 0,
		priceMin: tool.price || 0,
		priceMax: tool.price || 0,
		rating: 4.0, // Default rating since backend doesn't provide it
		reviews: 0, // Default reviews since backend doesn't provide it
		link: tool.amazon_link || "https://www.amazon.com",
		required: true, // Default to required since backend doesn't specify
		image: tool.image_link || "",
		riskFactors: tool.risk_factors || "",
		safetyMeasures: tool.safety_measures || ""
	}));
}

// Mock tools data for development/testing
export const mockTools = [
	{
		name: "Drill",
		priceMin: 25,
		priceMax: 150,
		rating: 4.5,
		reviews: 1250,
		link: "https://amazon.com/drill",
		required: true,
		image: ""
	},
	{
		name: "Screwdriver Set",
		priceMin: 15,
		priceMax: 45,
		rating: 4.2,
		reviews: 890,
		link: "https://amazon.com/screwdriver",
		required: true,
		image: ""
	},
	{
		name: "Measuring Tape",
		priceMin: 8,
		priceMax: 25,
		rating: 4.0,
		reviews: 567,
		link: "https://amazon.com/tape",
		required: true,
		image: ""
	},
	{
		name: "Level",
		priceMin: 12,
		priceMax: 35,
		rating: 4.3,
		reviews: 432,
		link: "https://amazon.com/level",
		required: false,
		image: ""
	}
];
