/**
 * Text processing utilities for chat messages
 */

/**
 * Splits a message into logical parts for better readability
 * @param {string} content - The message content to split
 * @returns {Array} Array of message parts with type, content, and icon
 */
export const splitMessageIntoParts = (content) => {
	// Check if this looks like a structured step message
	if (content.includes("**Step") || content.includes("⏱️") || content.includes("🔧")) {
		return splitStructuredMessage(content);
	}
	
	// For regular messages, split by paragraphs or logical breaks
	const paragraphs = content.split(/\n\s*\n/).filter(p => p.trim());
	
	if (paragraphs.length > 1) {
		// Multiple paragraphs - split into separate bubbles
		return paragraphs.map((paragraph, index) => ({
			type: "paragraph",
			content: paragraph.trim(),
			icon: "BOT"
		}));
	} else {
		// Single paragraph - check if it has multiple sentences that could be split
		return splitSingleParagraph(content);
	}
};

/**
 * Splits structured messages (with emojis) into sections
 * @param {string} content - The structured message content
 * @returns {Array} Array of message parts
 */
const splitStructuredMessage = (content) => {
	const sections = content.split(/\n(?=⏱️|🔧|⚠️|📋|💡)/);
	
	return sections.map((section, index) => {
		// Handle the main step header
		if (section.includes("**Step")) {
			const stepMatch = section.match(/\*\*(.*?)\*\*/);
			const stepText = stepMatch ? stepMatch[1] : section;
			return {
				type: "step-header",
				content: stepText,
				icon: "📋"
			};
		}
		
		// Handle other sections
		if (section.trim()) {
			const icon = section.charAt(0);
			const content = section.substring(1).trim();
			
			let sectionType = "info";
			if (icon === "⏱️") sectionType = "time";
			else if (icon === "🔧") sectionType = "tools";
			else if (icon === "⚠️") sectionType = "warning";
			else if (icon === "📋") sectionType = "instructions";
			else if (icon === "💡") sectionType = "tip";
			
			return {
				type: sectionType,
				content: content,
				icon: icon
			};
		}
		
		return null;
	}).filter(Boolean);
};

/**
 * Splits a single paragraph into sentences or chunks
 * @param {string} content - The paragraph content
 * @returns {Array} Array of message parts
 */
const splitSingleParagraph = (content) => {
	// Try to split by sentence endings
	const sentences = content
		.split(/(?<=[.!?—–])\s+/)
		.filter(s => s.trim())
		.map(s => s.trim());
	
	// If we have more than 3 sentences, group them
	if (sentences.length > 3) {
		return groupSentences(sentences);
	}
	
	// If we have 2-3 sentences, keep as one bubble
	if (sentences.length > 1) {
		return [{
			type: "default",
			content: content,
			icon: "BOT"
		}];
	}
	
	// Single sentence or short message
	return [{
		type: "default",
		content: content,
		icon: "BOT"
	}];
};

/**
 * Groups sentences into chunks of 3
 * @param {Array} sentences - Array of sentences
 * @returns {Array} Array of grouped message parts
 */
const groupSentences = (sentences) => {
	const groups = [];
	let currentGroup = "";
	let sentenceCount = 0;
	
	sentences.forEach((sentence, index) => {
		currentGroup += sentence + " ";
		sentenceCount++;
		
		// Create a new group every 3 sentences or at the end
		if (sentenceCount === 3 || index === sentences.length - 1) {
			groups.push({
				type: "paragraph",
				content: currentGroup.trim(),
				icon: "BOT"
			});
			currentGroup = "";
			sentenceCount = 0;
		}
	});
	
	return groups;
};

/**
 * Force splits long content into chunks when sentence splitting fails
 * @param {string} content - The content to split
 * @param {number} maxChunks - Maximum number of chunks (default: 3)
 * @returns {Array} Array of message parts
 */
export const forceSplitLongContent = (content, maxChunks = 3) => {
	if (!content || content.length <= 200) {
		return null; // No need to force split
	}
	
	const words = content.split(' ');
	const wordsPerChunk = Math.ceil(words.length / maxChunks);
	const chunks = [];
	
	for (let i = 0; i < words.length; i += wordsPerChunk) {
		const chunk = words.slice(i, i + wordsPerChunk).join(' ');
		if (chunk.trim()) {
			chunks.push({
				type: "paragraph",
				content: chunk.trim(),
				icon: "BOT"
			});
		}
	}
	
	return chunks.length > 1 ? chunks : null;
};
