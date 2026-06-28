// src/components/LoadingPlaceholder.jsx
import React from 'react';
import defaultNavLogo from "../assets/default_nav_logo.png";

export default function LoadingPlaceholder() {
  return (
    <div className="auth-transition-screen">
      <div className="auth-logo-loader" role="status" aria-live="polite">
        <img
          src={defaultNavLogo}
          alt="MyHandyAI"
          className="auth-logo-loader__image"
        />
        <span className="sr-only">Loading</span>
      </div>
    </div>
  );
}
