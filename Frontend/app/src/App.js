import "./App.css";
import { Routes, Route, Navigate } from "react-router-dom";
import Login from "./pages/auth/Login";
import Signup from "./pages/auth/Signup";
import AuthCallback from "./pages/auth/AuthCallback";
import Home from "./pages/Home.jsx";
import Chat from "./pages/Chat.jsx";
import MobileWrapper from "./components/MobileWrapper";
import { useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import Onboarding from "./pages/onboarding/Onboarding.jsx";
import OnboardingWelcome from "./pages/onboarding/OnboardingWelcome.jsx";
import OnboardingComplete from "./pages/onboarding/OnboardingComplete.jsx";
import ProjectOverview from "./pages/ProjectOverview.jsx";
import StepPage from "./pages/StepPage.jsx";
import ToolsPage from "./pages/ToolsPage.jsx";
import ProjectCompleted from "./pages/ProjectCompleted.jsx";
import Feedback from "./pages/Feedback.jsx";
import { trackMetricOnce } from "./services/metrics";
import { isCognitoAuthenticated } from "./services/cognitoAuth";

function App() {
	const navigate = useNavigate();
	const location = useLocation();

	useEffect(() => {
		trackMetricOnce("app_entered", "app_entered");

		const token =
			localStorage.getItem("authToken") || sessionStorage.getItem("authToken");
		const isAuthenticated = token || isCognitoAuthenticated();
		if (
			isAuthenticated &&
			(location.pathname === "/login" || location.pathname === "/signup")
		) {
			navigate("/home");
		}

		if (!isAuthenticated && location.pathname === "/") {
			navigate("/login");
		}
	}, [navigate, location.pathname]);

	return (
		<MobileWrapper>
			<Routes>
				<Route
					path="/"
					element={
						localStorage.getItem("authToken") ||
						sessionStorage.getItem("authToken") ||
						isCognitoAuthenticated() ? (
							<Navigate to="/home" replace />
						) : (
							<Navigate to="/login" replace />
						)
					}
				/>
				<Route path="/" element={<Login />} />
				<Route path="/home" element={<Home />} />
				<Route path="/login" element={<Login key={location.pathname} />} />
				<Route path="/signup" element={<Signup key={location.pathname} />} />
				<Route path="/auth/callback" element={<AuthCallback />} />
				<Route path="/chat" element={<Chat />} />
				<Route path="/onboarding/" element={<OnboardingWelcome />} />
				<Route path="/onboarding/complete" element={<OnboardingComplete />} />
				<Route path="/onboarding/:step" element={<Onboarding />} />
				<Route path="/projects/:projectId/overview" element={<ProjectOverview />} />
				<Route
					path="/projects/:projectId/steps/:stepIndex"
					element={<StepPage />}
				/>
				<Route
					path="/projects/:projectId/tools"
					element={<ToolsPage />}
				/>
				<Route
					path="/projects/:projectId/completed"
					element={<ProjectCompleted />}
				/>
				<Route
					path="/projects/:projectId/feedback"
					element={<Feedback />}
				/>
			</Routes>
			
		</MobileWrapper>
	);
}

export default App;
