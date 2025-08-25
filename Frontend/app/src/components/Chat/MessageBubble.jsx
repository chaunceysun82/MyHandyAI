import React from "react";
import { splitMessageIntoParts, forceSplitLongContent } from "../../utilities/textProcessing";

// Function to format content with proper line breaks and lists
const formatContent = (content) => {
	if (!content) return content;
	
	// Add line breaks after question marks for better readability
	let processedContent = content.replace(/\?/g, '?\n');
	
	// Split content into lines and format each line
	const lines = processedContent.split('\n').filter(line => line.trim());
	
	return lines.map((line, index) => {
		const trimmedLine = line.trim();
		
		// Handle numbered lists
		if (trimmedLine.match(/^\d+\./)) {
			return (
				<div key={index} className="ml-2 mb-2 flex items-start">
					<span className="text-gray-600 font-medium mr-2 flex-shrink-0">
						{trimmedLine.match(/^\d+\./)[0]}
					</span>
					<span className="text-gray-700">
						{renderFormattedText(trimmedLine.replace(/^\d+\.\s*/, ''))}
					</span>
				</div>
			);
		}
		
		// Handle bullet points
		if (trimmedLine.startsWith('•')) {
			return (
				<div key={index} className="ml-2 mb-2 flex items-start">
					<span className="text-gray-600 mr-2 flex-shrink-0">•</span>
					<span className="text-gray-700">
						{renderFormattedText(trimmedLine.substring(1).trim())}
					</span>
				</div>
			);
		}
		
		// Handle regular lines
		return (
			<div key={index} className="mb-2 text-gray-700">
				{renderFormattedText(trimmedLine)}
			</div>
		);
	});
};

// Function to render formatted text (bold, italic, etc.)
const renderFormattedText = (text) => {
	if (!text) return text;
	
	// Handle bold text: **text**
	text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
	
	// Handle italic text: *text*
	text = text.replace(/\*(.*?)\*/g, '<em>$1</em>');
	
	// Handle strikethrough: ~~text~~
	text = text.replace(/~~(.*?)~~/g, '<del>$1</del>');
	
	// Handle inline code: `code`
	text = text.replace(/`(.*?)`/g, '<code class="bg-gray-100 px-1 py-0.5 rounded text-sm">$1</code>');
	
	// Handle links: [text](url)
	text = text.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" class="text-blue-600 hover:underline" target="_blank" rel="noopener noreferrer">$1</a>');
	
	return <span dangerouslySetInnerHTML={{ __html: text }} />;
};

// Component for individual message parts
const MessagePart = ({ type, content, icon, isFirst = false, showIcon = false }) => {
	const getBubbleStyle = () => {
		switch (type) {
			case "step-header":
				return "bg-blue-100 border border-blue-200";
			case "time":
				return "bg-blue-50 border border-blue-200";
			case "tools":
				return "bg-green-50 border border-green-200";
			case "warning":
				return "bg-red-50 border border-red-200";
			case "instructions":
				return "bg-purple-50 border border-purple-200";
			case "tip":
				return "bg-yellow-50 border border-yellow-200";
			case "paragraph":
				return "bg-gray-200 border border-gray-200";
			default:
				return "bg-gray-200 border border-gray-200";
		}
	};

	return (
		<div className={`flex items-start gap-2 ${isFirst ? 'mt-4' : 'mt-3'}`}>
			{showIcon ? (
				<div className="h-7 w-7 rounded-full bg-gray-200 flex items-center justify-center shrink-0">
					<span className="text-xs">🤖</span>
				</div>
			) : (
				<div className="h-7 w-7 shrink-0"></div>
			)}
			<div className={`max-w-[78%] text-[15px] rounded-xl px-3.5 py-2.5 leading-snug text-gray-800 ${getBubbleStyle()}`}>
				{formatContent(content)}
			</div>
		</div>
	);
};

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
		const parts = splitMessageIntoParts(children);
		
		// Force split if content is very long and still not split
		if (parts.length === 1 && children && children.length > 200) {
			const forcedParts = forceSplitLongContent(children);
			if (forcedParts) {
				return (
					<div className="space-y-2">
						{forcedParts.map((part, index) => (
							<MessagePart 
								key={index} 
								type={part.type} 
								content={part.content} 
								icon={part.icon} 
								isFirst={index === 0}
								showIcon={index === 0}
							/>
						))}
					</div>
				);
			}
		}
		
		return (
			<div className="space-y-2">
				{parts.map((part, index) => (
					<MessagePart 
						key={index} 
						type={part.type} 
						content={part.content} 
						icon={part.icon} 
						isFirst={index === 0}
						showIcon={index === 0}
					/>
				))}
				
				{/* Display images if any (for bot messages with images) */}
				{images && images.length > 0 && (
					<div className="mt-4 space-y-2">
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
										window.open(image, '_blank');
									}}
								/>
							</div>
						))}
					</div>
				)}
			</div>
		);
	}

	// User message
	return (
		<div className="mt-3 flex justify-end">
			<div className="max-w-[78%] bg-blue-500 text-white text-[15px] rounded-xl px-3.5 py-2.5 leading-snug">
				{children}
			</div>
		</div>
	);
}
