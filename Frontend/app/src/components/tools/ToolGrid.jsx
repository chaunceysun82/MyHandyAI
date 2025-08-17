import React from "react";
import ToolCard from "./ToolCard";

export default function ToolsGrid({ tools }) {
	return (
		<div className="grid grid-cols-2 gap-3 place-items-stretch">
			{tools.map((tool, idx) => (
				<ToolCard key={idx} tool={tool} />
			))}
		</div>
	);
}
