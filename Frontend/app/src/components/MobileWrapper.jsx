import React from "react";

const MobileWrapper = ({ children }) => {
	return (
		<div
			data-app-shell
			className="min-h-screen flex justify-center items-stretch bg-[#dfeff3] lg:items-start lg:bg-[radial-gradient(circle_at_top,#eef8fb_0%,#dfeff3_48%,#d4e6ec_100%)] lg:p-6"
		>
			<div
				data-app-shell-frame
				className="min-h-screen w-full bg-white overflow-y-auto lg:min-h-[calc(100vh-3rem)] lg:max-w-7xl lg:rounded-[32px] lg:shadow-[0_24px_80px_rgba(15,53,66,0.16)]"
			>
				{children}
			</div>
		</div>
	);
};

export default MobileWrapper;
