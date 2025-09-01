import React, { useEffect } from "react";
import { Link, useLocation } from "react-router-dom";
import { useState } from "react";
import { loginUser, hasCompletedOnboarding } from "../../services/auth";
import { useNavigate } from "react-router-dom";
import {ReactComponent as Google} from '../../assets/google.svg';
import {ReactComponent as Facebook} from '../../assets/Facebook.svg';
import {getAuth, GoogleAuthProvider, signInWithPopup} from "firebase/auth";
import { app } from "../../firebase";
import { getUserById } from "../../services/auth";
import FieldError from "../../components/FieldError";

const Login = () => {
	const location = useLocation();
	const isLogin = location.pathname === "/login";
	const [showPassword, setShowPassword] = useState(false);
	const [email, setEmail] = useState("");
	const [password, setPassword] = useState("");
	const [rememberMe, setRememberMe] = useState(false);
	
	// Field-level error states
	const [errors, setErrors] = useState({
		email: "",
		password: "",
		general: ""
	});
	
	const navigate = useNavigate();

	const auth = getAuth(app);
	const googleProvider = new GoogleAuthProvider();

	// Clear errors when path changes
	useEffect(() => {
		setEmail("");
		setPassword("");
		setErrors({
			email: "",
			password: "",
			general: ""
		});
	}, [location.pathname]);

	// Clear specific field error when user starts typing
	const clearFieldError = (fieldName) => {
		setErrors(prev => ({
			...prev,
			[fieldName]: ""
		}));
	};

	const signUpWithGoogle = async () => {
		try {
			const result = await signInWithPopup(auth, googleProvider);
			const user = result.user;
			console.log("Google login attempt for:", user.email);
			
			// For Google sign-in, we'll try to find existing user by attempting to create a temporary user
			// This works with the existing backend endpoint
			try {
				const response = await fetch(`${process.env.REACT_APP_BASE_URL}/users`, {
					method: "POST",
					headers: { "Content-Type": "application/json" },
					body: JSON.stringify({
						firstname: "temp",
						lastname: "temp",
						email: user.email,
						password: "temp"
					}),
				});
				
				if (response.status === 400) {
					const error = await response.json();
					if (error.detail === "Email already exists") {
						// User exists, we need to check onboarding completion
						// But since we don't have a way to get user data by email without backend changes,
						// we'll redirect to onboarding to let them complete it
						console.log("Existing user found, redirecting to onboarding");
						
						// Store Google user data temporarily
						localStorage.setItem("tempGoogleUser", JSON.stringify({
							uid: user.uid,
							email: user.email,
							displayName: user.displayName || user.email?.split("@")[0] || "User"
						}));
						
						setErrors(prev => ({
							...prev,
							general: "Please login with your password to continue, or complete onboarding if you haven't finished it."
						}));
						return;
					}
				}
				
				// User doesn't exist, proceed with signup
				console.log("New user, proceeding with signup");
				localStorage.setItem("tempGoogleUser", JSON.stringify({
					uid: user.uid,
					email: user.email,
					displayName: user.displayName || user.email?.split("@")[0] || "User"
				}));
				navigate("/signup");
				
			} catch (error) {
				console.error("Error checking user existence:", error);
				// If we can't check, assume new user and redirect to signup
				localStorage.setItem("tempGoogleUser", JSON.stringify({
					uid: user.uid,
					email: user.email,
					displayName: user.displayName || user.email?.split("@")[0] || "User"
				}));
				navigate("/signup");
			}
		} catch (error) {
			console.error("An error occurred during Google sign-in:", error);
			setErrors(prev => ({
				...prev,
				general: "Google authentication failed. Please try again."
			}));
		}
	};

	const handleSubmit = async (e) => {
		e.preventDefault();
		
		// Clear previous errors
		setErrors({
			email: "",
			password: "",
			general: ""
		});

		// Basic validation
		let hasErrors = false;
		const newErrors = { email: "", password: "", general: "" };

		if (!email.trim()) {
			newErrors.email = "Email is required";
			hasErrors = true;
		} else if (!/\S+@\S+\.\S+/.test(email)) {
			newErrors.email = "Please enter a valid email address";
			hasErrors = true;
		}

		if (!password.trim()) {
			newErrors.password = "Password is required";
			hasErrors = true;
		}

		if (hasErrors) {
			setErrors(newErrors);
			return;
		}

		try {
			console.log("Calling the loginUser function");
			const res = await loginUser(email, password);
			
			const store = rememberMe ? localStorage : sessionStorage;
     		store.setItem("authToken", res.id);
    		
    		// fetch user data and check onboarding completion
     		try {
       		const user = await getUserById(res.id);
       		const full = [user.firstname, user.lastname].filter(Boolean).join(" ") || (user.email ?? "User");
       		store.setItem("displayName", full);
       		store.setItem("userEmail", user.email || "");
       		
       		// Check if user has completed onboarding
       		if (hasCompletedOnboarding(user)) {
       			console.log("User has completed onboarding, redirecting to home");
       			// Set flag to indicate user is coming from login
       			localStorage.setItem("fromLogin", "true");
       			navigate("/home");
       		} else {
       			console.log("User has not completed onboarding, redirecting to onboarding");
       			// Store user data temporarily for onboarding completion
       			localStorage.setItem("tempUserData", JSON.stringify({
       				userId: res.id,
       				firstname: user.firstname,
       				lastname: user.lastname,
       				email: user.email
       			}));
       			navigate("/onboarding", { replace: true });
       		}
     		} catch (error) {
       		console.error("Error fetching user data:", error);
       		// If we can't fetch user data, redirect to home as fallback
       		navigate("/home");
     		}

			console.log("Login result: ", res);
		}
		catch (err) {
			console.log("Login error: ", err.message);
			
			// Handle specific error cases
			if (err.message.includes("Invalid credentials") || err.message.includes("Login failed")) {
				setErrors(prev => ({
					...prev,
					general: "Incorrect email or password. Please try again!"
				}));
			} else {
				setErrors(prev => ({
					...prev,
					general: err.message || "Login failed. Please try again."
				}));
			}
		}
	};

	return (
		<div className="min-h-screen flex flex-col items-center p-4">
			<h1 className="text-[20px] mt-[-24px] font-semibold pt-20 pb-3">Welcome back!</h1>
			
			{/* General Error Message */}
			{errors.general && (
				<div className="w-full max-w-sm mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
					<div className="flex items-center gap-2 text-red-800">
						<svg className="w-4 h-4 text-red-600" fill="currentColor" viewBox="0 0 20 20">
							<path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
						</svg>
						<span className="text-sm font-medium">{errors.general}</span>
					</div>
				</div>
			)}
			
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
				<FieldError error={errors.email}>
					<label className="block mb-2 text-sm font-medium text-gray-700">
						Email <span className="text-red-500">*</span>
					</label>
					<div className={`relative w-full ${errors.email ? 'mb-4' : 'mb-5'}`}>
						<input
							type="email"
							value={email}
							onChange={(e) => {
								setEmail(e.target.value);
								clearFieldError('email');
							}}
							style={{backgroundColor: '#F7F7F7'}}
							className={`w-full p-2 border text-[12px] rounded-[20px] transition-colors ${
								errors.email 
									? 'border-red-500 focus:border-red-500 focus:ring-red-500' 
									: 'border-gray-300 focus:border-blue-500 focus:ring-blue-500'
							}`}
							placeholder="hello@example.com"
						/>
						{/* {errors.email && (
							<div className="absolute inset-y-0 right-3 flex items-center">
								<div className="w-5 h-5 bg-red-500 rounded-full flex items-center justify-center">
									<span className="text-white text-xs font-bold">!</span>
								</div>
							</div>
						)} */}
					</div>
				</FieldError>

				<FieldError error={errors.password}>
					<label className="block mb-2 text-sm font-medium text-gray-700">
						Password <span className="text-red-500">*</span>
					</label>
					<div className={`relative w-full ${errors.email ? 'mb-4' : 'mb-5'}`}>
						<input
							value={password}
							onChange={(e) => {
								setPassword(e.target.value);
								clearFieldError('password');
							}}
							type={showPassword ? "text" : "password"}
							placeholder="Password"
							style={{backgroundColor: '#F7F7F7'}}
							className={`w-full p-2 pr-10 border text-[12px] rounded-[20px] transition-colors ${
								errors.password 
									? 'border-red-500 focus:border-red-500 focus:ring-red-500' 
									: 'border-gray-300 focus:border-blue-500 focus:ring-blue-500'
							}`}
						/>
						<div className="absolute inset-y-0 right-3 flex items-center gap-2">
							{/* {errors.password && (
								<div className="w-5 h-5 bg-red-500 rounded-full flex items-center justify-center">
									<span className="text-white text-xs font-bold">!</span>
								</div>
							)} */}
							<div
								className="cursor-pointer text-gray-500"
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
					</div>
				</FieldError>

				<div className="flex justify-between items-center">
					<label className="flex items-center text-gray-700 cursor-pointer">
						<div className="relative w-5 h-5 mr-2">
							<input
								type="checkbox"
								checked={rememberMe}
								onChange={() => setRememberMe(prev => !prev)}
								className="appearance-none w-full h-full bg-[#D9D9D9] border border-gray-300 rounded-[3px] checked:bg-blue-500 checked:border-blue-500 cursor-pointer"
							/>
							{/* Custom checkmark */}
							<svg
								className={`absolute top-0 left-0 w-full h-full text-white pointer-events-none ${
									rememberMe ? "block" : "hidden"
								}`}
								viewBox="0 0 24 24"
							>
								<polyline
									points="20 6 9 17 4 12"
									stroke="currentColor"
									strokeWidth="2"
									fill="none"
									strokeLinecap="round"
									strokeLinejoin="round"
								/>
							</svg>
						</div>
						<span className="font-light text-[12px] text-[#000000]">Remember Me</span>
						</label>

					<Link
						to="/forgot-password"
						style={{color: '#595959'}}
						className="font-light text-[12px] text-[#000000] hover:underline">
						Forgot password?
					</Link>
				</div>

				<button
					className="w-full p-2 mt-5 text-[16px] text-white font-medium rounded-[20px] bg-[#1484A3] hover:bg-[#066580] duration-200"
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
					

					<button className="rounded-[20px] text-[14px] flex items-center justify-center gap-3 font-bold mb-3 p-2 w-[350px] bg-[#F2F2F5] hover:text-blue-600 hover:bg-gray-100 transition duration-200">
						<Facebook width={28} height={28} />
						Continue with Facebook
					</button>
			</div>
			
			<div className="flex flex-row gap-[20px]">
				<p className="text-[12px] text-[#595959] font-light">Don't have an account?</p>
				<a href = "/signup" className="text-[12px] text-[#55D468] hover:underline font-semibold">Sign up</a>
			</div>
		</div>
	);
};

export default Login;
