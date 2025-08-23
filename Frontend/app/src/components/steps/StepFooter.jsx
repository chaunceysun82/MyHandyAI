import React, {useState} from "react";
import { useNavigate } from "react-router-dom";
import ChatWindow from "../Chat/ChatWindow";

export default function StepFooter({ 
	projectId, 
	projectName, 
	stepNumber, 
	stepTitle, 
	totalSteps,
	projectVideoUrl, // Add this prop
	onPrev, 
	onNext,
	userId,
	isPrevDisabled = false,
	isNextDisabled = false,
	isNextFinal = false
}) {
	const navigate = useNavigate();

	const [openModal, setOpenModal] = useState(false);
	const [open, setOpen] = useState(true);

	const URL = process.env.REACT_APP_BASE_URL;


	// const userId = localStorage.getItem("authToken");
	
	console.log("User ID:", userId);

	const handleChatClick = () => {
		// navigate("/chat", { 
		// 	state: { 
		// 		projectId, 
		// 		projectName: projectName || "Project",
		// 		from: "step",
		// 		stepNumber: stepNumber,
		// 		stepTitle: stepTitle
		// 	}
		// });
		setOpenModal(true);
	};

	const handlePrevClick = () => {
		// Call the onPrev function passed from parent
		onPrev();
	};

	const handleNextClick = () => {
		// Call the onNext function passed from parent
		onNext();
	};

	return (
		<div className="px-4 pb-4 space-y-3">
			{/* Assistant prompt pill */}
			<div className="rounded-xl border border-gray-200 bg-gray-50 px-3 py-2 text-[12px] text-gray-600 flex items-center justify-between">
				<span>Hi "User", Need MyHandyAI Assistant?</span>
				<button
					onClick={handleChatClick}
					className="ml-3 px-3 py-1 rounded-lg bg-[#6FCBAE] text-white text-[12px] font-semibold">
					Ask
				</button>
			</div>

			{openModal && (
				<ChatWindow
					isOpen={open}
					projectId={projectId}
					onClose={() => setOpenModal(false)}
					secondChatStatus={true}
					URL={URL}
					userId={userId}
					stepNumber={stepNumber}
					// secondSessionID={true}
				/>
			)}

			{/* Bottom Navigation */}
			<div className="grid grid-cols-2 gap-3">
				<button
					onClick={handlePrevClick}
					disabled={isPrevDisabled}
					className={`py-2 rounded-lg font-medium ${
						isPrevDisabled
							? "bg-gray-100 text-gray-400 cursor-not-allowed"
							: "border border-gray-300 bg-gray-50 text-sm"
					}`}>
					Previous
				</button>
				<button
					onClick={handleNextClick}
					disabled={isNextDisabled}
					className={`py-2 rounded-lg font-medium ${
						isNextDisabled
							? "bg-gray-100 text-gray-400 cursor-not-allowed"
							: isNextFinal
							? "bg-green-600 text-white hover:bg-green-700"
							: "bg-black text-white text-sm font-semibold"
					}`}>
					{isNextFinal ? "Finish" : "Next Step"}
				</button>
			</div>
		</div>
	);
}
