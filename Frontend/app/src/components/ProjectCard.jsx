// src/components/ProjectCard.jsx
import React from 'react';

export default function ProjectCard({
  id,
  projectTitle,
  projectImages,
  lastActivity,
  percentComplete,
  onClick
}) {
  return (
    <div
      className="flex items-center bg-gray-100 p-3 rounded-lg mb-2 cursor-pointer"
      onClick={() => onClick(id)}
    >
      <img
        src={projectImages?.[0] || '/placeholder.png'}
        alt=""
        className="w-16 h-16 object-cover rounded mr-3"
      />
      <div className="flex-1">
        <p className="font-semibold">{projectTitle}</p>
        <p className="text-sm text-gray-500">{lastActivity} ago</p>
        <p className="text-sm text-gray-500">{percentComplete}% completed</p>
      </div>
    </div>
  );
}
