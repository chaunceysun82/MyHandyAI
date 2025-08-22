// Helper functions for step data processing

// Extract specific step from the steps data
export const extractSpecificStep = (stepsData, stepIndex) => {
	console.log("StepUtils: extractSpecificStep called with:", { stepIndex, stepsData });
	
	// Handle different data structures from the API
	if (Array.isArray(stepsData)) {
		console.log("StepUtils: Using direct array, length:", stepsData.length);
		console.log("StepUtils: Available steps:", stepsData.map((s, i) => ({ index: i, title: s.title || s.step_title || `Step ${i}` })));
		const result = stepsData[stepIndex];
		console.log("StepUtils: Extracted step at index", stepIndex, ":", result);
		return result;
	}
	
	if (stepsData?.steps_data?.steps && Array.isArray(stepsData.steps_data.steps)) {
		console.log("StepUtils: Using steps_data.steps, length:", stepsData.steps_data.steps.length);
		console.log("StepUtils: Available steps:", stepsData.steps_data.steps.map((s, i) => ({ index: i, title: s.title || s.step_title || `Step ${i}` })));
		const result = stepsData.steps_data.steps[stepIndex];
		console.log("StepUtils: Extracted step at index", stepIndex, ":", result);
		return result;
	}
	
	if (stepsData?.steps && Array.isArray(stepsData.steps)) {
		console.log("StepUtils: Using steps array, length:", stepsData.steps.length);
		console.log("StepUtils: Available steps:", stepsData.steps.map((s, i) => ({ index: i, title: s.title || s.step_title || `Step ${i}` })));
		const result = stepsData.steps[stepIndex];
		console.log("StepUtils: Extracted step at index", stepIndex, ":", result);
		return result;
	}
	
	console.log("StepUtils: No valid steps data structure found");
	return null;
};

// Transform step data to our display format
export const transformStepData = (stepData, stepNumber, allStepsData) => {
	console.log("StepUtils: transformStepData called with:", {
		stepData,
		stepNumber,
		allStepsDataLength: Array.isArray(allStepsData) ? allStepsData.length : 'Not an array'
	});
	
	// Log all available fields in stepData
	console.log("StepUtils: Available fields in stepData:", Object.keys(stepData));
	console.log("StepUtils: videoUrl field value:", stepData.videoUrl);
	console.log("StepUtils: video_url field value:", stepData.video_url);
	console.log("StepUtils: youtube field value:", stepData.youtube);
	
	const result = {
		number: stepNumber,
		total: getTotalSteps(allStepsData),
		title: stepData.title || stepData.step_title || `Step ${stepNumber}`,
		subtitle: stepData.subtitle || stepData.summary || stepData.description || "Step description",
		time: stepData.time_text || stepData.time || stepData.est_time_min ? `${stepData.est_time_min} min` : "10-15 min",
		timeMin: extractTimeMin(stepData.time_text || stepData.time || stepData.est_time_min),
		timeMax: extractTimeMax(stepData.time_text || stepData.time || stepData.est_time_min),
		description: stepData.description || stepData.summary || stepData.subtitle || "Complete this step to move forward with your project.",
		instructions: formatInstructions(stepData.instructions || stepData.instruction || []),
		toolsNeeded: formatToolsNeeded(stepData.tools_needed || stepData.tools || stepData.toolsNeeded || []),
		safety: formatSafetyWarnings(stepData.safety_warnings || stepData.safety || stepData.safety_warning || []),
		tips: formatTips(stepData.tips || stepData.tip || []),
		imageUrl: stepData.imageUrl || stepData.image_url || null,
		videoUrl: stepData.videoUrl || stepData.video_url || stepData.youtube || null,
		completed: stepData.completed || false // Add the completed field from API data
	};
	
	console.log("StepUtils: Transformed result:", result);
	console.log("StepUtils: Final videoUrl value:", result.videoUrl);
	console.log("StepUtils: Final step object:", { number: result.number, total: result.total, completed: result.completed });
	return result;
};

