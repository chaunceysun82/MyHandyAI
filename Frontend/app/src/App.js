import "./App.css";
import { Routes, Route } from "react-router-dom";
import Login from "./pages/auth/Login";
import Signup from "./pages/auth/Signup";
import Home from "./pages/Home.jsx";
import MobileWrapper from "./components/MobileWrapper";
import { useEffect } from "react";
import { useNavigate, useLocation  } from "react-router-dom";
import Onboarding from "./pages/onboarding/Onboarding.jsx";
import OnboardingWelcome from "./pages/onboarding/OnboardingWelcome.jsx";
import OnboardingComplete from "./pages/onboarding/OnboardingComplete.jsx";

function App() {

	const navigate = useNavigate();
	const location = useLocation();

	useEffect(() => {
		const token = localStorage.getItem("authToken") || sessionStorage.getItem("authToken");
		if(token && (location.pathname === '/login' || location.pathname === '/signup')) {
			navigate("/");
		}
		
		if(!token && location.pathname === '/')
		{
			navigate("/login");
		}
	}, [navigate, location.pathname]);

	return (
		<MobileWrapper>
			<Routes>
				<Route path="/home" element={<Home />} />
				<Route path="/login" element={<Login key={location.pathname}/>} />
				<Route path="/signup" element={<Signup key={location.pathname}/>} />
					<Route path="/onboarding/" element={<OnboardingWelcome />} />
					<Route path="/onboarding/:step" element={<Onboarding />} />
					<Route path="/onboarding/complete" element={<OnboardingComplete />} />
			</Routes>
		</MobileWrapper>
	);
}

export default App;
