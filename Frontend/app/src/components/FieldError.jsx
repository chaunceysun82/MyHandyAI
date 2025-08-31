import React from "react";

const FieldError = ({ error, children, className = "" }) => {
	if (!error) return children;

	return (
		<div className={className}>
			{children}
			{error && (
				<div className="flex mb-5 mt-3 items-center gap-1 text-red-600 text-sm">
					<svg className="w-4 h-4 text-red-600" fill="currentColor" viewBox="0 0 20 20">
						<path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
					</svg>
					<span>{error}</span>
				</div>
			)}
		</div>
	);
};

export default FieldError;
