import React, { useState } from "react";
import { useNavigate, useParams, useLocation } from "react-router-dom";
import MobileWrapper from "../components/MobileWrapper";

export default function ProjectCompleted() {
	const navigate = useNavigate();
	const { projectId } = useParams();
	const { state } = useLocation();
	const projectName = state?.projectName || "Project";
	
	// Debug logging
	console.log("ProjectCompleted: Received projectId:", projectId);
	console.log("ProjectCompleted: Received state:", state);
	console.log("ProjectCompleted: Using projectName:", projectName);
	
	const [rating, setRating] = useState(0);
	const [feedback, setFeedback] = useState("");

	const handleClose = () => {
		navigate("/home");
	};

	const handleGoBack = () => {
		const targetUrl = `/projects/${projectId}/overview`;
		console.log("ProjectCompleted: handleGoBack called, navigating to:", targetUrl);
		console.log("ProjectCompleted: projectId used:", projectId);
		navigate(targetUrl);
	};

	const handleFinish = () => {
		navigate("/home");
	};

	const handleShareSuccess = () => {
		// TODO: Implement share functionality
		console.log("Share success clicked");
	};

	const handleAllProjects = () => {
		navigate("/home");
	};

	const handleDone = () => {
		console.log("Project Completed - User Review:");
		console.log("Rating:", rating, "stars");
		console.log("Feedback:", feedback);
		navigate("/home");
	};

	const handleRatingClick = (selectedRating) => {
		setRating(selectedRating);
	};

	return (
		<MobileWrapper>
			<div className="min-h-screen bg-white">
				{/* Header */}
				<div className="sticky top-0 z-10 bg-white pt-5 pb-3 px-4">
					<div className="flex items-center justify-center relative">
						<h1 className="text-[16px] font-semibold">Project Completed</h1>
						<button
							aria-label="Close"
							onClick={handleClose}
							className="absolute right-0 text-xl leading-none px-2 py-1 rounded hover:bg-gray-100">
							×
						</button>
					</div>
				</div>

				{/* Main Content */}
				<div className="flex-1 px-4 py-6">
					{/* Celebration Icon */}
					<div className="flex justify-center mb-6">
						<div className="w-24 h-24 bg-gradient-to-br from-yellow-400 to-purple-500 rounded-full flex items-center justify-center">
							<span className="text-4xl">🎉</span>
						</div>
					</div>

					{/* Congratulations Text */}
					<div className="text-center mb-8">
						<h2 className="text-2xl font-bold text-gray-900 mb-2">Congratulations!</h2>
						<p className="text-gray-600">
							All done! Your {projectName.toLowerCase()} should be installed and looking great.
						</p>
					</div>

					{/* Rating & Review Section */}
					<div className="bg-gray-50 rounded-lg p-4 mb-6">
						<h3 className="text-lg font-semibold text-gray-900 mb-3">Rating & Review</h3>
						
						{/* Star Rating */}
						<div className="flex justify-center mb-4">
							{Array.from({ length: 5 }).map((_, index) => (
								<button
									key={index}
									onClick={() => handleRatingClick(index + 1)}
									className={`text-2xl mx-1 transition-colors ${
										index < rating ? "text-yellow-400" : "text-gray-300"
									}`}>
									★
								</button>
							))}
						</div>
						
						<p className="text-center text-gray-600 mb-3">
							How was your experience fixing this issue?
						</p>
						
						{/* Feedback Input */}
						<textarea
							value={feedback}
							onChange={(e) => setFeedback(e.target.value)}
							placeholder="Write us a feedback..."
							className="w-full p-3 border border-gray-300 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-green-500"
							rows={3}
						/>
					</div>

					{/* Navigation Options */}
					<div className="space-y-4">
						<p className="text-gray-600 text-center">
							If you need to go back and edit your steps, or revisit any parts you feel stuck on, we're here to help!
						</p>
						
						{/* Go Back and Finish Buttons */}
						<div className="grid grid-cols-2 gap-3">
							<button
								onClick={handleGoBack}
								className="py-3 px-4 border border-green-500 bg-white text-black rounded-lg font-medium hover:bg-gray-50">
								Go back
							</button>
							<button
								onClick={handleFinish}
								className="py-3 px-4 bg-green-600 text-white rounded-lg font-medium hover:bg-green-700">
								Finish
							</button>
						</div>

						{/* Additional Options */}
						<div className="space-y-3">
							{/* Share Success and All Projects in a single row */}
							<div className="grid grid-cols-2 gap-3">
								<button
									onClick={handleShareSuccess}
									className="p-4 border border-gray-200 rounded-lg bg-white hover:bg-gray-50">
									<div className="flex flex-col items-center">
										<span className="text-2xl mb-2">✅</span>
										<span className="font-medium text-gray-900">Share Success</span>
										<span className="text-sm text-gray-500">Show off your work</span>
									</div>
								</button>

								<button
									onClick={handleAllProjects}
									className="p-4 border border-gray-200 rounded-lg bg-white hover:bg-gray-50">
									<div className="flex flex-col items-center">
										<span className="text-2xl mb-2">📁</span>
										<span className="font-medium text-gray-900">All Projects</span>
										<span className="text-sm text-gray-500">View history</span>
									</div>
								</button>
							</div>

							<button
								onClick={handleDone}
								className="w-full py-3 px-4 bg-gray-900 text-white rounded-lg font-medium hover:bg-gray-800">
								Done
							</button>
						</div>
					</div>
				</div>
			</div>
		</MobileWrapper>
	);
}
