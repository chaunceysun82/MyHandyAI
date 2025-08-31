import React from "react";
import ToolCard from "./ToolCard";

export default function ToolsGrid({ tools, selectedTools, onToolSelection, isSelectionMode }) {
	return (
		<div className="grid grid-cols-2 gap-3 place-items-stretch">
			{tools.map((tool, idx) => {
				// Use a more reliable identifier - try multiple fields
				const toolId = tool._id || tool.id || tool.tool_id || `tool-${idx}`;
				const isSelected = selectedTools.has(toolId);
				
				console.log("ToolGrid rendering tool:", {
					name: tool.name,
					toolId,
					isSelected,
					isSelectionMode,
					selectedTools: Array.from(selectedTools),
					idx
				});
				
				return (
					<ToolCard 
						key={`tool-${idx}`} // Use index-based key for React
						tool={tool} 
						toolId={toolId}
						isSelected={isSelected}
						isSelectionMode={isSelectionMode}
						onSelectionToggle={() => onToolSelection(toolId)}
					/>
				);
			})}
		</div>
	);
}
