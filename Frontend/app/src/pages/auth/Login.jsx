import React, { useEffect } from "react";
import { Link, useLocation } from "react-router-dom";
import { useState } from "react";
import { loginUser } from "../../services/auth";
import { useNavigate } from "react-router-dom";
import {ReactComponent as Google} from '../../assets/google.svg';
import {ReactComponent as Facebook} from '../../assets/Facebook.svg';
import {getAuth, GoogleAuthProvider, signInWithPopup} from "firebase/auth";
import { app } from "../../firebase";
import { getUserById } from "../../services/auth";

const Login = () => {
	const location = useLocation();
	const isLogin = location.pathname === "/login";
	const [showPassword, setShowPassword] = useState(false);
	const [email, setEmail] = useState("");
	const [password, setPassword] = useState("");
	const [rememberMe, setRememberMe] = useState(false);
	const [toast, setToast] = useState({ show: false, message: "", type: "" });
	const navigate = useNavigate();

	const auth = getAuth(app);
	const googleProvider = new GoogleAuthProvider();

	// Toast function
	const showToast = (message, type = "info") => {
		setToast({ show: true, message, type });
		setTimeout(() => {
			setToast({ show: false, message: "", type: "" });
		}, 3000);
	};


	// const signInValidation = () => {
	// 	if(email === '' || password === '')
	// 	{
	// 		console.log("Please enter both email and password to proceed.");
	// 		return false;
	// 	}
	// 	return true;
	// }

	useEffect(() => {
		setEmail("");
		setPassword("");
	}, [location.pathname]);

	const signUpWithGoogle = async () => {
		try {
			const result = await signInWithPopup(auth, googleProvider);
			const user = result.user;
			console.log("Google login attempt for:", user.email);
			
			// Check if user exists in our backend
			try {
				const response = await fetch(`${process.env.REACT_APP_BASE_URL}/users/email/${user.email}`);
				
				if (response.ok) {
					// User exists in backend, proceed with login
					console.log("Existing user found, proceeding with login");
					const store = rememberMe ? localStorage : sessionStorage;
					store.setItem("authToken", user.uid);
					const name = user.displayName || (user.email?.split("@")[0]) || "User";
					store.setItem("displayName", name);
					store.setItem("email", user.email || "");
					navigate("/home");
				} else {
					// User doesn't exist in backend, redirect to signup
					console.log("User not found in database, redirecting to signup");
					
					// Store Google user data temporarily for signup
					localStorage.setItem("tempGoogleUser", JSON.stringify({
						uid: user.uid,
						email: user.email,
						displayName: user.displayName || user.email?.split("@")[0] || "User"
					}));
					
					// Show toast message and redirect to signup
					showToast("User account not found. Please sign up first.", "error");
					setTimeout(() => {
						navigate("/signup");
					}, 2000); // Wait 2 seconds for toast to be visible
				}
			} catch (error) {
				console.error("Error checking user existence:", error);
				// If we can't check, assume user doesn't exist and redirect to signup
				console.log("Couldn't verify user, redirecting to signup");
				
				// Store Google user data temporarily for signup
				localStorage.setItem("tempGoogleUser", JSON.stringify({
					uid: user.uid,
					email: user.email,
					displayName: user.displayName || user.email?.split("@")[0] || "User"
				}));
				
				// Show toast message and redirect to signup
				showToast("Unable to verify user account. Please sign up first.", "error");
				setTimeout(() => {
					navigate("/signup");
				}, 2000);
			}
		} catch (error) {
			console.error("An error occurred during Google login:", error);
			showToast("Google authentication failed. Please try again.", "error");
		}
	};

	const handleSubmit = async (e) => {
		e.preventDefault();
		try {
			console.log("Calling the loginUser function");
			const res = await loginUser(email, password);
			
			//if(res.id)
			//{
				//if(rememberMe)
				//{
					//localStorage.setItem("authToken", res.id);
				//}
				//else
				//{
					//sessionStorage.setItem("authToken", res.id);
				//}
			//}
			const store = rememberMe ? localStorage : sessionStorage;
     		store.setItem("authToken", res.id);
    		// fetch name and cache it for the header
     		try {
       		const u = await getUserById(res.id);
       		const full = [u.firstname, u.lastname].filter(Boolean).join(" ") || (u.email ?? "User");
       		store.setItem("displayName", full);
     		} catch { /* ignore; we'll fallback in Home */ }

			console.log("Login result: ", res);
			navigate("/home")
		}
		catch (err) {
			console.log("Login error: ", err.message);
		}
	};



	return (
		<div className="min-h-screen flex flex-col items-center p-4">
			<h1 className="text-[20px] mt-[-24px] font-semibold p-10">Welcome back!</h1>
			<div className="relative w-full max-w-sm mx-auto mb-8">
				{/* Tab buttons */}
				<div className="flex">
					<Link
						to="/login"
						className={`w-1/2 text-[16px] text-center font-medium pb-2 ${
							isLogin ? "text-black-600" : "text-black-500"
						}`}>
						Login
					</Link>
					<Link
						to="/signup"
						className={`w-1/2 text-[16px] text-center font-medium pb-2 ${
							!isLogin ? "text-black-600" : "text-black-500"
						}`}>
						Signup
					</Link>
				</div>

				{/* Underline */}
				<div className="absolute bottom-0 left-0 w-full h-0.5">
					<div
						style = {{backgroundColor: "#D9D9D9"}}
						className={`w-1/2 h-full transform transition-transform duration-300 ease-in-out ${
							isLogin ? "translate-x-0" : "translate-x-full"
						}`}
					/>
				</div>
			</div>
			<form className="w-full " onSubmit={handleSubmit}>
				<label className="block mb-2 text-sm font-medium text-gray-700">
					Email <span className="text-red-500">*</span>
				</label>
				<input
					type="email"
					value={email}
					onChange={(e) => setEmail(e.target.value)}
					style={{backgroundColor: '#F7F7F7'}}
					className="w-full p-2 mb-7 border text-[12px] border-gray-300 rounded-[20px]"
					placeholder="hello@example.com"
				/>
				<label className="block mb-2 text-sm font-medium text-gray-700">
					Password <span className="text-red-500">*</span>
				</label>
				<div className="relative w-full mb-5">
					<input
						value={password}
						onChange={(e) => setPassword(e.target.value)}
						type={showPassword ? "text" : "password"}
						placeholder="Password"
						style={{backgroundColor: '#F7F7F7'}}
						className="w-full p-2 pr-10 border border-gray-300 text-[12px] rounded-[20px]"
					/>
					<div
						className="absolute inset-y-0 right-3 flex items-center cursor-pointer text-gray-500"
						onClick={() => setShowPassword((prev) => !prev)}>
						{showPassword ? 
							<img 
								alt = "opening eye" 
								src="https://cdn-icons-png.flaticon.com/128/159/159604.png"
								className="w-5 h-5"
							/> : <img 
									src="https://cdn-icons-png.flaticon.com/128/2767/2767146.png" 	
									alt = "eye-closing" 
									className="w-5 h-5"
								/>
						}
					</div>
				</div>
				<div className="flex justify-between items-center">
					<label className="flex text-[12px] items-center text-sm text-gray-700">
						<input
							type="checkbox"
							checked={rememberMe}
							onChange={() => setRememberMe((prev) => !prev)}
							className="mr-2 size-4 border border-gray-300 rounded-lg focus:ring-blue-500 focus:border-blue-500"
						/>
						<p className="font-light">Remember Me</p>
					</label>
					<Link
						to="/forgot-password"
						style={{color: '#595959'}}
						className="text-sm font-light hover:underline">
						Forgot password?
					</Link>
				</div>

				<button
					className="w-full p-2 mt-5 text-[16px] text-white rounded-[20px] bg-[#6FCBAE] hover:bg-green-600 duration-200"
					type="submit">
					Login
				</button>

			</form>
			<p className="mt-5 text-[12px] font-light">Or</p>

			<div className="h-auto flex flex-col items-center p-4">
					
					<button onClick={signUpWithGoogle} className="rounded-[20px] text-[14px] flex items-center justify-center gap-3 font-bold mb-3 p-2 w-[350px] bg-[#F2F2F5] hover:bg-gray-200 transition duration-200">
						<Google width={28} height={28}/>
						Continue with Google
					</button>
					

					<button className="rounded-[20px] text-[14px] text-white flex items-center justify-center gap-3 font-bold mb-3 p-2 w-[350px] bg-[#1877F2] hover:text-blue-600 hover:bg-gray-100 transition duration-200">
						<Facebook width={28} height={28} />
						Continue with Facebook
					</button>

					<button className="rounded-[20px] text-[14px] font-bold mb-3 p-2 w-[350px] bg-[#F2F2F5] hover:bg-gray-200 transition duration-200">
						Use Face ID
					</button>
			</div>
			
			<div className="flex flex-row gap-6">
				<p className="text-[12px] text-[#595959] font-light">Don't have an account?</p>
				<a href = "/signup" className="text-[12px] text-[#55D468] hover:underline font-semibold">Sign up</a>
			</div>
			

			{/* <p className="text-xs text-center mt-auto mb-6 text-gray-500">
				By login, you agree to our{" "}
				<a href="/" className="text-blue-600 hover:underline">
					Terms of Conditions
				</a>{" "}
				and{" "}
				<a href="/" className="text-blue-600 hover:underline">
					Privacy Policy
				</a>
				.
			</p> */}

			{/* Toast Notification */}
			{toast.show && (
				<div className={`fixed top-4 right-4 z-50 p-4 rounded-lg shadow-lg max-w-sm ${
					toast.type === "error" 
						? "bg-red-500 text-white" 
						: toast.type === "success" 
						? "bg-green-500 text-white" 
						: "bg-blue-500 text-white"
				}`}>
					<div className="flex items-center justify-between">
						<span className="text-sm font-medium">{toast.message}</span>
						<button 
							onClick={() => setToast({ show: false, message: "", type: "" })}
							className="ml-4 text-white hover:text-gray-200"
						>
							×
						</button>
					</div>
				</div>
			)}
		</div>
	);
};

export default Login;
