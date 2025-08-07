// src/components/ProjectCard.jsx
import React from "react";

export default function ProjectCard({
  id,
  projectTitle,
  lastActivity,
  percentComplete,
  onStartChat,
  onRemove
}) {
  return (
    <div className="border rounded-lg p-4 bg-white shadow flex justify-between items-center">
      <div>
        <h3 className="text-lg font-semibold">{projectTitle}</h3>
        <p className="text-sm text-gray-500">Last Activity: {lastActivity || "N/A"}</p>
        <p className="text-sm text-gray-500">Progress: {percentComplete || 0}%</p>
      </div>
      <div className="flex flex-col ml-20 space-y-2">
        <button
          className="bg-blue-600 text-white px-3 py-1 rounded text-sm"
          onClick={onStartChat}
        >
          Start Chat
        </button>
        <button
          className="bg-red-500 text-white px-3 py-1 rounded text-sm"
          onClick={onRemove}
        >
          Remove
        </button>
      </div>
    </div>
  );
}
