import React from "react";
import { Link, useLocation } from "react-router-dom";
import { useState } from "react";
import { loginUser } from "../../services/auth";
import { useNavigate } from "react-router-dom";

const Login = () => {
	const location = useLocation();
	const isLogin = location.pathname === "/login";
	const [showPassword, setShowPassword] = useState(false);
	const [email, setEmail] = useState("");
	const [password, setPassword] = useState("");
	const [error, setError] = useState("");
	const navigate = useNavigate();

	const handleSubmit = async (e) => {
		e.preventDefault();
		setError("");

		try {
			const result = await loginUser(email, password);
			console.log("Logged in:", result);
			navigate("/"); // Redirect to home page on successful login
		} catch (err) {
			setError(err.message);
		}
	};

	return (
		<div className="min-h-screen flex flex-col items-center justify-center p-4">
			<h1 className="text-[24px]  text-semibold p-10">Welcome back!</h1>
			<div className="relative w-full max-w-sm mx-auto mb-8">
				{/* Tab buttons */}
				<div className="flex">
					<Link
						to="/login"
						className={`w-1/2 text-center text-lg font-medium pb-2 ${
							isLogin ? "text-purple-600" : "text-gray-500"
						}`}>
						Login
					</Link>
					<Link
						to="/signup"
						className={`w-1/2 text-center text-lg font-medium pb-2 ${
							!isLogin ? "text-purple-600" : "text-gray-500"
						}`}>
						Signup
					</Link>
				</div>

				{/* Underline */}
				<div className="absolute bottom-0 left-0 w-full h-0.5">
					<div
						className={`w-1/2 h-full bg-purple-600 transform transition-transform duration-300 ease-in-out ${
							isLogin ? "translate-x-0" : "translate-x-full"
						}`}
					/>
				</div>
			</div>
			<form className="w-full mb-5" onSubmit={handleSubmit}>
				<label className="block mb-2 text-sm font-medium text-gray-700">
					Email <span className="text-red-500">*</span>
				</label>
				<input
					type="email"
					value={email}
					onChange={(e) => setEmail(e.target.value)}
					className="w-full p-2 mb-7 border border-gray-300 rounded-lg"
					placeholder="Enter your email"
				/>
				<label className="block mb-2 text-sm font-medium text-gray-700">
					Password <span className="text-red-500">*</span>
				</label>
				<div className="relative w-full mb-5">
					<input
						value={password}
						onChange={(e) => setPassword(e.target.value)}
						type={showPassword ? "text" : "password"}
						placeholder="Enter your password"
						className="w-full p-2 pr-10 border border-gray-300 rounded-lg"
					/>
					<div
						className="absolute inset-y-0 right-3 flex items-center cursor-pointer text-gray-500"
						onClick={() => setShowPassword((prev) => !prev)}>
						{showPassword ? "--" : "X"}
					</div>
				</div>

				<div className="flex justify-between items-center">
					<label className="flex items-center text-sm text-gray-700">
						<input
							type="checkbox"
							className="mr-2 size-4 border border-gray-300 rounded-lg focus:ring-blue-500 focus:border-blue-500"
						/>
						Remember me
					</label>
					<Link
						to="/forgot-password"
						className="text-sm text-blue-600 hover:underline">
						Forgot password?
					</Link>
				</div>

				<button
					className="w-full p-2 mt-14 text-[16px] bg-blue-600 text-white rounded-lg hover:bg-blue-700"
					type="submit">
					Login
				</button>
			</form>

			<p className="text-xs text-center mt-auto mb-6 text-gray-500">
				By login, you agree to our{" "}
				<a href="/" className="text-blue-600 hover:underline">
					Terms of Conditions
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

export default Login;
