import React, { useEffect, useState, useCallback } from "react";
import { useParams, useNavigate, useLocation } from "react-router-dom";
import MobileWrapper from "../../components/MobileWrapper";
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

	const location = useLocation();

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
				await submitOnboardingAnswers(answers);
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
				</div>{" "}
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
			<StepRenderer
				step={stepData}
				value={currentAnswer || null}
				onChange={(val) => handleAnswer(stepData._id, val)}
			/>
		</OnboardingLayout>
	);
};

export default Onboarding;
