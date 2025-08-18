const BASE_URL = process.env.REACT_APP_BASE_URL;

if (!BASE_URL) {
	throw new Error("REACT_APP_BASE_URL is not defined in environment variables");
}

// Toggle step completion status
export const toggleStepCompletion = async (projectId, stepNumber) => {
	try {
		const response = await fetch(`${BASE_URL}/complete-step/${projectId}/${stepNumber}`, {
			method: 'PUT',
			headers: {
				'Content-Type': 'application/json',
			},
			body: JSON.stringify({
				project_id: projectId,
				step_number: stepNumber
			})
		});

		if (!response.ok) {
			throw new Error(`HTTP error! status: ${response.status}`);
		}

		const result = await response.json();
		console.log('Step completion toggled:', result);
		return result;
		
	} catch (error) {
		console.error('Error toggling step completion:', error);
		throw error;
	}
};

// Get step details by project ID and step number
export const getStepDetails = async (projectId, stepNumber) => {
	try {
		const response = await fetch(`${BASE_URL}/steps/${projectId}/${stepNumber}`);
		
		if (!response.ok) {
			throw new Error(`HTTP error! status: ${response.status}`);
		}

		return await response.json();
		
	} catch (error) {
		console.error('Error fetching step details:', error);
		throw error;
	}
};

// Update step progress
export const updateStepProgress = async (projectId, stepNumber, progressData) => {
	try {
		const response = await fetch(`${BASE_URL}/steps/${projectId}/${stepNumber}/progress`, {
			method: 'PUT',
			headers: {
				'Content-Type': 'application/json',
			},
			body: JSON.stringify(progressData)
		});

		if (!response.ok) {
			throw new Error(`HTTP error! status: ${response.status}`);
		}

		return await response.json();
		
	} catch (error) {
		console.error('Error updating step progress:', error);
		throw error;
	}
};
