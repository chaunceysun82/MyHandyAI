import React from "react";

const QuickReplyButtons = ({ onQuickReply, suggestedMessages = [] }) => {
  // Use suggested messages from backend, fallback to default if none provided
  const quickReplies = suggestedMessages.length > 0 ? suggestedMessages : [
    "Skip this question?",
    "How do I answer this question",
    "Is this a required question",
    "I don't know how to answer this",
  ];

  return (
    <div className="mb-1 relative">
      {/* Horizontal scroll container */}
      <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-hide scroll-smooth">
        {quickReplies.map((reply, index) => (
          <button
            key={index}
            onClick={() => onQuickReply(reply)}
            className="py-1 px-2 text-xs bg-[#E9FAFF] hover:bg-[#d2f4fc] text-gray-700 rounded-md border border-gray-200 transition-colors duration-200 hover:border-gray-300 whitespace-nowrap flex-shrink-0"
          >
            {reply}
          </button>
        ))}
      </div>
      
      {/* Subtle scroll indicator */}
      <div className="absolute right-0 top-0 bottom-0 w-4 bg-gradient-to-l from-white to-transparent pointer-events-none"></div>
    </div>
  );
};

export default QuickReplyButtons;
