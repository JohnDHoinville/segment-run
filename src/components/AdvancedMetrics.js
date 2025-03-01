import React from 'react';
import './AdvancedMetrics.css';

const AdvancedMetrics = ({ vo2max, trainingLoad, recoveryTime }) => {
  return (
    <div className="advanced-metrics">
      <h3>Advanced Metrics</h3>
      <div className="metrics-grid">
        <div className="metric-card">
          <h4>VO2 Max</h4>
          <p className="metric-value">{vo2max ? vo2max.toFixed(1) : 'N/A'}</p>
          <p className="metric-unit">ml/kg/min</p>
          <p className="metric-description">
            Estimated maximum oxygen uptake capacity
          </p>
        </div>

        <div className="metric-card">
          <h4>Training Load</h4>
          <p className="metric-value">
            {trainingLoad ? Math.round(trainingLoad) : 'N/A'}
          </p>
          <p className="metric-unit">TRIMP</p>
          <p className="metric-description">
            Training load based on duration and intensity
          </p>
        </div>

        <div className="metric-card">
          <h4>Recovery Time</h4>
          <p className="metric-value">
            {recoveryTime ? Math.round(recoveryTime * 10) / 10 : 'N/A'}
          </p>
          <p className="metric-unit">hours</p>
          <p className="metric-description">
            Recommended recovery time before next hard workout
          </p>
        </div>
      </div>
    </div>
  );
};

export default AdvancedMetrics; 