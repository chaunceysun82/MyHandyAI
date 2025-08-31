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

	return backendData.tools_data.tools.map((tool, index) => ({
		_id: tool._id || tool.id || `tool-${index}`, // Ensure unique ID
		id: tool._id || tool.id || `tool-${index}`, // Also add as id for compatibility
		name: tool.name || "Unknown Tool",
		description: tool.description || "",
		price: tool.price || 0,
		priceMin: tool.priceMin || tool.price_min || tool.price || 0,
		priceMax: tool.priceMax || tool.price_max || tool.price || 0,
		price_range: tool.price_range || (tool.price ? `$${tool.price}` : ""),
		rating: 4.0, // Default rating since backend doesn't provide it
		reviews: 0, // Default reviews since backend doesn't specify
		link: tool.amazon_link || tool.link || "https://www.amazon.com",
		required: tool.required !== undefined ? tool.required : true, // Use backend value if available
		image: tool.image_link || tool.image || "",
		riskFactors: tool.risk_factors || tool.riskFactors || "",
		safetyMeasures: tool.safety_measures || tool.safetyMeasures || ""
	}));
}

// Mock tools data for development/testing
export const mockTools = [
	{
		_id: "mock-tool-1",
		id: "mock-tool-1",
		name: "Drill",
		price: 50, // Add single price for testing
		priceMin: 25,
		priceMax: 150,
		price_range: "$25 - $150",
		rating: 4.5,
		reviews: 1250,
		link: "https://amazon.com/drill",
		required: true,
		image: ""
	},
	{
		_id: "mock-tool-2",
		id: "mock-tool-2",
		name: "Screwdriver Set",
		price: 30, // Add single price for testing
		priceMin: 15,
		priceMax: 45,
		price_range: "$15 - $45",
		rating: 4.2,
		reviews: 890,
		link: "https://amazon.com/screwdriver",
		required: true,
		image: ""
	},
	{
		_id: "mock-tool-3",
		id: "mock-tool-3",
		name: "Measuring Tape",
		price: 15, // Add single price for testing
		priceMin: 8,
		priceMax: 25,
		price_range: "$8 - $25",
		rating: 4.0,
		reviews: 567,
		link: "https://amazon.com/tape",
		required: true,
		image: ""
	},
	{
		_id: "mock-tool-4",
		id: "mock-tool-4",
		name: "Level",
		price: 20, // Add single price for testing
		priceMin: 12,
		priceMax: 35,
		price_range: "$12 - $35",
		rating: 4.3,
		reviews: 432,
		link: "https://amazon.com/level",
		required: false,
		image: ""
	}
];
