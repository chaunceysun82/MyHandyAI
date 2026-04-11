import React, { useEffect, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import MobileWrapper from "../components/MobileWrapper";
import { getCompletionMessage, submitFeedback } from "../services/feedback";
import { ReactComponent as ShareSuccess } from "../assets/share_success.svg";
import { ReactComponent as AllProjects } from "../assets/all_projects.svg";

const FEEDBACK_TAGS = [
	"Super helpful guides",
	"Easy to follow",
	"Confusing",
	"Too hard",
];

export default function Feedback() {
	const navigate = useNavigate();
	const { projectId } = useParams();
	const { state } = useLocation();
	const projectName = state?.projectName || "Project";

	const [loading, setLoading] = useState(true);
	const [apiMsg, setApiMsg] = useState(
		`All done! Your ${projectName.toLowerCase()} is completed and looking great.`
	);
	const [rating, setRating] = useState(0);
	const [selectedTags, setSelectedTags] = useState([]);
	const [comments, setComments] = useState("");
	const [error, setError] = useState("");
	const [saving, setSaving] = useState(false);

	useEffect(() => {
		let alive = true;
		(async () => {
			setError("");
			setLoading(true);
			try {
				const { message } = await getCompletionMessage(projectId);
				if (alive && message) {
					setApiMsg(message);
				}
			} catch (e) {
				console.warn("completion-message:", e?.message || e);
			} finally {
				if (alive) {
					setLoading(false);
				}
			}
		})();

		return () => {
			alive = false;
		};
	}, [projectId]);

	const toggleTag = (tag) => {
		setSelectedTags((prev) =>
			prev.includes(tag)
				? prev.filter((item) => item !== tag)
				: [...prev, tag]
		);
	};

	const handleGoBack = () => navigate(-1);
	const handleClose = () => navigate("/home");

	const handleFinish = async () => {
		if (!rating) {
			setError("Please select a rating before continuing.");
			return;
		}

		setError("");
		setSaving(true);
		try {
			await submitFeedback(projectId, {
				rating,
				comments: comments.trim(),
				tags: selectedTags,
			});
			navigate("/home");
		} catch (e) {
			setError(e.message || "Could not save feedback.");
		} finally {
			setSaving(false);
		}
	};

	return (
		<MobileWrapper>
			<div className="min-h-screen bg-[#fffef6]">
				<div className="sticky top-0 z-10 bg-white pt-3 pb-1 px-4">
					<div className="flex items-center justify-center relative">
						<h1 className="text-[18px] font-semibold">Project Completed</h1>
						<button
							aria-label="Close"
							onClick={handleClose}
							className="absolute right-0 text-xl leading-none px-2 py-1 rounded hover:bg-gray-100"
						>
							×
						</button>
					</div>
				</div>

				<div className="flex-1 px-4 py-6">
					<div className="flex justify-center mb-4">
						<div
							className="w-24 h-24 rounded-full flex items-center justify-center"
							style={{ backgroundColor: "#E3F2FD" }}
						>
							<span className="text-4xl">🎉</span>
						</div>
					</div>

					<div className="text-center mb-8">
						<h2 className="text-2xl font-bold text-gray-900 mb-2">Congratulations!</h2>
						<p className="text-gray-600">
							{loading ? "Finishing up..." : apiMsg}
						</p>
					</div>

					<div
						className="rounded-lg border-l-2 border-[#1484A3] p-4 mb-4 shadow-md"
						style={{ backgroundColor: "#ffffff" }}
					>
						<h3 className="text-lg font-semibold text-center text-gray-900 mb-1">
							Rating & Review
						</h3>

						<div className="flex justify-center mb-2">
							{[1, 2, 3, 4, 5].map((n) => (
								<button
									key={n}
									onClick={() => setRating(n)}
									className={`text-2xl mx-1 transition-colors hover:scale-110 ${
										n <= rating ? "text-yellow-400" : "text-gray-300"
									}`}
									aria-label={`Rate ${n} star${n > 1 ? "s" : ""}`}
								>
									★
								</button>
							))}
						</div>

						<p className="text-center text-gray-600 mb-3">
							How was your experience fixing this issue?
						</p>

						<div className="grid grid-cols-2 gap-2 mb-4">
							{FEEDBACK_TAGS.map((tag) => {
								const active = selectedTags.includes(tag);
								return (
									<button
										key={tag}
										type="button"
										onClick={() => toggleTag(tag)}
										className={`rounded-xl px-3 py-2 text-sm font-medium transition-colors ${
											active
												? "bg-[#1484A3] text-white"
												: "bg-[#DDF2F8] text-gray-700 hover:bg-[#cdeaf3]"
										}`}
									>
										{tag}
									</button>
								);
							})}
						</div>

						<textarea
							value={comments}
							onChange={(e) => setComments(e.target.value)}
							placeholder="Write us a feedback..."
							className="w-full p-3 border border-gray-300 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 shadow-sm"
							rows={2}
						/>
					</div>

					<div className="rounded-lg border-l-2 border-[#1484A3] px-4 py-2 mb-4 bg-white shadow-md">
						<p className="text-gray-600 text-center text-sm mb-4">
							If you need to go back and edit your steps, or revisit any parts you feel stuck on, we're here to help!
						</p>
						{error && (
							<div className="text-center text-red-600 text-sm mb-4">{error}</div>
						)}

						<div className="grid grid-cols-2 gap-3">
							<button
								onClick={handleGoBack}
								className="py-3 px-4 border border-gray-300 bg-white text-gray-900 rounded-lg font-medium hover:bg-gray-50 shadow-sm hover:shadow-md transition-shadow"
							>
								Go back
							</button>
							<button
								onClick={handleFinish}
								disabled={saving}
								className={`py-3 px-4 rounded-lg font-medium shadow-sm hover:shadow-md transition-shadow ${
									saving ? "bg-[#E9FAFF]" : "bg-[#E9FAFF] hover:bg-[#D1F2FF]"
								}`}
							>
								{saving ? "Saving..." : "Finish"}
							</button>
						</div>
					</div>

					<div className="grid grid-cols-2 gap-3 mb-4">
						<button
							onClick={() => alert("(Placeholder) Share to social / copy link")}
							className="p-2 border border-gray-200 rounded-lg bg-[#E9FAFF] hover:bg-gray-50 shadow-sm hover:shadow-md transition-shadow"
						>
							<div className="flex flex-col items-center">
								<div className="w-8 h-8 mb-1 flex items-center justify-center">
									<ShareSuccess className="w-6 h-6" />
								</div>
								<span className="font-medium text-gray-900">Share Success</span>
								<span className="text-sm text-gray-500">Show off your work</span>
							</div>
						</button>

						<button
							onClick={() => navigate("/home")}
							className="p-2 border border-gray-200 rounded-lg bg-[#E9FAFF] hover:bg-gray-50 shadow-sm hover:shadow-md transition-shadow"
						>
							<div className="flex flex-col items-center">
								<div className="w-8 h-8 mb-1 flex items-center justify-center">
									<AllProjects className="w-6 h-6" />
								</div>
								<span className="font-medium text-gray-900">All Projects</span>
								<span className="text-sm text-gray-500">View history</span>
							</div>
						</button>
					</div>

					<button
						onClick={() => navigate("/home")}
						className="w-full py-3 px-4 text-white rounded-xl font-medium hover:opacity-90 shadow-md hover:shadow-lg transition-shadow"
						style={{ backgroundColor: "#1484A3" }}
					>
						Start New Project
					</button>
				</div>
			</div>
		</MobileWrapper>
	);
}
