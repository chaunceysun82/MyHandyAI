import React, { useState } from "react";
import { useNavigate } from "react-router-dom";

export default function SideNavbar({ isOpen, onClose }) {
  const navigate = useNavigate();
  const [showSignoutConfirm, setShowSignoutConfirm] = useState(false);

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

  const handleHomeClick = () => {
    navigate("/home");
    onClose(); // Close the sidebar
  };

  const handleProfileClick = () => {
    // Demo profile action
    console.log("Profile clicked");
    onClose();
  };

  const handleSettingsClick = () => {
    // Demo settings action
    console.log("Settings clicked");
    onClose();
  };

  const handleHelpClick = () => {
    // Demo help action
    console.log("Help clicked");
    onClose();
  };

  const handleAboutClick = () => {
    // Demo about action
    console.log("About clicked");
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
        className={`absolute top-0 right-0 h-full w-64 bg-white shadow-2xl transform transition-transform duration-300 ease-in-out z-50 ${
          isOpen ? 'translate-x-0' : 'translate-x-full'
        }`}
        style={{ height: '100%' }}
      >
        {/* Header */}
        <div className="px-4 py-4 border-b border-gray-100">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-900">Menu</h2>
            <button
              onClick={onClose}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* Navigation Items */}
        <div className="flex-1 px-4 py-4 overflow-y-auto">
          <nav className="space-y-2">
            {/* Home Button */}
            <button
              onClick={handleHomeClick}
              className="w-full flex items-center space-x-3 px-3 py-2.5 text-left text-gray-700 hover:bg-gray-50 rounded-lg transition-colors"
            >
              <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
              </svg>
              <span className="font-medium text-sm">Home</span>
            </button>

            {/* Profile */}
            <button
              onClick={handleProfileClick}
              className="w-full flex items-center space-x-3 px-3 py-2.5 text-left text-gray-700 hover:bg-gray-50 rounded-lg transition-colors"
            >
              <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
              </svg>
              <span className="font-medium text-sm">Profile</span>
            </button>

            {/* Settings */}
            <button
              onClick={handleSettingsClick}
              className="w-full flex items-center space-x-3 px-3 py-2.5 text-left text-gray-700 hover:bg-gray-50 rounded-lg transition-colors"
            >
              <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
              <span className="font-medium text-sm">Settings</span>
            </button>

            {/* Help & Support */}
            <button
              onClick={handleHelpClick}
              className="w-full flex items-center space-x-3 px-3 py-2.5 text-left text-gray-700 hover:bg-gray-50 rounded-lg transition-colors"
            >
              <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span className="font-medium text-sm">Help & Support</span>
            </button>

            {/* About */}
            <button
              onClick={handleAboutClick}
              className="w-full flex items-center space-x-3 px-3 py-2.5 text-left text-gray-700 hover:bg-gray-50 rounded-lg transition-colors"
            >
              <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span className="font-medium text-sm">About</span>
            </button>
          </nav>

         
        </div>

        {/* Footer - Sign Out Button (Sticky to Bottom) */}
        <div className="mt-auto px-4 py-4 border-t border-gray-100 bg-gray-50">
          <button
            onClick={handleSignOut}
            className="w-full flex items-center justify-center space-x-2 px-3 py-2.5 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors font-medium text-sm"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
            </svg>
            <span>Sign Out</span>
          </button>
        </div>
      </div>

      {/* Sign Out Confirmation Modal */}
      {showSignoutConfirm && (
        <div className="absolute inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg p-4 max-w-xs w-full mx-4">
            <div className="text-center">
              <div className="w-10 h-10 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-3">
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
                className="flex-1 px-3 py-2 bg-red-600 text-white rounded-lg font-medium hover:bg-red-700 transition-colors text-sm"
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
