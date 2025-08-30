import React, { useState, useEffect } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import {getAuth, GoogleAuthProvider, signInWithPopup} from "firebase/auth";
import { app } from "../../firebase";
import {ReactComponent as Google} from '../../assets/google.svg';
import {ReactComponent as Facebook} from '../../assets/Facebook.svg';
import FieldError from "../../components/FieldError";
import { createUserDuringSignup } from "../../services/auth";

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
	
	// Field-level error states
	const [errors, setErrors] = useState({
		firstname: "",
		lastname: "",
		email: "",
		password: "",
		general: ""
	});
	
	const [isGoogleRedirect, setIsGoogleRedirect] = useState(false);
	
	const navigate = useNavigate();

	const auth = getAuth(app);
	const googleProvider = new GoogleAuthProvider();

	// Clear errors when path changes
	useEffect(() => {
		setFormData({
			firstname: "",
			lastname: "",
			email: "",
			password: "",
		});
		setErrors({
			firstname: "",
			lastname: "",
			email: "",
			password: "",
			general: ""
		});
	}, [location.pathname]);

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
			} catch (error) {
				console.error("Error parsing Google user data:", error);
			}
		}
	}, []);

	// Clear specific field error when user starts typing
	const clearFieldError = (fieldName) => {
		setErrors(prev => ({
			...prev,
			[fieldName]: ""
		}));
	};

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
		
		// Clear field error when user starts typing
		clearFieldError(name);
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
			localStorage.setItem("userEmail", user.email || "");
			navigate("/onboarding/1");
		} catch (error) {
			console.error("An error occurred during Google signup:", error);
			setErrors(prev => ({
				...prev,
				general: "Google authentication failed. Please try again."
			}));
		}
	};

	const handleSubmit = async (e) => {
		e.preventDefault();

		// Basic validation
		let hasErrors = false;
		const newErrors = { firstname: "", lastname: "", email: "", password: "", general: "" };

		if (!formData.firstname.trim()) {
			newErrors.firstname = "First name is required";
			hasErrors = true;
		}

		if (!formData.lastname.trim()) {
			newErrors.lastname = "Last name is required";
			hasErrors = true;
		}

		if (!formData.email.trim()) {
			newErrors.email = "Email is required";
			hasErrors = true;
		} else if (!/\S+@\S+\.\S+/.test(formData.email)) {
			newErrors.email = "Please enter a valid email address";
			hasErrors = true;
		}

		if (!formData.password.trim()) {
			newErrors.password = "Password is required";
			hasErrors = true;
		} else if (!passwordStrength.isStrong) {
			newErrors.password = "Password is not strong enough";
			hasErrors = true;
		}

		if (hasErrors) {
			setErrors(newErrors);
			return;
		}

		try {
			// Create user during signup - backend will handle email existence check
			const user = await createUserDuringSignup({
				firstname: formData.firstname,
				lastname: formData.lastname,
				email: formData.email,
				password: formData.password
			});
			console.log("User created during signup:", user);
			
			// Store user ID for onboarding
			localStorage.setItem("tempUserData", JSON.stringify({
				userId: user.id,
				firstname: formData.firstname,
				lastname: formData.lastname,
				email: formData.email
			}));
			
			// Navigate to onboarding and replace history
			navigate("/onboarding", { replace: true });
		} catch (err) {
			// Handle specific error cases
			if (err.message.includes("Email already exists")) {
				setErrors(prev => ({
					...prev,
					general: "Email address already in use. Please choose a different one."
				}));
			} else {
				setErrors(prev => ({
					...prev,
					general: err.message || "Signup failed."
				}));
			}
		}
	};

	return (
		<div className="min-h-screen flex flex-col items-center py-2 px-4">
			<h1 className="text-[20px] mt-[-24px] font-semibold p-10">Getting Started</h1>
			
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
				{/* First Name */}
				<FieldError error={errors.firstname}>
					<label className="block mb-2 text-sm font-medium text-gray-700">
						First Name <span className="text-red-500">*</span>
					</label>
					<div className="relative">
						<input
							value={formData.firstname}
							onChange={handleChange}
							name="firstname"
							type="text"
							className={`w-full text-[12px] p-2 mb-4 border rounded-[20px] transition-colors ${
								errors.firstname 
									? 'border-red-500 focus:border-red-500 focus:ring-red-500' 
									: 'border-gray-300 focus:border-blue-500 focus:ring-blue-500'
							}`}
							placeholder="Enter your first name"
							required
						/>
						{errors.firstname && (
							<div className="absolute inset-y-0 right-3 flex items-center">
								<div className="w-5 h-5 bg-red-500 rounded-full flex items-center justify-center">
									<span className="text-white text-xs font-bold">!</span>
								</div>
							</div>
						)}
					</div>
				</FieldError>

				{/* Last Name */}
				<FieldError error={errors.lastname}>
					<label className="block mb-2 text-sm font-medium text-gray-700">
						Last Name <span className="text-red-500">*</span>
					</label>
					<div className="relative">
						<input
							value={formData.lastname}
							onChange={handleChange}
							name="lastname"
							type="text"
							className={`w-full text-[12px] p-2 mb-4 border rounded-[20px] transition-colors ${
								errors.lastname 
									? 'border-red-500 focus:border-red-500 focus:ring-red-500' 
									: 'border-gray-300 focus:border-blue-500 focus:ring-blue-500'
							}`}
							placeholder="Enter your last name"
							required
						/>
						{errors.lastname && (
							<div className="absolute inset-y-0 right-3 flex items-center">
								<div className="w-5 h-5 bg-red-500 rounded-full flex items-center justify-center">
									<span className="text-white text-xs font-bold">!</span>
								</div>
							</div>
						)}
					</div>
				</FieldError>

				{/* Email */}
				<FieldError error={errors.email}>
					<label className="block mb-2 text-sm font-medium text-gray-700">
						Email <span className="text-red-500">*</span>
					</label>
					<div className="relative">
						<input
							value={formData.email}
							onChange={handleChange}
							name="email"
							type="email"
							className={`w-full text-[12px] p-2 mb-4 border rounded-[20px] transition-colors ${
								errors.email 
									? 'border-red-500 focus:border-red-500 focus:ring-red-500' 
									: 'border-gray-300 focus:border-blue-500 focus:ring-blue-500'
							}`}
							placeholder="Enter your email"
							required
						/>
						{errors.email && (
							<div className="absolute inset-y-0 right-3 flex items-center">
								<div className="w-5 h-5 bg-red-500 rounded-full flex items-center justify-center">
									<span className="text-white text-xs font-bold">!</span>
								</div>
							</div>
						)}
					</div>
				</FieldError>

				{/* Password */}
				<FieldError error={errors.password}>
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
							className={`w-full text-[12px] p-2 pr-10 border rounded-[20px] transition-colors ${
								errors.password 
									? 'border-red-500 focus:border-red-500 focus:ring-red-500' 
									: 'border-gray-300 focus:border-blue-500 focus:ring-blue-500'
							}`}
							required
						/>
						<div className="absolute inset-y-0 right-3 flex items-center gap-2">
							{errors.password && (
								<div className="w-5 h-5 bg-red-500 rounded-full flex items-center justify-center">
									<span className="text-white text-xs font-bold">!</span>
								</div>
							)}
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
					

					<button className="rounded-[20px] text-[14px] flex items-center justify-center gap-3 font-bold mb-3 p-2 w-[350px] bg-[#F2F2F5] hover:text-blue-600 hover:bg-gray-100 transition duration-200">
						<Facebook width={28} height={28} />
						Continue with Facebook
					</button>
			</div>
			
			<div className="flex flex-row gap-6 mb-3">
				<p className="text-[12px] text-[#595959] font-light">Already have an account?</p>
				<a href = "/login" className="text-[12px] text-[#55D468] hover:underline font-semibold">Sign in</a>
			</div>
		</div>
	);
};

export default Signup;
