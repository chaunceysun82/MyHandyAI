import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { exchangeCodeForTokens, getCognitoIdToken, getCognitoUser } from "../../services/cognitoAuth";
import { syncCognitoUser, hasCompletedOnboarding } from "../../services/auth";
import defaultNavLogo from "../../assets/default_nav_logo.png";

export default function AuthCallback() {
	const navigate = useNavigate();
	const [error, setError] = useState("");

	useEffect(() => {
		let isMounted = true;

		async function finishLogin() {
			try {
				const params = new URLSearchParams(window.location.search);
				const code = params.get("code");
				const state = params.get("state");
				const cognitoError = params.get("error_description") || params.get("error");

				if (cognitoError) {
					throw new Error(cognitoError);
				}

				if (!code) {
					throw new Error("Missing Cognito authorization code.");
				}

				await exchangeCodeForTokens(code, state);

				const idToken = getCognitoIdToken();
				const syncedUser = await syncCognitoUser(idToken);
				const cognitoUser = getCognitoUser();
				const fullName =
					[syncedUser.firstname, syncedUser.lastname].filter(Boolean).join(" ") ||
					cognitoUser?.email ||
					"User";

				localStorage.setItem("authToken", syncedUser.id);
				localStorage.setItem("displayName", fullName);
				localStorage.setItem("userEmail", syncedUser.email || cognitoUser?.email || "");

				if (hasCompletedOnboarding(syncedUser)) {
					navigate("/home", { replace: true });
				} else {
					localStorage.setItem(
						"tempUserData",
						JSON.stringify({
							userId: syncedUser.id,
							firstname: syncedUser.firstname,
							lastname: syncedUser.lastname,
							email: syncedUser.email,
						})
					);
					navigate("/onboarding", { replace: true });
				}
			} catch (err) {
				if (isMounted) {
					setError(err.message || "Could not finish sign in.");
				}
			}
		}

		finishLogin();

		return () => {
			isMounted = false;
		};
	}, [navigate]);

	return (
		<div className="auth-transition-screen">
			{error ? (
				<div className="w-full max-w-sm rounded-[28px] border border-[#d8e8ee] bg-white px-8 py-8 text-center shadow-[0_24px_60px_rgba(17,63,80,0.08)]">
					<img
						src={defaultNavLogo}
						alt="MyHandyAI"
						className="mx-auto mb-5 h-20 w-20 rounded-full object-cover"
					/>
					<h1 className="text-[24px] font-semibold text-[#000000]">
						Sign in needs attention
					</h1>
					<p className="mt-3 text-sm text-[#595959]">{error}</p>
					<button
						className="mt-6 w-full rounded-[20px] bg-[#1484A3] p-2 text-[16px] font-medium text-white duration-200 hover:bg-[#066580]"
						onClick={() => navigate("/login", { replace: true })}
					>
						Back to login
					</button>
				</div>
			) : (
				<div className="auth-logo-loader" role="status" aria-live="polite">
					<img
						src={defaultNavLogo}
						alt="MyHandyAI"
						className="auth-logo-loader__image"
					/>
					<span className="sr-only">Signing you in</span>
				</div>
			)}
		</div>
	);
}
