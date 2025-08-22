import React from "react";

export default function StepVideoGuide({ videoUrl, title = "Video Guide" }) {
	// Debug logging
	console.log("StepVideoGuide: Received props:", { videoUrl, title });
	
	// If no video URL, show placeholder
	if (!videoUrl) {
		console.log("StepVideoGuide: No video URL provided, showing placeholder");
		return (
			<div className="border-2 border-dashed border-gray-300 rounded-lg text-center p-4 mx-auto">
				<div className="w-8 h-8 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-2">
					<svg className="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.828 14.828a4 4 0 01-5.656 0M9 10h1m4 0h1m-6 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
					</svg>
				</div>
				<p className="text-xs text-gray-600 mb-1">{title}</p>
				<p className="text-[10px] text-gray-500">Video guide will appear here</p>
			</div>
		);
	}

	console.log("StepVideoGuide: Video URL found:", videoUrl);

	// Convert YouTube URL to embed format
	const getEmbedUrl = (url) => {
		if (!url) return null;
		
		console.log("StepVideoGuide: Processing URL:", url);
		
		// Handle different YouTube URL formats
		let videoId = null;
		
		// Regular YouTube watch URLs: https://www.youtube.com/watch?v=VIDEO_ID
		if (url.includes('youtube.com/watch?v=')) {
			videoId = url.split('v=')[1]?.split('&')[0];
			console.log("StepVideoGuide: Extracted video ID from watch URL:", videoId);
		}
		// Short YouTube URLs: https://youtu.be/VIDEO_ID
		else if (url.includes('youtu.be/')) {
			videoId = url.split('youtu.be/')[1]?.split('?')[0];
			console.log("StepVideoGuide: Extracted video ID from short URL:", videoId);
		}
		// YouTube embed URLs: https://www.youtube.com/embed/VIDEO_ID
		else if (url.includes('youtube.com/embed/')) {
			videoId = url.split('embed/')[1]?.split('?')[0];
			console.log("StepVideoGuide: Extracted video ID from embed URL:", videoId);
		}
		
		if (videoId) {
			const embedUrl = `https://www.youtube.com/embed/${videoId}`;
			console.log("StepVideoGuide: Generated embed URL:", embedUrl);
			return embedUrl;
		}
		
		console.log("StepVideoGuide: Could not extract video ID, returning original URL");
		return url; // Return original URL if we can't parse it
	};

	const embedUrl = getEmbedUrl(videoUrl);
	console.log("StepVideoGuide: Final embed URL:", embedUrl);

	return (
		<div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
			<div className="p-3 border-b border-gray-100">
				<h3 className="text-sm font-semibold text-gray-900">{title}</h3>
			</div>
			<div className="aspect-video w-full">
				{embedUrl ? (
					<iframe
						src={embedUrl}
						title={title}
						className="w-full h-full"
						frameBorder="0"
						allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
						allowFullScreen
					/>
				) : (
					<div className="w-full h-full bg-gray-100 flex items-center justify-center">
						<p className="text-sm text-gray-500">Invalid video URL</p>
					</div>
				)}
			</div>
		</div>
	);
}
