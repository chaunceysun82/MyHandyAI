import React, { useState, useEffect } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import {getAuth, GoogleAuthProvider, signInWithPopup} from "firebase/auth";
import { app } from "../../firebase";
import {ReactComponent as Google} from '../../assets/google.svg';
import {ReactComponent as Facebook} from '../../assets/Facebook.svg';

const Signup = () => {
	const location = useLocation();
	const isSignup = location.pathname === "/signup";
	const [showPassword, setShowPassword] = useState(false);
	const [formData, setFormData] = useState({
		firstname: "",
		lastname: "",
		email: "",
		password: "",
	});
	const [error, setError] = useState("");
	const [toast, setToast] = useState({ show: false, message: "", type: "" });
	const [isGoogleRedirect, setIsGoogleRedirect] = useState(false);
	
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

	// Check if user was redirected from login with Google data
	useEffect(() => {
		const tempGoogleUser = localStorage.getItem("tempGoogleUser");
		if (tempGoogleUser) {
			try {
				const googleUser = JSON.parse(tempGoogleUser);
				setFormData(prev => ({
					...prev,
					email: googleUser.email,
					firstname: googleUser.displayName.split(" ")[0] || googleUser.displayName,
					lastname: googleUser.displayName.split(" ").slice(1).join(" ") || ""
				}));
				setIsGoogleRedirect(true);
				showToast("Please complete your signup information", "info");
			} catch (error) {
				console.error("Error parsing Google user data:", error);
			}
		}
	}, []);

	const [passwordStrength, setPasswordStrength] = useState({
		lengthRequirement: false,
		uppercaseRequirement: false,
		lowercaseRequirement: false,
		numberRequirement: false,
		specialCharRequirement: false,
		isStrong: false,
	});


	const checkPasswordStrength = (password) => {
		const lengthRequirement = password.length >= 8;
		const uppercaseRequirement = /[A-Z]/.test(password);
		const lowercaseRequirement = /[a-z]/.test(password);
		const numberRequirement = /[0-9]/.test(password);
		const specialCharRequirement = /[^A-Za-z0-9]/.test(password);

		setPasswordStrength({
			lengthRequirement,
			uppercaseRequirement,
			lowercaseRequirement,
			numberRequirement,
			specialCharRequirement,
			isStrong:
				lengthRequirement &&
				uppercaseRequirement &&
				lowercaseRequirement &&
				numberRequirement &&
				specialCharRequirement,
		});
	};

	const handleChange = (e) => {
		const { name, value } = e.target;
		setFormData({ ...formData, [name]: value });

		if (name === "password") checkPasswordStrength(value);
	};

	const signUpWithGoogle = async () => {
		try {
			const result = await signInWithPopup(auth, googleProvider);
			const user = result.user;
			console.log("Google signup successful for:", user.email);
			
			// Clear any temporary Google user data from login redirect
			localStorage.removeItem("tempGoogleUser");
			
			// For signup, always redirect to onboarding since this is a new user
			console.log("New user signing up, redirecting to onboarding");
			localStorage.setItem("authToken", user.uid);
			localStorage.setItem("displayName", user.displayName || user.email?.split("@")[0] || "User");
			localStorage.setItem("email", user.email || "");
			navigate("/onboarding/1");
		} catch (error) {
			console.error("An error occurred during Google signup:", error);
			showToast("Google authentication failed. Please try again.", "error");
		}
	};

	const handleSubmit = async (e) => {
		e.preventDefault();
		setError("");

		if (!passwordStrength.isStrong) {
			setError("Password is not strong enough.");
			return;
		}

		try {
			// Store user data temporarily for combined signup with onboarding
			const userData = {
				firstname: formData.firstname,
				lastname: formData.lastname,
				email: formData.email,
				password: formData.password
			};
			
			// Store user data for onboarding (no API call yet)
			localStorage.setItem("tempUserData", JSON.stringify(userData));
			console.log("User data stored for onboarding:", userData);
			
			navigate("/onboarding");
		} catch (err) {
			setError(err.message || "Signup failed.");
		}
	};

	return (
		<div className="min-h-screen flex flex-col items-center justify-center py-2 px-4">
			<h1 className="text-[20px] font-semibold p-10">Getting Started</h1>
			<div className="relative w-full max-w-sm mx-auto mb-8">
				<div className="flex">
					<Link
						to="/login"
						className={`w-1/2 text-[16px] text-center font-medium pb-2 ${
							isSignup ? "text-black-500" : "text-black-600"
						}`}>
						Login
					</Link>
					<Link
						to="/signup"
						className={`w-1/2 text-[16px] text-center font-medium pb-2 ${
							isSignup ? "text-black-600" : "text-black-500"
						}`}>
						Signup
					</Link>
				</div>

				<div className="absolute bottom-0 left-0 w-full h-0.5">
					<div
						style = {{backgroundColor: "#D9D9D9"}}
						className={`w-1/2 h-full transform transition-transform duration-300 ease-in-out ${
							isSignup ? "translate-x-full" : "translate-x-0"
						}`}
					/>
				</div>
			</div>

			<form className="w-full max-w-sm" onSubmit={handleSubmit}>
				{/* Google Redirect Notice */}
				{isGoogleRedirect && (
					<div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
						<p className="text-sm text-blue-800 text-center">
							📧 <strong>Google Account Detected</strong><br/>
							Please complete your signup information below
						</p>
					</div>
				)}

				{/* First Name */}
				<label className="block mb-2 text-sm font-medium text-gray-700">
					First Name <span className="text-red-500">*</span>
				</label>
				<input
					value={formData.firstname}
					onChange={handleChange}
					name="firstname"
					type="text"
					className="w-full text-[12px] p-2 mb-4 border border-gray-300 rounded-[20px]"
					placeholder="Enter your first name"
					required
				/>

				{/* Last Name */}
				<label className="block mb-2 text-sm font-medium text-gray-700">
					Last Name <span className="text-red-500">*</span>
				</label>
				<input
					value={formData.lastname}
					onChange={handleChange}
					name="lastname"
					type="text"
					className="w-full text-[12px] p-2 mb-4 border border-gray-300 rounded-[20px]"
					placeholder="Enter your last name"
					required
				/>

				{/* Email */}
				<label className="block mb-2 text-sm font-medium text-gray-700">
					Email <span className="text-red-500">*</span>
				</label>
				<input
					value={formData.email}
					onChange={handleChange}
					name="email"
					type="email"
					className="w-full text-[12px] p-2 mb-4 border border-gray-300 rounded-[20px]"
					placeholder="Enter your email"
					required
				/>

				{/* Password */}
				<label className="block mb-2 text-sm font-medium text-gray-700">
					Password <span className="text-red-500">*</span>
				</label>
				<div className="relative w-full mb-2">
					<input
						value={formData.password}
						onChange={handleChange}
						name="password"
						type={showPassword ? "text" : "password"}
						placeholder="Enter your password"
						className="w-full text-[12px] p-2 pr-10 border border-gray-300 rounded-[20px]"
						required
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

				{/* Password strength indicator in a single line */}
				{formData.password.length > 0 && (
					<p className="text-sm mt-2">
						Password must contain:
						<span
							className={`ml-1 ${
								passwordStrength.lengthRequirement
									? "text-green-600"
									: "text-red-500"
							}`}>
							8 characters,
						</span>
						<span
							className={`ml-1 ${
								passwordStrength.uppercaseRequirement
									? "text-green-600"
									: "text-red-500"
							}`}>
							an uppercase,
						</span>
						<span
							className={`ml-1 ${
								passwordStrength.lowercaseRequirement
									? "text-green-600"
									: "text-red-500"
							}`}>
							a lowercase,
						</span>
						<span
							className={`ml-1 ${
								passwordStrength.numberRequirement
									? "text-green-600"
									: "text-red-500"
							}`}>
							a number &
						</span>
						<span
							className={`ml-1 ${
								passwordStrength.specialCharRequirement
									? "text-green-600"
									: "text-red-500"
							}`}>
							a special character.
						</span>
					</p>
				)}
				{/* Error */}
				{error && (
					<div className="text-red-600 text-sm mb-4 text-center">{error}</div>
				)}

				<button
					className="w-full p-2 mt-2 text-[16px] text-white rounded-[20px] bg-[#6FCBAE] hover:bg-green-600 duration-200"
					type="submit">
					Signup
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
			</div>
			
			<div className="flex flex-row gap-6 mb-3">
				<p className="text-[12px] text-[#595959] font-light">Already have an account?</p>
				<a href = "/login" className="text-[12px] text-[#55D468] hover:underline font-semibold">Sign in</a>
			</div>

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

export default Signup;
