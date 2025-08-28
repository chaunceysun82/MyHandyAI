// src/components/ProjectCard.jsx
import React, { useState } from "react";
import defaultProjectImage from "../assets/default-project.png";

export default function ProjectCard({
  id,
  projectTitle,
  lastActivity,
  percentComplete,
  onStartChat,
  onRemove,
  onComplete,
  hasSteps = false, // New prop to check if project has steps generated
}) {
  const [showMenu, setShowMenu] = useState(false);
  const [isCompleting, setIsCompleting] = useState(false);

  console.log("Propject percentage", Number(percentComplete));

  const formatLastActivity = (dateString) => {
    if (!dateString) return "Just now";
    const date = new Date(dateString);
    const now = new Date();
    const diffTime = Math.abs(now - date);
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    
    if (diffDays === 1) return "1 day ago";
    if (diffDays < 7) return `${diffDays} days ago`;
    if (diffDays < 30) return `${Math.ceil(diffDays / 7)} weeks ago`;
    return `${Math.ceil(diffDays / 30)} months ago`;
  };

  const handleMenuClick = (e) => {
    e.stopPropagation();
    setShowMenu(!showMenu);
  };

  const handleOptionClick = async (option) => {
    setShowMenu(false);
    
    switch (option) {
      case 'chat':
        if (onStartChat) onStartChat();
        break;
      case 'complete':
        if (onComplete && hasSteps) {
          setIsCompleting(true);
          try {
            await onComplete(id);
          } catch (error) {
            console.error('Error completing project:', error);
          } finally {
            setIsCompleting(false);
          }
        }
        break;
      case 'delete':
        if (onRemove) onRemove(id);
        break;
      case 'rename':
        console.log('Rename functionality not implemented');
        break;
      case 'archive':
        console.log('Archive functionality not implemented');
        break;
      default:
        break;
    }
  };

  const handleCardClick = () => {
    if (onStartChat) onStartChat();
  };

  // Check if project can be completed
  const canComplete = hasSteps && percentComplete < 100;

  return (
    <div className="bg-gray-100 rounded-xl flex items-center justify-between relative">
      {/* Left Section - Image and Project Details - Clickable */}
      <div 
        className="flex items-center space-x-4 flex-1 cursor-pointer rounded-lg p-1"
        onClick={handleCardClick}
      >
        {/* Project Image */}
        <div className="w-14 h-14 mx-2 bg-blue-50 rounded-lg flex items-center justify-center shadow-sm overflow-hidden flex-shrink-0">
          <img 
            src={defaultProjectImage} 
            alt="Project" 
            className="w-full h-full object-cover"
            onError={(e) => {
              e.target.style.display = 'none';
              e.target.nextSibling.style.display = 'flex';
            }}
          />
          {/* Fallback icon if image fails */}
          <div className="w-full h-full bg-gray-200 flex items-center justify-center hidden">
            <span className="text-gray-500 text-lg">🏠</span>
          </div>
        </div>
        
        {/* Project Details - Three lines as shown in image */}
        <div className="flex flex-col space-y-1">
          {/* Project Title - First line */}
          <h3 className="text-base font-semibold text-gray-900">
            {projectTitle}
          </h3>
          {/* Last Activity - Second line */}
          <span className="text-sm text-gray-500">
            {formatLastActivity(lastActivity)}
          </span>
          {/* Completion Status - Third line */}
          <span className="text-sm text-gray-500">
            {percentComplete || 0}% completed
          </span>
        </div>
      </div>

      {/* Right Section - Three-dot menu with dropdown - Not clickable for navigation */}
      <div className="flex items-center flex-shrink-0">
        <button
          onClick={handleMenuClick}
          className="p-2 text-gray-600 hover:text-gray-800 hover:bg-gray-200 rounded-lg transition-colors"
          title="More options"
        >
          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
            <path d="M10 6a2 2 0 110-4 2 2 0 010 4zM10 12a2 2 0 110-4 2 2 0 010 4zM10 18a2 2 0 110-4 2 2 0 010 4z" />
          </svg>
        </button>

        {/* Dropdown Menu */}
        {showMenu && (
          <div className="absolute right-0 top-full mt-2 w-36 bg-white rounded-lg shadow-lg border border-gray-200 z-10">
            <div className="py-1">
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleOptionClick('chat');
                }}
                className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition-colors"
              >
                Chat
              </button>
              
              {/* Complete option - only show if project has steps and isn't already complete */}
              {canComplete && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleOptionClick('complete');
                  }}
                  disabled={isCompleting}
                  className={`w-full text-left px-4 py-2 text-sm transition-colors ${
                    isCompleting 
                      ? 'text-gray-400 cursor-not-allowed' 
                      : 'text-green-600 hover:bg-green-50'
                  }`}
                >
                  {isCompleting ? 'Completing...' : 'Complete'}
                </button>
              )}
              
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleOptionClick('rename');
                }}
                className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition-colors cursor-not-allowed opacity-50"
                disabled
              >
                Rename
              </button>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleOptionClick('archive');
                }}
                className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition-colors cursor-not-allowed opacity-50"
                disabled
              >
                Archive
              </button>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleOptionClick('delete');
                }}
                className="w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-red-50 transition-colors"
              >
                Delete
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Click outside to close menu */}
      {showMenu && (
        <div 
          className="fixed inset-0 z-0" 
          onClick={() => setShowMenu(false)}
        />
      )}
    </div>
  );
}
