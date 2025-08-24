export default function MessageBubble({ role = "bot", children, images = [], isImageOnly = false }) {
	// If this is an image-only message, render just the image without bubble background
	if (isImageOnly && images && images.length > 0) {
		return (
			<div className="mt-3 flex justify-end">
				<div className="max-w-[78%] flex flex-col items-end">
					{images.map((image, index) => (
						<div key={index} className="mb-2">
							<img 
								src={image} 
								alt={`Uploaded image ${index + 1}`}
								className="max-w-full max-h-48 rounded-lg object-contain shadow-sm hover:shadow-md transition-shadow cursor-pointer"
								onError={(e) => {
									e.target.style.display = 'none';
								}}
								onClick={() => {
									// Optional: Open image in full size
									window.open(image, '_blank');
								}}
							/>
						</div>
					))}
				</div>
			</div>
		);
	}

	if (role === "bot") {
		return (
			<div className="mt-4 flex items-start gap-2">
				<div className="h-7 w-7 rounded-full bg-gray-200 flex items-center justify-center shrink-0">
					<span className="text-xs">🤖</span>
				</div>
				<div className="max-w-[78%] text-[15px] rounded-xl bg-gray-200 px-3.5 py-2.5 leading-snug text-gray-800">
					{children}
					{/* Display images if any (for bot messages with images) */}
					{images && images.length > 0 && (
						<div className="mt-3 space-y-2">
							{images.map((image, index) => (
								<div key={index} className="flex justify-center">
									<img 
										src={image} 
										alt={`Image ${index + 1}`}
										className="max-w-full max-h-48 rounded-lg object-contain border border-gray-300 shadow-sm hover:shadow-md transition-shadow cursor-pointer"
										onError={(e) => {
											e.target.style.display = 'none';
										}}
										onClick={() => {
											// Optional: Open image in full size
											window.open(image, '_blank');
										}}
									/>
								</div>
							))}
						</div>
					)}
				</div>
			</div>
		);
	}
	
	// Regular user message with text (no images)
	return (
		<div className="mt-3 flex justify-end">
			<div className="max-w-[78%] rounded-xl bg-[#2F87FF] text-white px-3.5 py-2.5 text-[15px] leading-snug whitespace-pre-wrap">
				{children}
			</div>
		</div>
	);
}
