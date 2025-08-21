import React from "react";
import amzzonLogo from "../../assets/amazon.png";

export default function AmazonButton({ link }) {
	return (
		<a
			href={link}
			target="_blank"
			rel="noreferrer"
			className="mt-2 flex items-center gap-1 bg-blue-100 text-blue-700 px-2 py-1 rounded-full text-xs font-medium">
			<img src="" alt="Amazon" className="h-4 w-4" />
			Amazon
		</a>
	);
}
