import React from 'react';
import { Line } from 'react-chartjs-2';
import 'chart.js/auto';
import './PaceProgressChart.css';

const FatigueAnalysis = ({ run }) => {
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

  // Extract mile numbers and paces
  const miles = mileSplits.map((split, i) => i + 1);
  const paces = mileSplits.map(split => split.pace);

  // Calculate best fit line (linear regression)
  const n = miles.length;
  let sumX = 0, sumY = 0, sumXY = 0, sumX2 = 0;
  
  for (let i = 0; i < n; i++) {
    sumX += miles[i];
    sumY += paces[i];
    sumXY += miles[i] * paces[i];
    sumX2 += miles[i] * miles[i];
  }
  
  const slope = (n * sumXY - sumX * sumY) / (n * sumX2 - sumX * sumX);
  const intercept = (sumY - slope * sumX) / n;
  
  // Generate trend line points
  const trendline = miles.map(mile => intercept + slope * mile);
  
  // Calculate fatigue rate (slope as percentage)
  const avgPace = sumY / n;
  const fatigueRate = (slope / avgPace) * 100;
  
  // Prepare chart data
  const data = {
    labels: miles,
    datasets: [
      {
        label: 'Actual Pace',
        data: paces,
        fill: false,
        borderColor: '#4c9aff',
        tension: 0.3,
        pointBackgroundColor: '#2a71d0',
        pointRadius: 4,
      },
      {
        label: 'Pace Trend',
        data: trendline,
        fill: false,
        borderColor: '#ff6b6b',
        borderDash: [5, 5],
        tension: 0,
        pointRadius: 0,
      }
    ]
  };
  
  // Chart options
  const options = {
    scales: {
      y: {
        reverse: true, // Lower pace is better
        title: {
          display: true,
          text: 'Pace (min/mi)'
        },
        ticks: {
          callback: function(value) {
            const mins = Math.floor(value);
            const secs = Math.round((value - mins) * 60);
            return `${mins}:${secs < 10 ? '0' + secs : secs}`;
          }
        }
      },
      x: {
        title: {
          display: true,
          text: 'Mile'
        }
      }
    },
    plugins: {
      tooltip: {
        callbacks: {
          label: function(context) {
            const pace = context.raw;
            const mins = Math.floor(pace);
            const secs = Math.round((pace - mins) * 60);
            return `${context.dataset.label}: ${mins}:${secs < 10 ? '0' + secs : secs} min/mi`;
          }
        }
      },
      title: {
        display: true,
        text: 'Pace Degradation Analysis',
        font: { size: 16 }
      }
    }
  };
  
  // Format date
  const runDate = new Date(run.date).toLocaleDateString();
  
  return (
    <div className="fatigue-analysis">
      <h3>Fatigue Analysis</h3>
      <p className="chart-subtitle">
        {runDate} · {run.total_distance.toFixed(1)} miles · {slope > 0 ? 'Slowing' : 'Speeding up'} {Math.abs(fatigueRate).toFixed(1)}% per mile
      </p>
      
      <div className="metrics-row">
        <div className="metric-card">
          <div className="metric-value">{fatigueRate > 0 ? 
            `+${fatigueRate.toFixed(1)}%` : 
            `${fatigueRate.toFixed(1)}%`}</div>
          <div className="metric-label">Pace Change/Mile</div>
        </div>
        <div className="metric-card">
          <div className="metric-value">{((paces[paces.length-1] - paces[0]) / paces[0] * 100).toFixed(1)}%</div>
          <div className="metric-label">Total Pace Change</div>
        </div>
        <div className="metric-card">
          <div className="metric-value">
            {Math.abs(paces[paces.length-1] - paces[0]).toFixed(2)}
          </div>
          <div className="metric-label">Pace Difference</div>
        </div>
      </div>
      
      <div className="chart-container">
        <Line data={data} options={options} />
      </div>
      
      <div className="fatigue-insights">
        <h4>Insights</h4>
        <ul>
          {fatigueRate > 3 && (
            <li>Your pace slows significantly over distance, suggesting endurance issues</li>
          )}
          {fatigueRate > 0 && fatigueRate <= 3 && (
            <li>Your pace slows moderately, which is common during longer runs</li>
          )}
          {fatigueRate <= 0 && (
            <li>Your pace improves throughout the run, showing strong pacing strategy</li>
          )}
          {Math.abs(paces[Math.floor(paces.length/2)] - avgPace) / avgPace > 0.05 && (
            <li>Your pacing is inconsistent, with significant variations between miles</li>
          )}
        </ul>
      </div>
    </div>
  );
};

export default FatigueAnalysis; 