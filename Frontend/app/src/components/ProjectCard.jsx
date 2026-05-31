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
  onRename, // New prop for rename functionality
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
        if (onRename) onRename();
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
    <div
      className="group relative flex min-h-[72px] select-none items-center justify-between overflow-hidden rounded-xl border-l-4 border-[#288AA5] bg-gray-100 shadow-md transition-all duration-200 ease-out hover:-translate-y-0.5 hover:bg-white hover:shadow-[0_14px_30px_-14px_rgba(20,132,163,0.65)] active:translate-y-0 active:scale-[0.995] focus-within:ring-2 focus-within:ring-[#1484A3]/30 lg:min-h-0 lg:rounded-[20px]"
      style={{
        boxShadow: '0 6px 12px -2px rgba(0, 0, 0, 0.1)',
      }}
    >
      <div className="pointer-events-none absolute inset-y-0 left-0 w-1 bg-[#1484A3] opacity-0 transition-opacity duration-200 group-hover:opacity-100" />
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-r from-[#E9FAFF]/80 via-transparent to-transparent opacity-0 transition-opacity duration-200 group-hover:opacity-100" />

      {/* Left Section - Image and Project Details - Clickable */}
      <div 
        className="relative z-[1] flex min-w-0 flex-1 cursor-pointer items-center gap-3 rounded-lg px-2 py-2 outline-none transition-transform duration-200 group-hover:translate-x-0.5 lg:gap-4 lg:px-4 lg:py-3"
        onClick={handleCardClick}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            handleCardClick();
          }
        }}
        role="button"
        tabIndex={0}
      >
        {/* Project Image */}
        <div className="h-11 w-11 flex-shrink-0 overflow-hidden rounded-lg bg-blue-50 shadow-sm ring-0 ring-[#1484A3]/20 transition-all duration-200 group-hover:scale-105 group-hover:ring-4 lg:h-16 lg:w-16">
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
        <div className="flex min-w-0 flex-col gap-0.5 pr-9 lg:pr-10">
          {/* Project Title - First line */}
          <h3 className="truncate text-[15px] font-semibold leading-5 text-gray-900 transition-colors duration-200 group-hover:text-[#066580] lg:text-[18px] lg:leading-6">
            {projectTitle}
          </h3>
          {/* Last Activity - Second line */}
          <span className="text-[12px] leading-4 text-gray-500 lg:text-[15px] lg:leading-5">
            {formatLastActivity(lastActivity)}
          </span>
          {/* Completion Status - Third line */}
          <span className="text-[12px] leading-4 text-gray-500 lg:text-[15px] lg:leading-5">
            {percentComplete || 0}% completed
          </span>
        </div>
      </div>

      {/* Right Section - Three-dot menu with dropdown - Not clickable for navigation */}
      <div className="flex items-center flex-shrink-0">
        <button
          onClick={handleMenuClick}
          className="absolute right-1.5 top-1.5 z-[2] rounded-lg p-2 text-black transition-colors hover:bg-[#E9FAFF] hover:text-[#066580] focus:outline-none focus:ring-2 focus:ring-[#1484A3]/30 lg:right-3 lg:top-3"
          title="More options"
        >
          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
            <path d="M6 10a2 2 0 11-4 0 2 2 0 014 0zM12 10a2 2 0 11-4 0 2 2 0 014 0zM18 10a2 2 0 11-4 0 2 2 0 014 0z" />
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
                Resume
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
                className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition-colors"
              >
                Rename
              </button>
              {/* <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleOptionClick('archive');
                }}
                className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition-colors cursor-not-allowed opacity-50"
                disabled
              >
                Archive
              </button> */}
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
