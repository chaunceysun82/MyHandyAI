import React from "react";
// import { getAuth, signOut } from "firebase/auth";
import { useNavigate } from "react-router-dom";

const Home = () => {

	// const auth = getAuth();
	const navigate = useNavigate();

	const handleLogOut = () => {
		localStorage.removeItem("authToken");
		sessionStorage.removeItem("authToken");
		navigate("/login");
	};

	const headChat = () => {
		navigate("/chat");
	};

	return (
		<div>
			<h1 className="text-2xl text-red-700 font-bold">Home Page</h1>

			<button
			// 	onClick={() => {
			// 		signOut(auth).then(() => {
			// 			console.log("Signed out from Firebase");
			// 		});
			// 		navigate("/login");
			// 	}
			
			// }
			onClick={handleLogOut}
				className="text-sm text-red-500 mt-3"
			>
				Sign Out
			</button>
			
			<button
			onClick={headChat}
				className="text-sm text-red-500 mt-3"
			>
				Chatbot!
			</button>

		</div>
	);
};

export default Home;
