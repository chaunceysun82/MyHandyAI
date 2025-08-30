import React, { useState, useEffect } from "react";

export default function StepMediaGuide({ videoUrl, imageData, title = "Step Guide" }) {
	const [currentIndex, setCurrentIndex] = useState(0);
	const [mediaItems, setMediaItems] = useState([]);
	const [showImageModal, setShowImageModal] = useState(false);

	// Set up media items array
	useEffect(() => {
		const items = [];
		
		// Handle multiple images or single image FIRST
		if (imageData) {
			if (Array.isArray(imageData)) {
				// Multiple images - add each complete image
				imageData.forEach((img, index) => {
					if (img && img.status === 'complete' && img.url) {
						items.push({ type: 'image', url: img.url, index, originalData: img });
					}
				});
			} else if (imageData.status === 'complete' && imageData.url) {
				// Single image
				items.push({ type: 'image', url: imageData.url, index: 0, originalData: imageData });
			}
		}
		
		// Add video SECOND (after images)
		if (videoUrl) {
			items.push({ type: 'video', url: videoUrl });
		}
		
		setMediaItems(items);
	}, [videoUrl, imageData]);

	// Check if image is loading (status is not complete)
	const isImageLoading = imageData && (
		Array.isArray(imageData) 
			? imageData.some(img => img && img.status !== 'complete')
			: imageData.status !== 'complete'
	);

	// If no media items, show placeholder or loading state
	if (mediaItems.length === 0) {
		if (isImageLoading) {
			return (
				<div className="border-2 border-dashed border-gray-300 rounded-lg text-center p-4 mx-auto">
					<div className="w-8 h-8 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-2">
						<div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
					</div>
					<p className="text-xs text-gray-600 mb-1">{title}</p>
					<p className="text-[10px] text-gray-500">Generating step images...</p>
				</div>
			);
		}
		
		return (
			<div className="border-2 border-dashed border-gray-300 rounded-lg text-center p-4 mx-auto">
				<div className="w-8 h-8 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-2">
					<svg className="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.828 14.828a4 4 0 01-5.656 0M9 10h1m4 0h1m-6 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
					</svg>
				</div>
				<p className="text-xs text-gray-600 mb-1">{title}</p>
				<p className="text-[10px] text-gray-500">No media available</p>
			</div>
		);
	}

	// Navigation functions
	const goToPrevious = () => {
		setCurrentIndex((prev) => (prev === 0 ? mediaItems.length - 1 : prev - 1));
		setShowImageModal(false); // Close modal when navigating
	};

	const goToNext = () => {
		setCurrentIndex((prev) => (prev === mediaItems.length - 1 ? 0 : prev + 1));
		setShowImageModal(false); // Close modal when navigating
	};

	// Simple image modal toggle
	const toggleImageModal = () => {
		setShowImageModal(!showImageModal);
	};

	// Convert YouTube URL to embed format
	const getEmbedUrl = (url) => {
		if (!url) return null;
		
		// Handle different YouTube URL formats
		let videoId = null;
		
		// Regular YouTube watch URLs: https://www.youtube.com/watch?v=VIDEO_ID
		if (url.includes('youtube.com/watch?v=')) {
			videoId = url.split('v=')[1]?.split('&')[0];
		}
		// Short YouTube URLs: https://youtu.be/VIDEO_ID
		else if (url.includes('youtu.be/')) {
			videoId = url.split('youtu.be/')[1]?.split('?')[0];
		}
		// YouTube embed URLs: https://www.youtube.com/embed/VIDEO_ID
		else if (url.includes('youtube.com/embed/')) {
			videoId = url.split('embed/')[1]?.split('?')[0];
		}
		
		if (videoId) {
			return `https://www.youtube.com/embed/${videoId}`;
		}
		
		return url; // Return original URL if we can't parse it
	};

	const currentItem = mediaItems[currentIndex];

	return (
		<>
			<div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
				{/* Header with title and navigation */}
				<div className="p-3 border-b border-gray-100 flex items-center justify-between">
					<div className="flex items-center space-x-2">
						<h3 className="text-sm font-semibold text-gray-900">{title}</h3>
						
						{/* Show loading indicator if image is being generated */}
						{isImageLoading && (
							<div className="flex items-center space-x-1">
								<div className="animate-spin rounded-full h-3 w-3 border-b-2 border-blue-600"></div>
								<span className="text-xs text-blue-600">Generating images...</span>
							</div>
						)}
					</div>
					
					{/* Navigation buttons - only show if there are multiple items */}
					{mediaItems.length > 1 && (
						<div className="flex items-center space-x-2">
							<button
								onClick={goToPrevious}
								className="p-1.5 rounded-full bg-gray-100 hover:bg-gray-200 transition-colors"
								title="Previous"
							>
								<svg className="w-4 h-4 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
								</svg>
							</button>
							
							{/* Current position indicator */}
							<span className="text-xs text-gray-500">
								{currentIndex + 1} of {mediaItems.length}
							</span>
							
							<button
								onClick={goToNext}
								className="p-1.5 rounded-full bg-gray-100 hover:bg-gray-200 transition-colors"
								title="Next"
							>
								<svg className="w-4 h-4 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
								</svg>
							</button>
						</div>
					)}
				</div>

				{/* Media content */}
				{currentItem.type === 'video' ? (
					<div className="aspect-video w-full">
						<iframe
							src={getEmbedUrl(currentItem.url)}
							title={`${title} - Video`}
							className="w-full h-full"
							frameBorder="0"
							allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
							allowFullScreen
						/>
					</div>
				) : currentItem.type === 'image' ? (
					<div className="aspect-video w-full">
						<img
							src={currentItem.url}
							alt={`${title} - Image ${currentItem.index + 1}`}
							className="w-full h-full object-cover cursor-pointer"
							onClick={toggleImageModal}
						/>
					</div>
				) : (
					<div className="aspect-video w-full bg-gray-100 flex items-center justify-center">
						<p className="text-sm text-gray-500">Invalid media type</p>
					</div>
				)}
			</div>

			{/* Image Modal - Full Screen Overlay */}
			{showImageModal && currentItem?.type === 'image' && (
				<div 
					className="fixed inset-0 bg-black bg-opacity-90 z-50 flex items-center justify-center p-4"
					onClick={toggleImageModal}
				>
					<div className="relative max-w-full max-h-full">
						<img
							src={currentItem.url}
							alt={`${title} - Image ${currentItem.index + 1} (Enlarged)`}
							className="max-w-full max-h-full object-contain"
							onClick={(e) => e.stopPropagation()} // Prevent closing when clicking image
						/>
						
						{/* Close button */}
						<button
							onClick={toggleImageModal}
							className="absolute top-2 right-2 p-2 bg-white bg-opacity-80 rounded-full hover:bg-opacity-100 transition-all shadow-lg"
						>
							<svg className="w-6 h-6 text-gray-700" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
							</svg>
						</button>
					</div>
				</div>
			)}
		</>
	);
}
