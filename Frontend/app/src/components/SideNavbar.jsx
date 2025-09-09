import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import defaultNavLogo from '../assets/default_nav_logo.png';

export default function SideNavbar({ isOpen, onClose, onStartNewProject }) {
  const navigate = useNavigate();
  const [showSignoutConfirm, setShowSignoutConfirm] = useState(false);

  // Get user data from localStorage
  const userName = localStorage.getItem("displayName") || sessionStorage.getItem("displayName") || "User";
  const userEmail = localStorage.getItem("userEmail") || sessionStorage.getItem("userEmail") || "example@email.com";

  const handleSignOut = () => {
    setShowSignoutConfirm(true);
  };

  const confirmSignOut = () => {
    // Clear all stored data
    localStorage.removeItem("authToken");
    sessionStorage.removeItem("authToken");
    localStorage.removeItem("chatMessages");
    localStorage.removeItem("introShown");
    localStorage.removeItem("displayName");
    sessionStorage.removeItem("displayName");
    
    // Navigate to login
    navigate("/login", { replace: true });
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

  const handleSettings = () => {
    console.log("Settings clicked");
    onClose();
  };

  const handleBilling = () => {
    console.log("Billing clicked");
    onClose();
  };

  const handleAbout = () => {
    console.log("About clicked");
    onClose();
  };

  const handleAskAPro = () => {
    console.log("Ask A Pro clicked");
    onClose();
  };

  const handleTerms = () => {
    console.log("Terms clicked");
    onClose();
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

            {/* Settings */}
            <button
              onClick={handleSettings}
              className="w-full flex items-center space-x-3 px-3 py-2.5 text-left text-gray-700 hover:bg-gray-50 rounded-lg transition-colors"
            >
              <svg className="w-4 h-4 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
              <span className="font-medium text-sm">Settings</span>
            </button>

            {/* Billing & Subscriptions */}
            <button
              onClick={handleBilling}
              className="w-full flex items-center space-x-3 px-3 py-2.5 text-left text-gray-700 hover:bg-gray-50 rounded-lg transition-colors"
            >
              <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1" />
              </svg>
              <span className="font-medium text-sm">Billing & Subscriptions</span>
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
    </>
  );
}
