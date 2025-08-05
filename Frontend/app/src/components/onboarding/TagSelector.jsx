import React, { useState } from "react";

const TagSelector = ({
	title,
	items,
	selectedItems,
	onToggle,
	onAddCustomItem,
	onClearAll,
	showAddButton = true,
	showClearButton = false,
}) => {
	const [inputVisible, setInputVisible] = useState(false);
	const [inputValue, setInputValue] = useState("");

	const handleAdd = () => {
		const trimmed = inputValue.trim();
		if (
			trimmed &&
			!items.includes(trimmed) &&
			!selectedItems.includes(trimmed)
		) {
			onAddCustomItem(trimmed);
		}
		setInputValue("");
		setInputVisible(false);
	};

	return (
		<div className="max-w-md mx-auto space-y-4 mt-10">
			{title && <h2 className="text-lg font-semibold text-center">{title}</h2>}

			<div className="flex flex-wrap gap-3">
				{items.map((item) => {
					const isSelected = selectedItems.includes(item);
					return (
						<button
							key={item}
							onClick={() => onToggle(item)}
							className={`flex items-center px-4 py-2 rounded-xl border transition text-sm ${
								isSelected ? "bg-gray-200 " : "bg-white border-gray-300 "
							}`}>
							<input
								type="checkbox"
								checked={isSelected}
								onChange={() => {}}
								className="mr-2 w-4 h-4"
							/>
							{item}
						</button>
					);
				})}
			</div>

			{inputVisible && (
				<div className="flex gap-2">
					<input
						type="text"
						className="flex-1 px-4 py-2 border border-gray-300 rounded-xl"
						placeholder="Enter custom item"
						value={inputValue}
						onChange={(e) => setInputValue(e.target.value)}
					/>
					<button
						onClick={handleAdd}
						className="bg-gray-600 text-white px-4 py-2 rounded-xl">
						Add
					</button>
				</div>
			)}

			{showAddButton && !inputVisible && (
				<button
					onClick={() => setInputVisible(true)}
					className="w-full flex items-center justify-center gap-2 border border-gray-300 rounded-xl  hover:border-gray-400 transition">
					<span className="text-lg p-2">+</span>
					<span>Add item not listed</span>
				</button>
			)}

			{showClearButton && (
				<button
					onClick={onClearAll}
					className="w-full border border-gray-300 rounded-xl py-3 hover:border-gray-400 transition">
					I don’t have any yet
				</button>
			)}
		</div>
	);
};

export default TagSelector;
