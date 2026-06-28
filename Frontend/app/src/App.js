import "./App.css";
import { Routes, Route, Navigate } from "react-router-dom";
import Login from "./pages/auth/Login";
import Signup from "./pages/auth/Signup";
import AuthCallback from "./pages/auth/AuthCallback";
import Home from "./pages/Home.jsx";
import Chat from "./pages/Chat.jsx";
import MobileWrapper from "./components/MobileWrapper";
import { useEffect, useRef, useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import Onboarding from "./pages/onboarding/Onboarding.jsx";
import OnboardingWelcome from "./pages/onboarding/OnboardingWelcome.jsx";
import OnboardingComplete from "./pages/onboarding/OnboardingComplete.jsx";
import ProjectOverview from "./pages/ProjectOverview.jsx";
import StepPage from "./pages/StepPage.jsx";
import ToolsPage from "./pages/ToolsPage.jsx";
import ProjectCompleted from "./pages/ProjectCompleted.jsx";
import Feedback from "./pages/Feedback.jsx";
import defaultNavLogo from "./assets/default_nav_logo.png";
import { trackMetricOnce } from "./services/metrics";
import {
	clearAuthStorage,
	getCognitoTokenExpiration,
	isCognitoAuthenticated,
} from "./services/cognitoAuth";

function App() {
	const navigate = useNavigate();
	const location = useLocation();
	const currentRoute = `${location.pathname}${location.search}`;
	const previousRouteRef = useRef(currentRoute);
	const [routeTransitioning, setRouteTransitioning] = useState(false);

	useEffect(() => {
		trackMetricOnce("app_entered", "app_entered");

		const publicPaths = ["/login", "/signup", "/auth/callback"];
		const isPublicPath = publicPaths.includes(location.pathname);
		const isAuthenticated = isCognitoAuthenticated();

		if (!isAuthenticated && !isPublicPath) {
			clearAuthStorage();
			navigate("/login", { replace: true });
			return;
		}

		if (
			isAuthenticated &&
			(location.pathname === "/login" || location.pathname === "/signup")
		) {
			navigate("/home");
		}

		const expiresAt = getCognitoTokenExpiration();
		if (!expiresAt) {
			return;
		}

		const timeout = window.setTimeout(() => {
			clearAuthStorage();
			navigate("/login", { replace: true });
		}, Math.max(expiresAt - Date.now(), 0));

		return () => window.clearTimeout(timeout);
	}, [navigate, location.pathname]);

	useEffect(() => {
		if (previousRouteRef.current === currentRoute) {
			return;
		}

		previousRouteRef.current = currentRoute;
		setRouteTransitioning(true);

		const timeout = window.setTimeout(() => {
			setRouteTransitioning(false);
		}, 700);

		return () => window.clearTimeout(timeout);
	}, [currentRoute]);

	return (
		<MobileWrapper>
			{routeTransitioning && (
				<div className="route-transition-overlay" role="status" aria-live="polite">
					<div className="auth-logo-loader">
						<img
							src={defaultNavLogo}
							alt="MyHandyAI"
							className="auth-logo-loader__image"
						/>
						<span className="sr-only">Loading page</span>
					</div>
				</div>
			)}
			<Routes>
				<Route
					path="/"
					element={
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