// Get total number of steps (including Tools Required step)
export const getTotalSteps = (stepsData) => {
	let backendSteps = 0;
	
	console.log("StepUtils: getTotalSteps called with:", stepsData);
	
	if (Array.isArray(stepsData)) {
		backendSteps = stepsData.length;
		console.log("StepUtils: Using direct array, backendSteps:", backendSteps);
	} else if (stepsData?.steps_data?.steps && Array.isArray(stepsData.steps_data.steps)) {
		backendSteps = stepsData.steps_data.steps.length;
		console.log("StepUtils: Using steps_data.steps, backendSteps:", backendSteps);
	} else if (stepsData?.steps && Array.isArray(stepsData.steps)) {
		backendSteps = stepsData.steps.length;
		console.log("StepUtils: Using steps array, backendSteps:", backendSteps);
	}
	
	// Add 1 for the "Tools Required" step that's always shown first
	const totalSteps = backendSteps + 1;
	console.log("StepUtils: Final totalSteps (including Tools):", totalSteps);
	return totalSteps;
};

// Helper functions to extract and generate step data
export const extractTimeMin = (timeText) => {
	if (!timeText) return 10;
	const match = timeText.match(/(\d+)/);
	return match ? parseInt(match[1]) : 10;
};

export const extractTimeMax = (timeText) => {
	if (!timeText) return 15;
	const match = timeText.match(/(\d+).*?(\d+)/);
	return match ? parseInt(match[2]) : 15;
};

export const formatInstructions = (instructions) => {
	if (!instructions) return [];
	
	// Handle both array and string formats
	if (Array.isArray(instructions)) {
		return instructions.map(inst => {
			if (typeof inst === 'string') {
				// Capitalize the first letter of each sentence
				return inst.split('. ').map(sentence => {
					if (sentence.trim()) {
						return sentence.charAt(0).toUpperCase() + sentence.slice(1);
					}
					return sentence;
				}).join('. ');
			}
			return String(inst);
		});
	}
	
	// If it's a string, split by periods and format
	if (typeof instructions === 'string') {
		return instructions.split('. ').map(sentence => {
			if (sentence.trim()) {
				return sentence.charAt(0).toUpperCase() + sentence.slice(1);
			}
			return sentence;
		}).filter(Boolean);
	}
	
	return [];
};

export const formatToolsNeeded = (tools) => {
	if (!tools) return [];
	
	// Handle both array and string formats
	if (Array.isArray(tools)) {
		return tools.map(tool => {
			if (typeof tool === 'string') {
				return tool.charAt(0).toUpperCase() + tool.slice(1);
			}
			return String(tool);
		});
	}
	
	// If it's a string, split by commas and format
	if (typeof tools === 'string') {
		return tools.split(',').map(tool => {
			const trimmed = tool.trim();
			return trimmed.charAt(0).toUpperCase() + trimmed.slice(1);
		}).filter(Boolean);
	}
	
	return [];
};

export const formatSafetyWarnings = (warnings) => {
	if (!warnings) return [];
	
	if (Array.isArray(warnings)) {
		// Return array format for bullet point display
		return warnings.map(warning => {
			if (typeof warning === 'string') {
				return warning.charAt(0).toUpperCase() + warning.slice(1);
			}
			return String(warning);
		});
	}
	
	if (typeof warnings === 'string') {
		// Split by periods and format as array for bullet points
		return warnings.split('. ').map(warning => {
			const trimmed = warning.trim();
			if (trimmed) {
				return trimmed.charAt(0).toUpperCase() + trimmed.slice(1);
			}
			return trimmed;
		}).filter(Boolean);
	}
	
	return [];
};

export const formatTips = (tips) => {
	if (!tips) return [];
	
	if (Array.isArray(tips)) {
		// Return array format for bullet point display
		return tips.map(tip => {
			if (typeof tip === 'string') {
				return tip.charAt(0).toUpperCase() + tip.slice(1);
			}
			return String(tip);
		});
	}
	
	if (typeof tips === 'string') {
		// Split by periods and format as array for bullet points
		return tips.split('. ').map(tip => {
			const trimmed = tip.trim();
			if (trimmed) {
				return trimmed.charAt(0).toUpperCase() + trimmed.slice(1);
			}
			return trimmed;
		}).filter(Boolean);
	}
	
	return [];
};
