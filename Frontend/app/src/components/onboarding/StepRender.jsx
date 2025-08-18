import React, { useState } from "react";
import SingleSelectorCard from "./SingleSelectorCard";
import TagSelector from "./TagSelector";
import LocationSelector from "./LocationSelector";
import DIYConfidenceSelector from "./DIYConfindecs";

const StepRenderer = ({ step, value, onChange }) => {
	const [customItems, setCustomItems] = useState([]);
	const [customInputVisible, setCustomInputVisible] = useState(false);
	const [customInputValue, setCustomInputValue] = useState("");

	if (!step) return null;

	const { Category, Options, Question, Comment, Type, _id } = step;

	const originalOptions = Array.isArray(Options)
		? Options.map((opt) => (typeof opt === "string" ? opt : opt.title))
		: [];

	const allOptions = [...originalOptions, ...customItems];

	const handleAddCustomItem = () => {
		const trimmed = customInputValue.trim();
		if (
			trimmed &&
			!allOptions.includes(trimmed) &&
			!customItems.includes(trimmed)
		) {
			setCustomItems([...customItems, trimmed]);
			onChange([...(value || []), trimmed]);
		}
		setCustomInputValue("");
		setCustomInputVisible(false);
	};

	const handleMultiToggle = (option) => {
		const isSelected = value?.includes(option);
		const updated = isSelected
			? value.filter((v) => v !== option)
			: [...(value || []), option];
		onChange(updated);
	};

	const handleClearAll = () => {
		onChange([]);
	};

	return (
		<div className="space-y-2">
			<h2 className="text-lg text-center font-semibold">{Question}</h2>
			{Comment && (
				<p className="text-sm text-center pb-12 text-gray-500">{Comment}</p>
			)}

			{Category === "single-selection" && Type === "DIY confidence" && (
				<div className="space-y-4">
					{Options.map((option, idx) => (
						<DIYConfidenceSelector
							key={idx}
							title={option.title}
							description={option.description}
							value={option.title}
							selected={value}
							onClick={(val) => onChange(val)}
						/>
					))}
				</div>
			)}

			{Category === "single-selection" && Type !== "DIY confidence" && (
				<div className="space-y-4">
					{Options.map((option, idx) => (
						<SingleSelectorCard
							key={idx}
							title={option.title}
							description={option.description}
							value={option.title}
							selected={value}
							onClick={(val) => onChange(val)}
						/>
					))}
				</div>
			)}

			{Category === "multiple-selection" && (
				<>
					<TagSelector
						questionId={_id || `question_${_id || 'unknown'}`}
						items={originalOptions}
						selectedItems={value || []}
						onToggle={handleMultiToggle}
						onClearAll={handleClearAll}
						onAddCustomItem={(custom) => {
							if (!customItems.includes(custom)) {
								setCustomItems([...customItems, custom]);
							}
							onChange([...(value || []), custom]);
						}}
						showClearButton={true}
					/>

					{customInputVisible && (
						<div className="flex gap-2 mt-2">
							<input
								type="text"
								value={customInputValue}
								onChange={(e) => setCustomInputValue(e.target.value)}
								placeholder="Enter tool name"
								className="flex-1 px-4 py-2 border border-gray-300"
							/>
							<button
								onClick={handleAddCustomItem}
								className="bg-black text-white px-4 py-2 rounded-xl">
								Add
							</button>
						</div>
					)}
				</>
			)}

			{Category === "combo-box" && Type === "Location" && (
				<LocationSelector
					value={value || { country: "", state: "" }}
					onChange={onChange}
				/>
			)}
		</div>
	);
};

export default StepRenderer;
