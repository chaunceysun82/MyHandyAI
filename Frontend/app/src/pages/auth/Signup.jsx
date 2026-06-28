import React, { useEffect, useState } from "react";
import { redirectToCognitoLogin } from "../../services/cognitoAuth";

const Signup = () => {
	const [redirectFailed, setRedirectFailed] = useState(false);

	useEffect(() => {
		let cancelled = false;

		redirectToCognitoLogin().catch((err) => {
			console.error("Cognito signup redirect failed:", err);
			if (!cancelled) {
				setRedirectFailed(true);
			}
		});

		return () => {
			cancelled = true;
		};
	}, []);

	return (
		<div className="min-h-screen flex flex-col items-center justify-center bg-[#fffef6] px-4 text-center">
			<h1 className="text-[22px] font-semibold text-[#111827]">
				Opening secure signup...
			</h1>
			<p className="mt-3 max-w-xs text-sm text-[#595959]">
				You are being redirected to MyHandyAI secure account creation.
			</p>

			{redirectFailed && (
				<button
					className="mt-6 rounded-[20px] bg-[#1484A3] px-5 py-2 text-sm font-medium text-white hover:bg-[#066580]"
					type="button"
					onClick={() => redirectToCognitoLogin()}
				>
					Try secure signup again
				</button>
			)}
		</div>
	);
};

export default Signup;
