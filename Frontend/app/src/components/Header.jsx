// src/components/Header.jsx
import React from "react";
import { useNavigate } from "react-router-dom";
import { ReactComponent as Gear } from "../assets/gear.svg";

export default function Header({ userName, onSignOut }) {
  const navigate = useNavigate();
  
  // Helper function to extract first name
  const getFirstName = (fullName) => {
    if (!fullName || fullName === "User") return "User";
    
    // Handle cases where there might be extra spaces or single name
    const trimmedName = fullName.trim();
    if (!trimmedName) return "User";
    
    const firstName = trimmedName.split(" ")[0];
    if (!firstName) return "User";
    
    // Capitalize first letter and make rest lowercase
    return firstName.charAt(0).toUpperCase() + firstName.slice(1).toLowerCase();
  };

  return (
    <div className="flex items-center justify-between mb-6">
      {/* Left: Profile Avatar (60×60) */}
      <div className="flex items-center">
        <button
          onClick={() => navigate("/profile")}
          aria-label="Go to profile"
          className="w-16 h-16 bg-gray-300 rounded-full mr-3 flex-shrink-0"
        />
        <div>
          <p className="text-lg text-gray-600">Welcome back</p>
          <p className="font-bold text-xl">{getFirstName(userName)}</p>
        </div>
      </div>

      {/* Right: Gear & Sign Out */}
      <div className="flex items-center space-x-4">
        <button
          onClick={() => navigate("/settings")}
          aria-label="Settings"
        >
          <Gear className="w-6 h-6 text-gray-600" />
        </button>
        <button
          className="text-sm text-red-500"
          onClick={onSignOut}
        >
          Sign Out
        </button>
      </div>
    </div>
  );
}
