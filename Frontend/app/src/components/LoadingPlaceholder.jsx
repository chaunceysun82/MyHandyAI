// src/components/LoadingPlaceholder.jsx
import React from 'react';

export default function LoadingPlaceholder() {
  return (
    <div className="p-4 h-screen">
      <div className="animate-pulse bg-gray-200 h-8 mb-4 rounded" />
      {[...Array(4)].map((_, i) => (
        <div key={i} className="flex items-center animate-pulse bg-gray-200 h-20 mb-2 rounded" />
      ))}
    </div>
  );
}
