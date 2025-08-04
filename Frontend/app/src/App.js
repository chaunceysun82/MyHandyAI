import "./App.css";
import { Routes, Route } from "react-router-dom";
import Login from "./pages/auth/Login";
import Signup from "./pages/auth/Signup";
import Home from "./pages/Home.jsx";
import MobileWrapper from "./components/MobileWrapper";
import { useEffect } from "react";
import { useNavigate, useLocation  } from "react-router-dom";

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
				<Route path="/" element={<Home />} />
				<Route path="/login" element={<Login key={location.pathname}/>} />
				<Route path="/signup" element={<Signup key={location.pathname}/>} />
			</Routes>
		</MobileWrapper>
	);
}

export default App;