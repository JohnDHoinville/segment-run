import React from 'react';
import './LoadingSpinner.css';

function LoadingSpinner() {
  return (
    <div className="spinner-container">
      <div className="spinner"></div>
      <p>Analyzing run data...</p>
    </div>
  );
}

export default LoadingSpinner;