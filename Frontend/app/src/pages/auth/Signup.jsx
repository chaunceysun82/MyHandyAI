import React, { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { signupUser } from "../../services/auth";

const Signup = () => {
	const location = useLocation();
	const isSignup = location.pathname === "/Signup";
	const [showPassword, setShowPassword] = useState(false);
	const [formData, setFormData] = useState({
		firstname: "",
		lastname: "",
		email: "",
		password: "",
	});
	const [error, setError] = useState("");
	const [passwordStrength, setPasswordStrength] = useState({
		lengthRequirement: false,
		uppercaseRequirement: false,
		lowercaseRequirement: false,
		numberRequirement: false,
		specialCharRequirement: false,
		isStrong: false,
	});

	const navigate = useNavigate();

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

	const handleSubmit = async (e) => {
		e.preventDefault();
		setError("");

		if (!passwordStrength.isStrong) {
			setError("Password is not strong enough.");
			return;
		}

		try {
			const result = await signupUser(formData);
			console.log("Signed up:", result);
			navigate("/login");
		} catch (err) {
			setError(err.message || "Signup failed.");
		}
	};

	return (
		<div className="min-h-screen flex flex-col items-center justify-center py-2 px-4">
			<h1 className="text-[24px] font-semibold p-10">Welcome MyHandyAI!</h1>
			<div className="relative w-full max-w-sm mx-auto mb-8">
				<div className="flex">
					<Link
						to="/login"
						className={`w-1/2 text-center text-lg font-medium pb-2 ${
							isSignup ? "text-gray-500" : "text-purple-600"
						}`}>
						Login
					</Link>
					<Link
						to="/signup"
						className={`w-1/2 text-center text-lg font-medium pb-2 ${
							isSignup ? "text-purple-600" : "text-gray-500"
						}`}>
						Signup
					</Link>
				</div>

				<div className="absolute bottom-0 left-0 w-full h-0.5">
					<div
						className={`w-1/2 h-full bg-purple-600 transform transition-transform duration-300 ease-in-out ${
							isSignup ? "translate-x-0" : "translate-x-full"
						}`}
					/>
				</div>
			</div>

			<form className="w-full max-w-sm" onSubmit={handleSubmit}>
				{/* First Name */}
				<label className="block mb-2 text-sm font-medium text-gray-700">
					First Name <span className="text-red-500">*</span>
				</label>
				<input
					value={formData.firstname}
					onChange={handleChange}
					name="firstname"
					type="text"
					className="w-full p-2 mb-4 border border-gray-300 rounded-lg"
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
					className="w-full p-2 mb-4 border border-gray-300 rounded-lg"
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
					className="w-full p-2 mb-4 border border-gray-300 rounded-lg"
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
						className="w-full p-2 pr-10 border border-gray-300 rounded-lg"
						required
					/>
					<div
						className="absolute inset-y-0 right-3 flex items-center cursor-pointer text-gray-500"
						onClick={() => setShowPassword((prev) => !prev)}>
						{showPassword ? "--" : "X"}
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
					className="w-full p-2 mt-2 text-[16px] bg-blue-600 text-white rounded-lg hover:bg-blue-700"
					type="submit">
					Signup
				</button>
			</form>

			<p className="text-xs text-center mt-auto mb-6 text-gray-500">
				By Signing up, you agree to our{" "}
				<a href="/" className="text-blue-600 hover:underline">
					Terms of Service
				</a>{" "}
				and{" "}
				<a href="/" className="text-blue-600 hover:underline">
					Privacy Policy
				</a>
				.
			</p>
		</div>
	);
};

export default Signup;
