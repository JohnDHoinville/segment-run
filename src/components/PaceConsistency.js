import React from 'react';
import 'chart.js/auto';
import './PaceProgressChart.css';

const PaceConsistency = ({ run }) => {
  // Make sure we have mile splits data
  if (!run || !run.data || !run.data.mile_splits || run.data.mile_splits.length < 3) {
    return null;
  }

  // Parse data if needed
  let mileSplits = run.data.mile_splits;
  if (typeof run.data === 'string') {
    try {
      const parsed = JSON.parse(run.data);
      mileSplits = parsed.mile_splits || [];
    } catch (e) {
      console.error("Failed to parse run data");
      return null;
    }
  }

  if (mileSplits.length < 3) return null;

  // Extract paces
  const paces = mileSplits.map(split => split.pace);
  
  // Calculate statistics
  const avgPace = paces.reduce((sum, pace) => sum + pace, 0) / paces.length;
  const variance = paces.reduce((sum, pace) => sum + Math.pow(pace - avgPace, 2), 0) / paces.length;
  const stdDev = Math.sqrt(variance);
  
  // Calculate coefficient of variation (lower is better)
  const cv = (stdDev / avgPace) * 100;
  
  // Calculate pace range
  const minPace = Math.min(...paces);
  const maxPace = Math.max(...paces);
  const paceRange = maxPace - minPace;
  
  // Calculate consistency score (0-100)
  const consistencyScore = Math.max(0, 100 - (cv * 10));
  
  // Format display values
  const formatPace = (pace) => {
    const mins = Math.floor(pace);
    const secs = Math.round((pace - mins) * 60);
    return `${mins}:${secs < 10 ? '0' + secs : secs}`;
  };
  
  // Determine rating
  let rating, ratingColor;
  if (consistencyScore >= 90) {
    rating = "Excellent";
    ratingColor = "#34c759"; // Green
  } else if (consistencyScore >= 80) {
    rating = "Good";
    ratingColor = "#5ac8fa"; // Blue
  } else if (consistencyScore >= 70) {
    rating = "Average";
    ratingColor = "#ffcc00"; // Yellow
  } else if (consistencyScore >= 60) {
    rating = "Fair";
    ratingColor = "#ff9500"; // Orange
  } else {
    rating = "Needs Work";
    ratingColor = "#ff3b30"; // Red
  }
  
  return (
    <div className="pace-consistency">
      <h3>Pace Consistency</h3>
      <p className="chart-subtitle">
        Analysis of pace variation during this run
      </p>
      
      <div className="consistency-score-container">
        <div className="consistency-score" style={{ 
          background: `conic-gradient(${ratingColor} ${consistencyScore}%, #e0e0e0 0)`
        }}>
          <div className="score-inner">
            <span>{Math.round(consistencyScore)}</span>
          </div>
        </div>
        <div className="score-details">
          <h4 style={{ color: ratingColor }}>{rating}</h4>
          <p>Your pacing consistency</p>
        </div>
      </div>
      
      <div className="metrics-row">
        <div className="metric-card">
          <div className="metric-value">{formatPace(avgPace)}</div>
          <div className="metric-label">Average Pace</div>
        </div>
        <div className="metric-card">
          <div className="metric-value">{formatPace(minPace)}</div>
          <div className="metric-label">Fastest Mile</div>
        </div>
        <div className="metric-card">
          <div className="metric-value">{formatPace(maxPace)}</div>
          <div className="metric-label">Slowest Mile</div>
        </div>
        <div className="metric-card">
          <div className="metric-value">{Math.round(cv)}%</div>
          <div className="metric-label">Variation</div>
        </div>
      </div>
      
      <div className="consistency-insights">
        <h4>What This Means</h4>
        <p>
          {consistencyScore >= 90 && "Your pacing is extremely consistent, indicating excellent pacing control."}
          {consistencyScore >= 80 && consistencyScore < 90 && "Your pacing is very good, with minor variations between miles."}
          {consistencyScore >= 70 && consistencyScore < 80 && "Your pacing shows moderate consistency, typical for most runners."}
          {consistencyScore >= 60 && consistencyScore < 70 && "Your pacing has notable variations that could be improved."}
          {consistencyScore < 60 && "Your pacing shows significant variations, suggesting opportunity for improvement."}
        </p>
        <p>
          A difference of {formatPace(paceRange)} between your fastest and slowest miles 
          {paceRange > 1.0 ? " is substantial and " : " "}
          suggests {paceRange > 1.0 ? "inconsistent pacing" : "good pacing strategy"}.
        </p>
      </div>
    </div>
  );
};

export default PaceConsistency; 