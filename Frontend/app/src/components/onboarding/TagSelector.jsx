import React, { useState, useEffect } from "react";

// Utility function to generate consistent storage keys
const generateStorageKey = (questionId) => `onboarding_custom_${questionId}`;

const TagSelector = ({
	title,
	items, // Original options from parent
	selectedItems,
	onToggle,
	onAddCustomItem,
	onClearAll,
	showAddButton = true,
	showClearButton = false,
	questionId, // Unique identifier for this question
}) => {
	const [inputVisible, setInputVisible] = useState(false);
	const [inputValue, setInputValue] = useState("");
	const [localCustomItems, setLocalCustomItems] = useState([]);

	// Generate a unique storage key for this question
	const storageKey = generateStorageKey(questionId);

	// Load custom items from localStorage when component mounts or questionId changes
	useEffect(() => {
		if (questionId) {
			console.log(`TagSelector: Loading custom items for question ${questionId}`);
			const savedCustomItems = localStorage.getItem(storageKey);
			if (savedCustomItems) {
				try {
					const parsed = JSON.parse(savedCustomItems);
					const validItems = Array.isArray(parsed) ? parsed : [];
					setLocalCustomItems(validItems);
					console.log(`TagSelector: Loaded ${validItems.length} custom items for question ${questionId}:`, validItems);
				} catch (error) {
					console.error('Error parsing saved custom items:', error);
					setLocalCustomItems([]);
				}
			} else {
				setLocalCustomItems([]);
				console.log(`TagSelector: No saved custom items found for question ${questionId}`);
			}
		}
	}, [questionId, storageKey]);

	// Save custom items to localStorage whenever they change
	useEffect(() => {
		if (questionId && localCustomItems.length > 0) {
			localStorage.setItem(storageKey, JSON.stringify(localCustomItems));
			console.log(`TagSelector: Saved ${localCustomItems.length} custom items for question ${questionId}:`, localCustomItems);
		} else if (questionId && localCustomItems.length === 0) {
			localStorage.removeItem(storageKey);
			console.log(`TagSelector: Removed storage for question ${questionId}`);
		}
	}, [localCustomItems, questionId, storageKey]);

	// Combine original items with local custom items
	const allItems = [...items, ...localCustomItems];

	const handleAdd = () => {
		const trimmed = inputValue.trim();
		if (
			trimmed &&
			!allItems.includes(trimmed) &&
			!selectedItems.includes(trimmed)
		) {
			console.log(`TagSelector: Adding custom item "${trimmed}" to question ${questionId}`);
			
			// Add to local custom items
			const newCustomItems = [...localCustomItems, trimmed];
			setLocalCustomItems(newCustomItems);
			
			// Save to localStorage immediately
			localStorage.setItem(storageKey, JSON.stringify(newCustomItems));
			
			// Notify parent component
			onAddCustomItem(trimmed);
		}
		setInputValue("");
		setInputVisible(false);
	};

	return (
		<div className="max-w-md mx-auto space-y-4 mt-10">
			{title && <h2 className="text-lg font-semibold text-center">{title}</h2>}

			{/* Scrollable checkbox grid section */}
			<div className="max-h-64 overflow-y-auto">
				<div className="flex flex-wrap gap-3">
					{allItems.map((item) => {
						const isSelected = selectedItems.includes(item);
						return (
							<button
								key={item}
								onClick={() => onToggle(item)}
								className={`flex items-center px-4 py-2 rounded-xl border transition text-[10px] ${
									isSelected ? "bg-gray-200 " : "bg-white border-gray-300 "
								}`}>
								<input
									type="checkbox"
									checked={isSelected}
									onChange={() => {}}
									className="mr-2 w-4 h-4 checked:bg-black checked:border-black checked:text-white checked:content-['✓']"
								/>
								{item}
							</button>
						);
					})}
				</div>
			</div>

			{/* Fixed action buttons section - always visible */}
			<div className="space-y-3">
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
						className="w-full flex items-center justify-center gap-2 border border-gray-300 rounded-xl hover:border-gray-400 transition">
						<span className="text-lg p-1.5">+</span>
						<span>Add item not listed</span>
					</button>
				)}

				{showClearButton && (
					<button
						onClick={onClearAll}
						className="w-full border border-gray-300 rounded-xl py-2 hover:border-gray-400 transition">
						I don't have any yet
					</button>
				)}
			</div>
		</div>
	);
};

export default TagSelector;
