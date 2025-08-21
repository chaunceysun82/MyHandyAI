// components/ToolCard.jsx
import { useMemo, useState } from "react";
import amazon from "../../assets/amazon.svg";
import defaultToolImage from "../../assets/default_tool.png";
import { truncateWords } from "../../utilities/text"; 

export default function ToolCard({ tool }) {
	const [showDetails, setShowDetails] = useState(false);
	const [showModal, setShowModal] = useState(false);
	
	// Handle both transformed and raw API data structures
	const toolName = tool?.name || "Unknown Tool";
	const toolDescription = tool?.description || "No description available";
	const toolPrice = tool?.price || tool?.priceMin || 0;
	const toolImage = tool?.image || tool?.image_link || "";
	const toolLink = tool?.link || tool?.amazon_link || "https://www.amazon.com";
	const toolRiskFactors = tool?.riskFactors || tool?.risk_factors || "";
	const toolSafetyMeasures = tool?.safetyMeasures || tool?.safety_measures || "";
	const toolRequired = tool?.required !== undefined ? tool.required : true;
	
	const defaultSrc = defaultToolImage;

	const initialSrc = useMemo(() => {
		if (/^https?:\/\//.test(toolImage) || toolImage.startsWith("/"))
			return toolImage;
		return toolImage ? `/${toolImage}` : defaultSrc;
	}, [toolImage]);

	const [src, setSrc] = useState(initialSrc);

	const rating = Number(tool?.rating ?? 4.0);
	const fullStars = Math.max(0, Math.min(5, Math.floor(rating)));
	const emptyStars = 5 - fullStars;

	const priceText = toolPrice 
		? `$${toolPrice.toFixed(2)}`
		: tool?.priceMin != null && tool?.priceMax != null
		? `$${tool.priceMin} \u2013 $${tool.priceMax}`
		: tool?.priceRange || "Price not available";

	// Cut description to half length for display
	const shortDescription = toolDescription 
		? toolDescription.length > 50 
			? toolDescription.substring(0, 30) + "..."
			: toolDescription
		: "No description available";

	const hasAdditionalInfo = toolRiskFactors || toolSafetyMeasures;

	const handleShowDetails = () => {
		setShowModal(true);
	};

	const handleCloseModal = () => {
		setShowModal(false);
	};

	return (
		<>
			<div className="w-full flex flex-col items-center h-full">
				{/* Card */}
				<div className="w-full h-full rounded-xl border border-gray-200 bg-gray-50 shadow-sm p-3 flex flex-col items-center justify-between min-h-[140px]">
					{/* Image tile */}
					<div className="h-12 w-12 rounded-lg bg-white shadow-inner flex items-center justify-center overflow-hidden">
						<img
							src={src}
							alt={toolName}
							className="h-10 w-10 object-contain"
							referrerPolicy="no-referrer"
							onError={() => {
								if (src !== defaultSrc) setSrc(defaultSrc);
							}}
						/>
					</div>

					{/* Title */}
					<h3 className="mt-2 text-sm font-semibold text-gray-900 text-center line-clamp-2 leading-tight min-h-[2.5rem] flex items-center justify-center">
						{truncateWords(toolName, 4)}
					</h3>

					{/* Description */}
					{/* <p className="mt-2 text-sm text-gray-600 text-center line-clamp-3">
						{shortDescription}
					</p> */}

					{/* Price */}
					<div className="mt-1 text-emerald-600 text-sm font-semibold tracking-tight">
						{priceText}
					</div>

					{/* Rating row */}
					

					{/* Amazon button */}
					<a
						href={toolLink}
						target="_blank"
						rel="noreferrer"
						className="mt-2 inline-flex items-center gap-1 rounded-lg bg-blue-100 text-blue-800 px-2 py-1 text-xs font-medium hover:bg-blue-200 transition-colors">
						<img src={amazon} alt="Amazon" className="h-3 w-3" />
						<span>Amazon</span>
						<svg
							className="h-3 w-3"
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							strokeWidth="2"
							aria-hidden="true">
							<path d="M18 13v6a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
							<path d="M15 3h6v6" />
							<path d="M10 14L21 3" />
						</svg>
					</a>

					{/* Show Details Toggle */}
					{hasAdditionalInfo && (
						<button
							onClick={handleShowDetails}
							className="mt-2 text-xs text-blue-600 hover:text-blue-800 underline"
						>
							Show Details
						</button>
					)}
				</div>

				{/* Bottom pill */}
				<div className="mt-2 mb-1">
					<span
						className={`inline-flex items-center justify-center rounded-full px-2 py-0.5 text-xs italic shadow-sm ${
							toolRequired
								? "bg-orange-100 text-orange-700"
								: "bg-green-100 text-emerald-700"
						}`}>
						{toolRequired ? "Required" : "Optional"}
					</span>
				</div>
			</div>

			{/* Modal Overlay */}
			{showModal && (
				<div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-2">
					<div className="bg-white rounded-lg max-w-xs w-full max-h-[80vh] overflow-y-auto">
						{/* Header */}
						<div className="sticky top-0 bg-white border-b border-gray-200 px-3 py-2 rounded-t-lg">
							<div className="flex items-center justify-between">
								<h2 className="text-sm font-bold text-gray-900">Tool Details</h2>
								<button
									onClick={handleCloseModal}
									className="text-gray-400 hover:text-gray-600 text-lg font-bold"
								>
									×
								</button>
							</div>
						</div>

						{/* Content */}
						<div className="p-3 space-y-3">
							{/* Tool Image and Basic Info */}
							<div className="flex items-center space-x-2">
								<div className="h-12 w-12 rounded-md bg-gray-100 flex items-center justify-center overflow-hidden">
									<img
										src={src}
										alt={toolName}
										className="h-10 w-10 object-contain"
										referrerPolicy="no-referrer"
										onError={() => {
											if (src !== defaultSrc) setSrc(defaultSrc);
										}}
									/>
								</div>
								<div className="flex-1">
									<h3 className="text-sm font-semibold text-gray-900">{toolName}</h3>
									<div className="text-lg font-bold text-emerald-600">{priceText}</div>
									<span
										className={`inline-flex items-center px-1.5 py-0.5 rounded-full text-xs font-medium ${
											toolRequired
												? "bg-orange-100 text-orange-700"
												: "bg-green-100 text-emerald-700"
										}`}>
										{toolRequired ? "Required" : "Optional"}
									</span>
								</div>
							</div>

							{/* Full Description */}
							<div>
								<h4 className="text-xs font-semibold text-gray-700 mb-1">Description</h4>
								<p className="text-xs text-gray-600 leading-relaxed">{toolDescription}</p>
							</div>

							{/* Risk Factors */}
							{toolRiskFactors && (
								<div>
									<h4 className="text-xs font-semibold text-red-700 mb-1">⚠️ Risk Factors</h4>
									<p className="text-xs text-gray-700 leading-relaxed">{toolRiskFactors}</p>
								</div>
							)}

							{/* Safety Measures */}
							{toolSafetyMeasures && (
								<div>
									<h4 className="text-xs font-semibold text-green-700 mb-1">🛡️ Safety Measures</h4>
									<p className="text-xs text-gray-700 leading-relaxed">{toolSafetyMeasures}</p>
								</div>
							)}

							{/* Amazon Link */}
							<div className="pt-1">
								<a
									href={toolLink}
									target="_blank"
									rel="noreferrer"
									className="w-full inline-flex items-center justify-center gap-1 rounded-md bg-blue-600 text-white px-2 py-1.5 text-xs font-medium hover:bg-blue-700 transition-colors">
									<img src={amazon} alt="Amazon" className="h-3 w-3" />
									<span>View on Amazon</span>
									<svg
										className="h-3 w-3"
										viewBox="0 0 24 24"
										fill="none"
										stroke="currentColor"
										strokeWidth="2"
										aria-hidden="true">
										<path d="M18 13v6a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
										<path d="M15 3h6v6" />
										<path d="M10 14L21 3" />
									</svg>
								</a>
							</div>
						</div>
					</div>
				</div>
			)}
		</>
	);
}
