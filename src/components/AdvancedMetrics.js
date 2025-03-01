import React from 'react';
import './AdvancedMetrics.css';

const AdvancedMetrics = ({ vo2max, trainingLoad, recoveryTime }) => {
  return (
    <div className="advanced-metrics">
      <h3>Advanced Metrics</h3>
      <div className="metrics-grid">
        <div className="metric-item">
          <h4>Estimated VO2 Max</h4>
          <p className="metric-value">{vo2max ? (vo2max + " ml/kg/min") : "Available with heart rate data"}</p>
          {vo2max && <p className="metric-unit">ml/kg/min</p>}
        </div>
        <div className="metric-item">
          <h4>Training Load</h4>
          <p className="metric-value">{trainingLoad ? trainingLoad : "Available with heart rate data"}</p>
          {trainingLoad && <p className="metric-unit">TRIMP</p>}
        </div>
        <div className="metric-item">
          <h4>Recovery Time</h4>
          <p className="metric-value">
            {recoveryTime 
              ? (Math.floor(recoveryTime) + "h " + Math.round((recoveryTime % 1) * 60) + "m")
              : "Available with heart rate data"}
          </p>
          {recoveryTime && <p className="metric-unit">hours</p>}
        </div>
      </div>
    </div>
  );
};

export default AdvancedMetrics; 