import React from "react";
// import { getAuth, signOut } from "firebase/auth";
import { useNavigate } from "react-router-dom";

const Home = () => {

	// const auth = getAuth();
	const navigate = useNavigate();

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
			onClick={() => navigate("/login")}
				className="text-sm text-red-500 mt-3"
			>
				Sign Out
			</button>

		</div>
	);
};

export default Home;
