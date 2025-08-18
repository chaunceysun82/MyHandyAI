export function truncateWords(text, count = 7) {
	if (!text) return "";
	const words = String(text).trim().split(/\s+/);
	if (words.length <= count) return text;
	return words.slice(0, count).join(" ") + "…";
}

export function truncateUntilWord(text, word) {
	const regex = new RegExp(`\\b${word}\\b`, "i"); // case-insensitive, full word match
	const match = text.match(regex);

	if (!match) return text;

	return text.slice(0, match.index + match[0].length);
}

export function truncateUntilChar(text, char) {
	if (!text) return "";
	const index = String(text).indexOf(char);
	
	if (index === -1) return text; // Character not found, return full text
	
	return text.slice(0, index);
}

export function truncateUntilChars(text, chars) {
	if (!text) return "";
	
	// Convert chars to array if it's a string
	const charArray = Array.isArray(chars) ? chars : [chars];
	
	// Find the earliest occurrence of any of the characters
	let earliestIndex = -1;
	
	for (const char of charArray) {
		const index = String(text).indexOf(char);
		if (index !== -1 && (earliestIndex === -1 || index < earliestIndex)) {
			earliestIndex = index;
		}
	}
	
	if (earliestIndex === -1) return text; // No characters found, return full text
	
	return text.slice(0, earliestIndex);
}
