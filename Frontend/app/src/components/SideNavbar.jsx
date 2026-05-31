import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import defaultNavLogo from '../assets/default_nav_logo.png';
import { redirectToCognitoLogout } from "../services/cognitoAuth";
import { getUserById, updateUser } from "../services/auth";
import { fetchOnboardingQuestions } from "../services/onboarding";
import StepRenderer from "./onboarding/StepRender";
import LocationSelector from "./onboarding/LocationSelector";

export default function SideNavbar({ isOpen, onClose, onStartNewProject }) {
  const navigate = useNavigate();
  const [showSignoutConfirm, setShowSignoutConfirm] = useState(false);
  const [activeInfoModal, setActiveInfoModal] = useState(null);
  const [profileUser, setProfileUser] = useState(null);
  const [profileForm, setProfileForm] = useState({});
  const [profileLoading, setProfileLoading] = useState(false);
  const [profileSaving, setProfileSaving] = useState(false);
  const [profileError, setProfileError] = useState("");
  const [profileSuccess, setProfileSuccess] = useState("");
  const [onboardingQuestions, setOnboardingQuestions] = useState([]);

  // Get user data from localStorage
  const userName = localStorage.getItem("displayName") || sessionStorage.getItem("displayName") || "User";
  const userEmail = localStorage.getItem("userEmail") || sessionStorage.getItem("userEmail") || "example@email.com";

  const handleSignOut = () => {
    setShowSignoutConfirm(true);
  };

  const confirmSignOut = () => {
    redirectToCognitoLogout();
  };

  const cancelSignOut = () => {
    setShowSignoutConfirm(false);
  };

  const handleStartNewProject = () => {
    // Close the sidebar first
    onClose();
    
    // Then trigger the start new project modal from parent component
    if (onStartNewProject) {
      onStartNewProject();
    }
  };

  const handleMyProjects = () => {
    navigate("/home");
    onClose();
  };

  const handleMyProfile = async () => {
    setActiveInfoModal("profile");
    setProfileError("");
    setProfileSuccess("");

    const userId = localStorage.getItem("authToken") || sessionStorage.getItem("authToken");
    if (!userId || profileUser) return;

    setProfileLoading(true);
    try {
      const [user, questions] = await Promise.all([
        getUserById(userId),
        onboardingQuestions.length ? Promise.resolve(onboardingQuestions) : fetchOnboardingQuestions(),
      ]);
      setOnboardingQuestions(questions);
      setProfileUser(user);
      setProfileForm(createProfileForm(user, questions));
    } catch (err) {
      console.error("Could not load profile:", err);
      setProfileError("Could not load your profile answers right now.");
    } finally {
      setProfileLoading(false);
    }
  };

  const handleAbout = () => {
    setActiveInfoModal("about");
  };

  const handleAskAPro = () => {
    console.log("Ask A Pro clicked");
    onClose();
  };

  const handleTerms = () => {
    setActiveInfoModal("terms");
  };

  const closeInfoModal = () => {
    setActiveInfoModal(null);
  };

  const createProfileForm = (user = {}, questions = onboardingQuestions) => ({
    experienceLevel: user.experienceLevel || "",
    confidence: getConfidenceTitle(user.confidence, questions),
    tools: parseProfileList(user.tools),
    interestedProjects: parseProfileList(user.interestedProjects),
    country: user.country || "",
    state: user.state || "",
    describe: user.describe || "",
  });

  const parseProfileList = (value) => {
    if (Array.isArray(value)) return value;
    if (typeof value === "string") {
      return value.split(",").map((item) => item.trim()).filter(Boolean);
    }
    return [];
  };

  const formatProfileValue = (value) => {
    if (Array.isArray(value)) return value.join(", ");
    if (typeof value === "object" && value !== null) {
      return [value.country, value.state].filter(Boolean).join(", ") || JSON.stringify(value);
    }
    return value;
  };

  const confidenceMap = {
    "not confident at all": 1,
    "slightly confident": 2,
    "somewhat confident": 3,
    "confident": 4,
    "very confident": 5,
  };

  const findOnboardingQuestion = (matcher) =>
    onboardingQuestions.find((question) => {
      const text = [
        question.Type,
        question.Question,
        question.Comment,
        ...(Array.isArray(question.Options) ? question.Options.map((option) => option?.title || option) : []),
      ].filter(Boolean).join(" ").toLowerCase();
      return matcher(text, question);
    });

  const getConfidenceQuestion = (questions = onboardingQuestions) =>
    questions.find((question) => String(question.Type || "").toLowerCase() === "diy confidence");

  const getConfidenceTitle = (confidence, questions = onboardingQuestions) => {
    if (confidence === undefined || confidence === null || confidence === "") return "";
    if (typeof confidence === "string" && Number.isNaN(Number(confidence))) return confidence;

    const confidenceNumber = Number(confidence);
    const confidenceQuestion = getConfidenceQuestion(questions);
    const options = confidenceQuestion?.Options || [];
    const matchingOption = options.find((option) => confidenceMap[String(option.title || option).toLowerCase()] === confidenceNumber);
    return matchingOption?.title || String(confidence);
  };

  const getConfidenceNumber = (confidence) => {
    if (confidence === undefined || confidence === null || confidence === "") return "";
    if (!Number.isNaN(Number(confidence))) return Number(confidence);
    return confidenceMap[String(confidence).toLowerCase()] || "";
  };

  const handleProfileFieldChange = (field, value) => {
    setProfileForm((prev) => ({ ...prev, [field]: value }));
    setProfileSuccess("");
  };

  const handleSaveProfile = async () => {
    const userId = profileUser?.id || profileUser?._id || localStorage.getItem("authToken") || sessionStorage.getItem("authToken");
    if (!userId) {
      setProfileError("Could not find your user profile.");
      return;
    }

    setProfileSaving(true);
    setProfileError("");
    setProfileSuccess("");

    try {
      const payload = {
        experienceLevel: profileForm.experienceLevel,
        confidence: getConfidenceNumber(profileForm.confidence),
        tools: formatProfileValue(profileForm.tools) || "",
        interestedProjects: formatProfileValue(profileForm.interestedProjects) || "",
        country: profileForm.country,
        state: profileForm.state,
        describe: profileForm.describe,
      };
      const updated = await updateUser(userId, payload);
      const nextUser = { ...profileUser, ...payload, ...updated };
      setProfileUser(nextUser);
      setProfileForm(createProfileForm(nextUser));
      setProfileSuccess("Profile updated.");
    } catch (err) {
      console.error("Could not save profile:", err);
      setProfileError("Could not save your profile changes. Please try again.");
    } finally {
      setProfileSaving(false);
    }
  };

  const profileQuestionConfigs = [
    {
      field: "experienceLevel",
      label: "Experience level",
      matcher: (text, question) => question.Category === "single-selection" && text.includes("experience"),
      fallbackPlaceholder: "Example: Beginner, Intermediate, Advanced",
    },
    {
      field: "confidence",
      label: "DIY confidence",
      matcher: (_text, question) => String(question.Type || "").toLowerCase() === "diy confidence",
      fallbackPlaceholder: "Example: Confident",
    },
    {
      field: "tools",
      label: "Tools available",
      matcher: (text, question) => question.Category === "multiple-selection" && (text.includes("tool") || text.includes("equipment")),
      fallbackPlaceholder: "Example: drill, screwdriver, level",
    },
    {
      field: "interestedProjects",
      label: "Interested projects",
      matcher: (text, question) => question.Category === "multiple-selection" && (text.includes("project") || text.includes("interested")),
      fallbackPlaceholder: "Example: plumbing, mounting, painting",
    },
  ];

  const renderProfileQuestion = ({ field, label, matcher, fallbackPlaceholder }) => {
    const question = findOnboardingQuestion(matcher);
    const labelClass = "text-[11px] font-semibold uppercase tracking-wide text-gray-500";

    if (question) {
      const step = {
        ...question,
        Question: label,
        Comment: "",
        _id: `profile_${field}`,
      };

      return (
        <div key={field} className="rounded-2xl border border-[#d8e8ee] bg-white/70 p-3">
          <StepRenderer
            step={step}
            value={profileForm[field]}
            onChange={(value) => handleProfileFieldChange(field, value)}
          />
        </div>
      );
    }

    return (
      <label key={field} className="block">
        <span className={labelClass}>{label}</span>
        <input
          className="mt-1 w-full rounded-xl border border-[#d8e8ee] bg-white px-3 py-2 text-sm text-gray-900 outline-none focus:border-[#1484A3] focus:ring-2 focus:ring-[#1484A3]/20"
          value={formatProfileValue(profileForm[field]) || ""}
          placeholder={fallbackPlaceholder}
          onChange={(e) => handleProfileFieldChange(field, e.target.value)}
        />
      </label>
    );
  };

  const modalContent = {
    profile: {
      title: "My Profile",
      body: (
        <>
          <p className="text-sm text-gray-600">
            Your profile is connected through your secure MyHandyAI account.
          </p>
          <div className="mt-4 rounded-xl bg-[#E9FAFF] p-3 text-left">
            <p className="text-xs font-semibold uppercase tracking-wide text-[#1484A3]">Name</p>
            <p className="text-sm font-medium text-gray-900">{userName}</p>
            <p className="mt-3 text-xs font-semibold uppercase tracking-wide text-[#1484A3]">Email</p>
            <p className="text-sm font-medium text-gray-900">{userEmail}</p>
          </div>

          <div className="mt-4 text-left">
            <p className="text-xs font-semibold uppercase tracking-wide text-[#1484A3]">
              Onboarding answers
            </p>

            {profileLoading && (
              <p className="mt-2 text-sm text-gray-500">Loading your answers...</p>
            )}

            {profileError && (
              <p className="mt-2 rounded-lg bg-red-50 p-2 text-xs text-red-600">
                {profileError}
              </p>
            )}

            {!profileLoading && !profileError && !profileUser && (
              <p className="mt-2 text-sm text-gray-500">
                No onboarding answers saved yet.
              </p>
            )}

            {!profileLoading && profileUser && (
              <div className="mt-3 space-y-3">
                {profileQuestionConfigs.map(renderProfileQuestion)}

                <div className="rounded-2xl border border-[#d8e8ee] bg-white/70 p-3">
                  <p className="text-[11px] font-semibold uppercase tracking-wide text-gray-500">
                    Location
                  </p>
                  <LocationSelector
                    value={{ country: profileForm.country || "", state: profileForm.state || "" }}
                    onChange={(value) => {
                      handleProfileFieldChange("country", value.country || "");
                      handleProfileFieldChange("state", value.state || "");
                    }}
                  />
                </div>

                <label className="block">
                  <span className="text-[11px] font-semibold uppercase tracking-wide text-gray-500">
                    About you
                  </span>
                  <textarea
                    className="mt-1 min-h-[88px] w-full rounded-xl border border-[#d8e8ee] bg-white px-3 py-2 text-sm text-gray-900 outline-none focus:border-[#1484A3] focus:ring-2 focus:ring-[#1484A3]/20"
                    value={profileForm.describe || ""}
                    placeholder="Tell MyHandyAI what helps personalize your project guidance."
                    onChange={(e) => handleProfileFieldChange("describe", e.target.value)}
                  />
                </label>

                {profileSuccess && (
                  <p className="rounded-lg bg-green-50 p-2 text-xs text-green-700">
                    {profileSuccess}
                  </p>
                )}

                <button
                  className="w-full rounded-xl bg-[#1484A3] px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-[#066580] disabled:cursor-not-allowed disabled:opacity-60"
                  type="button"
                  onClick={handleSaveProfile}
                  disabled={profileSaving}
                >
                  {profileSaving ? "Saving..." : "Save profile"}
                </button>
              </div>
            )}
          </div>
        </>
      ),
    },
    about: {
      title: "About MyHandyAI",
      body: (
        <p className="text-sm leading-6 text-gray-600">
          MyHandyAI helps homeowners break household problems into practical, step-by-step repair plans. It can collect details, suggest tools, estimate time and cost, and guide you through each step with an assistant.
        </p>
      ),
    },
    terms: {
      title: "Terms & Conditions",
      body: (
        <div className="space-y-3 text-sm leading-6 text-gray-600">
          <p>
            MyHandyAI provides informational guidance only. Always verify important details before starting work, follow product instructions, and use proper safety equipment.
          </p>
          <p>
            For electrical, gas, structural, roofing, plumbing emergencies, or any task that feels unsafe, stop and contact a qualified professional.
          </p>
        </div>
      ),
    },
  };

  return (
    <>
      {/* Backdrop */}
      {isOpen && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-50 z-40"
          onClick={onClose}
        />
      )}

      {/* Sidebar */}
      <div 
        className={`absolute top-0 right-0 h-full w-72 bg-[#fffef6] rounded-l-2xl shadow-2xl transform transition-transform duration-300 ease-in-out z-50 flex flex-col ${
          isOpen ? 'translate-x-0' : 'translate-x-full'
        }`}
        style={{ height: '100%' }}
      >
        {/* User Profile Section */}
        <div className="px-4 py-4 border-b border-gray-100 flex-shrink-0">
          <div className="flex items-center space-x-3">
            {/* Profile Picture */}
            <div className="w-16 h-16 bg-gray-300 rounded-full flex items-center justify-center">
              <img 
                src={defaultNavLogo} 
                alt="Default Nav Logo" 
                className="w-full h-full object-cover rounded-full"
                onError={(e) => {
                  e.target.style.display = 'none';
                  e.target.nextSibling.style.display = 'flex';
                }}
              />
              <div className="w-full h-full bg-gray-400 rounded-full flex items-center justify-center text-white font-semibold text-lg" style={{display: 'none'}}>
                {userName.charAt(0).toUpperCase()}
              </div>
            </div>
            
            {/* User Info */}
            <div className="flex flex-col">
              <h3 className="text-base font-semibold text-gray-900">{userName.split(' ').map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase()).join(' ')}</h3>
              <p className="text-xs text-gray-600">{userEmail}</p>
            </div>
          </div>
        </div>

        {/* Start New Project Button */}
        <div className="px-4 py-3 flex-shrink-0">
          <button
            onClick={handleStartNewProject}
            className="w-full flex items-center justify-center space-x-2 px-3 py-2.5 bg-[#1484A3] text-gray-800 rounded-lg hover:bg-gray-300 transition-colors font-medium text-sm"
          >
            <span className="text-white text-semibold text-md">+ Start New Project</span>
          </button>
        </div>

        {/* Navigation Links */}
        <div className="flex-1 px-4 py-3 overflow-y-auto">
          <nav className="space-y-1">
            {/* My Projects */}
            <button
              onClick={handleMyProjects}
              className="w-full flex items-center space-x-3 px-3 py-2.5 text-left text-gray-700 hover:bg-gray-50 rounded-lg transition-colors"
            >
              <svg className="w-4 h-4 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
              </svg>
              <span className="font-medium text-sm">My Projects</span>
            </button>

            {/* My Profile */}
            <button
              onClick={handleMyProfile}
              className="w-full flex items-center space-x-3 px-3 py-2.5 text-left text-gray-700 hover:bg-gray-50 rounded-lg transition-colors"
            >
              <svg className="w-4 h-4 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.75 7.5a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.5 20.25a7.5 7.5 0 0115 0" />
              </svg>
              <span className="font-medium text-sm">My Profile</span>
            </button>

            {/* About MyHandyAI */}
            <button
              onClick={handleAbout}
              className="w-full flex items-center space-x-3 px-2 py-2.5 text-left text-gray-700 hover:bg-gray-50 rounded-lg transition-colors"
            >
              <span className="font-medium text-sm">About MyHandyAI</span>
            </button>

            {/* Ask A Pro */}
            <button
              onClick={handleAskAPro}
              className="w-full flex items-center justify-between px-2 py-2.5 text-left text-gray-700 hover:bg-gray-50 rounded-lg transition-colors"
            >
              <span className="font-medium text-sm">Ask A Pro</span>
              <span className="text-[#1484A3] text-semibold text-sm">Coming Soon</span>
            </button>

            {/* Terms & Conditions */}
            <button
              onClick={handleTerms}
              className="w-full flex items-center space-x-3 px-2 py-2.5 text-left text-gray-700 hover:bg-gray-50 rounded-lg transition-colors"
            >
              <span className="font-medium text-sm">Terms & Conditions</span>
            </button>
          </nav>
        </div>

        {/* Footer - Logout Button and Disclaimer - Fixed at bottom */}
        <div className="px-4 py-3 border-t border-gray-100 flex-shrink-0">
          {/* Logout Button */}
          <button
            onClick={handleSignOut}
            className="w-full flex items-center justify-center space-x-2 px-3 py-2.5 bg-[#E9FAFF] shadow-md  rounded-lg font-medium text-sm mb-2"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
            </svg>
            <span>Log-Out</span>
          </button>

          {/* Disclaimer */}
          <p className="text-xs text-gray-500 text-center">
            MyHandyAI may not be fully accurate. Please verify important information!
          </p>
        </div>
      </div>

      {/* Sign Out Confirmation Modal */}
      {showSignoutConfirm && (
        <div className="absolute inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-[#fffef6] rounded-lg p-4 max-w-xs w-full mx-4">
            <div className="text-center">
              <div className="w-10 h-10 bg-[#E9FAFF] rounded-full flex items-center justify-center mx-auto mb-3">
                <svg className="w-5 h-5 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z" />
                </svg>
              </div>
              <h3 className="text-base font-semibold text-gray-900 mb-2">
                Confirm Sign Out
              </h3>
              <p className="text-xs text-gray-600 mb-4">
                Are you sure you want to sign out? You'll need to log in again to access your account.
              </p>
            </div>

            <div className="flex gap-2">
              <button
                onClick={cancelSignOut}
                className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-gray-700 font-medium hover:bg-gray-50 transition-colors text-sm"
              >
                Cancel
              </button>
              <button
                onClick={confirmSignOut}
                className="flex-1 px-3 py-2 bg-[#E9FAFF] rounded-lg font-medium  transition-colors text-sm"
              >
                Yes, Sign Out
              </button>
            </div>
          </div>
        </div>
      )}

      {activeInfoModal && (
        <div className="absolute inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[60] p-4">
          <div className="bg-[#fffef6] rounded-2xl p-5 max-h-[82vh] max-w-xs w-full mx-4 overflow-y-auto shadow-2xl">
            <div className="flex items-start justify-between gap-3">
              <h3 className="text-lg font-semibold text-gray-900">
                {modalContent[activeInfoModal].title}
              </h3>
              <button
                onClick={closeInfoModal}
                className="-mt-1 rounded-lg px-2 text-2xl leading-none text-gray-500 hover:bg-gray-100"
                aria-label="Close"
              >
                ×
              </button>
            </div>

            <div className="mt-4">
              {modalContent[activeInfoModal].body}
            </div>

            {activeInfoModal !== "profile" && (
              <button
                onClick={closeInfoModal}
                className="mt-5 w-full rounded-xl bg-[#1484A3] px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-[#066580]"
              >
                Close
              </button>
            )}
          </div>
        </div>
      )}
    </>
  );
}
