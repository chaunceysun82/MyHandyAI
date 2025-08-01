import React from "react";

const MobileWrapper = ({ children }) => {
	return (
		<div className="min-h-screen bg-gray-200 flex justify-center items-start">
			<div className="w-full max-w-sm min-h-screen bg-white shadow-md overflow-y-auto">
				{children}
			</div>
		</div>
	);
};

export default MobileWrapper;
