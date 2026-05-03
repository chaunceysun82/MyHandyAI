import React, { useState } from "react";
import { Link } from "react-router-dom";
import { redirectToCognitoLogin } from "../../services/cognitoAuth";

const Signup = () => {
	const [isRedirecting, setIsRedirecting] = useState(false);

	const handleSignup = async () => {
		setIsRedirecting(true);
		await redirectToCognitoLogin();
	};

	return (
		<div className="min-h-screen flex flex-col items-center px-4 py-6 lg:justify-center lg:bg-[#f2f8fa]">
			<div className="w-full max-w-sm lg:max-w-md lg:rounded-[28px] lg:border lg:border-[#d8e8ee] lg:bg-white lg:px-9 lg:py-10 lg:shadow-[0_24px_60px_rgba(17,63,80,0.08)]">
				<h1 className="pb-3 pt-12 text-center text-[20px] font-semibold text-[#000000] lg:pb-5 lg:pt-0 lg:text-[30px]">
					Getting Started
				</h1>

				<div className="relative mb-8 w-full lg:mb-10">
					<div className="flex">
						<Link
							to="/login"
							className="w-1/2 pb-2 text-center text-[16px] font-medium text-black-500 lg:pb-3 lg:text-[21px]"
						>
							Login
						</Link>
						<Link
							to="/signup"
							className="w-1/2 pb-2 text-center text-[16px] font-medium text-black-600 lg:pb-3 lg:text-[21px]"
						>
							Signup
						</Link>
					</div>

					<div className="absolute bottom-0 left-0 h-0.5 w-full">
						<div
							style={{ backgroundColor: "#D9D9D9" }}
							className="h-full w-1/2 translate-x-full transform transition-transform duration-300 ease-in-out"
						/>
					</div>
				</div>

				<button
					className="mt-5 w-full rounded-[20px] bg-[#1484A3] p-2 text-[16px] font-medium text-white duration-200 hover:bg-[#066580] disabled:cursor-not-allowed disabled:opacity-70 lg:mt-7 lg:rounded-[22px] lg:px-4 lg:py-3 lg:text-[18px]"
					type="button"
					disabled={isRedirecting}
					onClick={handleSignup}
				>
					{isRedirecting ? "Opening secure signup..." : "Create account securely"}
				</button>

				<p className="mt-5 text-center text-[12px] font-light text-[#595959] lg:mt-7 lg:text-[14px]">
					AWS Cognito will handle signup, password reset, and account security.
				</p>

				<div className="mt-5 flex flex-row justify-center gap-6 lg:pt-2">
					<p className="text-[12px] text-[#595959] font-light lg:text-[14px]">
						Already have an account?
					</p>
					<Link
						to="/login"
						className="text-[12px] text-[#55D468] hover:underline font-semibold lg:text-[14px]"
					>
						Sign in
					</Link>
				</div>
			</div>
		</div>
	);
};

export default Signup;
