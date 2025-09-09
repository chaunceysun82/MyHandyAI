import React from "react";

const StepValidationModal = ({ 
	isOpen, 
	onClose, 
	onConfirm, 
	title, 
	message, 
	confirmText = "Yes, Continue", 
	cancelText = "No, Go Back" 
}) => {
	if (!isOpen) return null;

	return (
		<div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
			<div className="bg-[#fffef6] rounded-lg p-4 max-w-xs w-full mx-4">
				{/* Header */}
				<div className="text-center mb-3">
					<h3 className="text-base font-semibold text-gray-900 mb-2">
						{title}
					</h3>
					<p className="text-xs text-gray-600 leading-relaxed">
						{message}
					</p>
				</div>

				{/* Buttons */}
				<div className="flex gap-2">
					<button
						onClick={onClose}
						className="flex-1 py-2 px-3 border border-gray-300 rounded-lg text-xs font-medium text-gray-700 hover:bg-gray-50 transition-colors"
					>
						{cancelText}
					</button>
					<button
						onClick={onConfirm}
						className="flex-1 py-2 px-3 bg-[#1484A3] text-white rounded-lg text-xs font-medium transition-colors"
					>
						{confirmText}
					</button>
				</div>
			</div>
		</div>
	);
};

export default StepValidationModal;
