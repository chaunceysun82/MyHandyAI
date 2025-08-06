const PrimaryButton = ({ label, onClick, disabled, className }) => {
	return (
		<div>
			<button
				className={`w-full text-white rounded-md bg-green-600 py-3 text-sm font-medium disabled:opacity-50 ${className}`}
				onClick={onClick}
				disabled={disabled}>
				{label}
			</button>
		</div>
	);
};

export default PrimaryButton;
