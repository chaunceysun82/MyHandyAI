import React, { useEffect, useState, useCallback } from "react";
import { useParams, useNavigate, useLocation } from "react-router-dom";
import MobileWrapper from "../../components/MobileWrapper";
import {
	submitOnboardingAnswers,
	fetchOnboardingQuestions,
} from "../../services/onboarding";
import TagSelector from "../../components/onboarding/TagSelector";
import SingleSelectorCard from "../../components/onboarding/SingleSelectorCard";
import DIYConfidenceSelector from "../../components/onboarding/DIYConfindecs";
import LocationSelector from "../../components/onboarding/LocationSelector";
import OnboardingLayout from "./OnboardingLayout";

const Onboarding = () => {
	const [questions, setQuestions] = useState([]);
	const [answers, setAnswers] = useState({});
	const [loading, setLoading] = useState(true);

	const { step } = useParams();
	const navigate = useNavigate();
	const stepIndex = Number(step) - 1;

	const location = useLocation();

	// Utility function to collect all custom items from localStorage
	const collectCustomItemsFromStorage = useCallback(() => {
		const customItemsData = {};
		
		// Iterate through localStorage to find all onboarding custom items
		for (let i = 0; i < localStorage.length; i++) {
			const key = localStorage.key(i);
			if (key && key.startsWith('onboarding_custom_')) {
				try {
					const questionId = key.replace('onboarding_custom_', '');
					const customItems = JSON.parse(localStorage.getItem(key));
					
					if (Array.isArray(customItems) && customItems.length > 0) {
						customItemsData[questionId] = customItems;
						console.log(`Collected custom items for ${questionId}:`, customItems);
					}
				} catch (error) {
					console.error(`Error parsing custom items from ${key}:`, error);
				}
			}
		}
		
		return customItemsData;
	}, []);

	// Function to merge custom items with regular answers
	const mergeCustomItemsWithAnswers = useCallback((regularAnswers, customItemsData) => {
		const mergedAnswers = { ...regularAnswers };
		
		// For each question that has custom items, merge them with the regular answers
		Object.entries(customItemsData).forEach(([questionId, customItems]) => {
			if (mergedAnswers[questionId]) {
				// If question already has answers, merge custom items
				const existingAnswers = Array.isArray(mergedAnswers[questionId]) 
					? mergedAnswers[questionId] 
					: [mergedAnswers[questionId]];
				
				// Add custom items that aren't already in the answers
				customItems.forEach(customItem => {
					if (!existingAnswers.includes(customItem)) {
						existingAnswers.push(customItem);
					}
				});
				
				mergedAnswers[questionId] = existingAnswers;
			} else {
				// If question has no answers, just use custom items
				mergedAnswers[questionId] = customItems;
			}
		});
		
		console.log('Merged answers with custom items:', mergedAnswers);
		return mergedAnswers;
	}, []);

	useEffect(() => {
		const fetchData = async () => {
			try {
				const data = await fetchOnboardingQuestions();
				setQuestions(data);
				setLoading(false);

				if (
					(!step || isNaN(step) || stepIndex < 0 || stepIndex >= data.length) &&
					location.pathname !== "/onboarding/1"
				) {
					navigate("/onboarding/1", { replace: true });
				}
			} catch (err) {
				console.error("Failed to fetch onboarding questions", err);
			}
		};

		fetchData();
	}, [step, stepIndex, navigate, location.pathname]);

	const handleAnswer = useCallback((stepId, value) => {
		setAnswers((prev) => ({
			...prev,
			[stepId]: value,
		}));
	}, []);

	const handleNext = async () => {
		if (stepIndex < questions.length - 1) {
			navigate(`/onboarding/${stepIndex + 2}`);
		} else {
			// Submit onboarding answers (this will handle both new signup and existing user updates)
			try {
				console.log('Original answers before merging:', answers);
				
				// Collect all custom items from localStorage
				const customItemsData = collectCustomItemsFromStorage();
				console.log('Custom items collected from localStorage:', customItemsData);
				
				// Merge custom items with regular answers
				const completeAnswers = mergeCustomItemsWithAnswers(answers, customItemsData);
				console.log('Complete answers ready for submission:', completeAnswers);
				
				// Submit the complete answers including custom items
				await submitOnboardingAnswers(completeAnswers);
				navigate("/onboarding/complete");
			} catch (error) {
				console.error("Error submitting onboarding answers:", error);
				// Handle error - maybe show a message to the user
			}
		}
	};

	const handleBack = () => {
		const prevStep = Number(step) - 1;
		if (prevStep > 0) {
			navigate(`/onboarding/${prevStep}`);
		}
	};

	const handleSkip = () => {
		// Don't save the answer, just move forward
		handleNext();
	};

	// Render question based on its type
	const renderQuestion = (questionData) => {
		const { Category, Options, Question, Comment, Type, _id } = questionData;
		const currentAnswer = answers[_id];

		switch (Category) {
			case "single-selection":
				if (Type === "DIY confidence") {
					return (
						<div className="space-y-4">
							{Options.map((option, idx) => (
								<DIYConfidenceSelector
									key={idx}
									title={option.title}
									description={option.description}
									value={option.title}
									selected={currentAnswer}
									onClick={(val) => handleAnswer(_id, val)}
								/>
							))}
						</div>
					);
				} else {
					return (
						<div className="space-y-4">
							{Options.map((option, idx) => (
								<SingleSelectorCard
									key={idx}
									title={option.title}
									description={option.description}
									value={option.title}
									selected={currentAnswer}
									onClick={(val) => handleAnswer(_id, val)}
								/>
							))}
						</div>
					);
				}

			case "multiple-selection":
				return (
					<TagSelector
						questionId={_id || `question_${_id || 'unknown'}`}
						items={Array.isArray(Options) ? Options.map((opt) => (typeof opt === "string" ? opt : opt.title)) : []}
						selectedItems={currentAnswer || []}
						onToggle={(item) => {
							const isSelected = currentAnswer?.includes(item);
							const updated = isSelected
								? currentAnswer.filter((v) => v !== item)
								: [...(currentAnswer || []), item];
							handleAnswer(_id, updated);
						}}
						onClearAll={() => handleAnswer(_id, [])}
						onAddCustomItem={(custom) => {
							const updated = [...(currentAnswer || []), custom];
							handleAnswer(_id, updated);
						}}
						showClearButton={true}
					/>
				);

			case "combo-box":
				if (Type === "Location") {
					return (
						<LocationSelector
							value={currentAnswer || { country: "", state: "" }}
							onChange={(val) => handleAnswer(_id, val)}
						/>
					);
				}
				break;

			default:
				return <div>Unsupported question type: {Category}</div>;
		}
	};

	if (loading || !questions.length) {
		return (
			<MobileWrapper>
				<div className="flex items-center justify-center min-h-screen">
					<div className="flex space-x-2">
						{[...Array(5)].map((_, i) => (
							<div
								key={i}
								className="w-2 h-10 bg-indigo-500 rounded wave-bar"
								style={{ animationDelay: `${i * 0.15}s` }}
							/>
						))}
					</div>
				</div>
			</MobileWrapper>
		);
	}

	const stepData = questions[stepIndex];
	const currentAnswer = answers[stepData._id];

	return (
		<OnboardingLayout
			currentStep={stepIndex + 1}
			totalSteps={questions.length}
			onNext={handleNext}
			onBack={handleBack}
			onSkip={handleSkip}
			primaryLabel="Continue"
			disableNext={!stepData.Optional && !currentAnswer}
			showSkip={stepData.Optional}>
			<div className="space-y-2">
				<h2 className="text-lg text-center font-semibold">{stepData.Question}</h2>
				{stepData.Comment && (
					<p className="text-sm text-center pb-12 text-gray-500">{stepData.Comment}</p>
				)}
				{renderQuestion(stepData)}
			</div>
		</OnboardingLayout>
	);
};

export default Onboarding;
