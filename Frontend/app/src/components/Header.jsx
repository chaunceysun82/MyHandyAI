// src/components/Header.jsx
import React from "react";
import { useNavigate } from "react-router-dom";
import { ReactComponent as Gear } from "../assets/gear.svg";

export default function Header({ userName, onSignOut }) {
  const navigate = useNavigate();

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
          <p className="font-bold text-xl">{userName}</p>
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
