const SingleSelectorCard = ({
	title,
	description,
	value,
	selected,
	onClick,
}) => {
	const isSelected = selected === value;

	return (
		<div
			onClick={() => onClick(value)}
			className={`w-full border rounded-xl px-6 py-2 cursor-pointer transition-all duration-200 ${
				isSelected ? " bg-gray-200" : "border-gray-300 hover:border-gray-400"
			} mb-4`}>
			<div className="text-center">
				<div className="text-lg font-bold text-gray-900">{title}</div>
				{description && (
					<div className="text-sm text-gray-500 mt-1">{description}</div>
				)}
			</div>
		</div>
	);
};

export default SingleSelectorCard;
