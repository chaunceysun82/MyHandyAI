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
