import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
	submitOnboardingAnswers,
	fetchOnboardingQuestions,
} from "../../services/onboarding";
import StepRenderer from "../../components/onboarding/StepRender";
import OnboardingLayout from "./OnboardingLayout";

const Onboarding = () => {
	const [questions, setQuestions] = useState([]);
	const [answers, setAnswers] = useState({});
	const [loading, setLoading] = useState(true);

	const { step } = useParams();
	const navigate = useNavigate();
	const stepIndex = Number(step) - 1;

	useEffect(() => {
		const fetchData = async () => {
			try {
				const data = await fetchOnboardingQuestions();
				setQuestions(data);
				setLoading(false);

				if (!step || isNaN(step) || stepIndex < 0 || stepIndex >= data.length) {
					navigate("/onboarding/1", { replace: true });
				}
			} catch (err) {
				console.error("Failed to fetch onboarding questions", err);
			}
		};

		fetchData();
	}, [step, stepIndex, navigate]);

	const handleAnswer = (stepId, value) => {
		setAnswers((prev) => ({
			...prev,
			[stepId]: value,
		}));
	};

	const handleNext = () => {
		if (stepIndex < questions.length - 1) {
			navigate(`/onboarding/${stepIndex + 2}`);
		} else {
			submitOnboardingAnswers(answers);
			navigate("/onboarding/complete");
		}
	};

	const handleBack = () => {
		if (stepIndex > 0) {
			navigate(`/onboarding/${stepIndex}`);
		}
	};

	const handleSkip = () => {
		// Don't save the answer, just move forward
		handleNext();
	};

	if (loading || !questions.length) {
		return <div className="text-center py-10">Loading...</div>;
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
			<StepRenderer
				step={stepData}
				value={currentAnswer || null}
				onChange={(val) => handleAnswer(stepData._id, val)}
			/>
		</OnboardingLayout>
	);
};

export default Onboarding;
