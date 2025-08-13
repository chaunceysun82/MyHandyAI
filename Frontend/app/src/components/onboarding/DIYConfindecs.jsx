import React from "react";

const emojiMap = {
	"Not confident at all": "😕",
	"Slightly confident": "🤔",
	"Somewhat confident": "🙂",
	Confident: "😊",
	"Very confident": "😎",
};

export default function DIYConfidenceSelector({
	title,
	description,
	selected,
	onClick,
}) {
	const isSelected = selected === title;

	return (
		<div
			onClick={() => onClick(title)}
			className={`cursor-pointer border rounded-xl px-4 py-2 flex items-center justify-between ${
				isSelected ? "bg-gray-200" : "hover:bg-gray-50"
			}`}>
			<div className="flex items-center gap-2">
				<span className="text-3xl">{emojiMap[title]}</span>
				<div>
					<h4 className="font-semibold">{title}</h4>
					<p className="text-sm text-gray-500">{description}</p>
				</div>
			</div>
		</div>
	);
}
