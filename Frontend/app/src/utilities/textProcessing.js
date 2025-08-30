

/**
 * Splits a message into logical parts for better readability
 * Prioritizes sentence boundaries and natural breaks to avoid breaking mid-sentence
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
 * Groups sentences into chunks of 4-5 for better readability
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
		
		// Create a new group every 4-5 sentences or at the end
		// This provides better readability while maintaining conversation flow
		if (sentenceCount >= 4 || index === sentences.length - 1) {
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
 * Groups content by natural breaks (commas, semicolons, colons)
 * @param {Array} breaks - Array of content parts
 * @returns {Array} Array of grouped message parts
 */
const groupNaturalBreaks = (breaks) => {
	const groups = [];
	let currentGroup = "";
	let breakCount = 0;
	
	breaks.forEach((breakPart, index) => {
		currentGroup += breakPart + " ";
		breakCount++;
		
		// Create a new group every 4-5 natural breaks or at the end
		if (breakCount >= 4 || index === breaks.length - 1) {
			groups.push({
				type: "paragraph",
				content: currentGroup.trim(),
				icon: "BOT"
			});
			currentGroup = "";
			breakCount = 0;
		}
	});
	
	return groups;
};

/**
 * Splits content by words but tries to find good break points
 * @param {string} content - The content to split
 * @param {number} maxChunks - Maximum number of chunks
 * @returns {Array} Array of message parts
 */
const splitByWordsWithBreaks = (content, maxChunks) => {
	const words = content.split(' ');
	const wordsPerChunk = Math.ceil(words.length / maxChunks);
	const chunks = [];
	
	for (let i = 0; i < words.length; i += wordsPerChunk) {
		// Try to find a good break point near the target chunk size
		let chunkEnd = Math.min(i + wordsPerChunk, words.length);
		
		// If we're not at the end, try to find a better break point
		if (chunkEnd < words.length) {
			// Look for a period, comma, or other punctuation within 3 words of target
			for (let j = chunkEnd; j < Math.min(chunkEnd + 3, words.length); j++) {
				if (words[j] && /[.!?,;:]$/.test(words[j])) {
					chunkEnd = j + 1;
					break;
				}
			}
		}
		
		const chunk = words.slice(i, chunkEnd).join(' ');
		if (chunk.trim()) {
			chunks.push({
				type: "paragraph",
				content: chunk.trim(),
				icon: "BOT"
			});
		}
		
		// Update i to skip the words we just processed
		i = chunkEnd - 1;
	}
	
	return chunks.length > 1 ? chunks : null;
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
	
	// First try to split by sentence boundaries
	const sentences = content
		.split(/(?<=[.!?—–])\s+/)
		.filter(s => s.trim())
		.map(s => s.trim());
	
	if (sentences.length > 1) {
		// Group sentences into chunks, ensuring we don't break mid-sentence
		return groupSentences(sentences);
	}
	
	// If no sentence boundaries found, try to split by natural breaks
	// Look for common break points like commas, semicolons, or colons
	const naturalBreaks = content
		.split(/(?<=[,;:])\s+/)
		.filter(s => s.trim())
		.map(s => s.trim());
	
	if (naturalBreaks.length > 1) {
		// Group by natural breaks
		return groupNaturalBreaks(naturalBreaks);
	}
	
	// Last resort: split by words but try to find good break points
	return splitByWordsWithBreaks(content, maxChunks);
};
