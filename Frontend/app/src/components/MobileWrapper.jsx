import React from "react";

const MobileWrapper = ({ children }) => {
	return (
		<div className="min-h-screen bg-gray-200 flex justify-center items-start">
			<div className="w-full mt-8 mb-12 max-w-sm bg-white shadow-md overflow-y-auto">
				{children}
			</div>
		</div>
	);
};

export default MobileWrapper;
