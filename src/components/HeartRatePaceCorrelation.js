import React from 'react';
import { Scatter } from 'react-chartjs-2';
import 'chart.js/auto';  // Ensure all Chart.js components are registered
import './PaceProgressChart.css';

// Import the helper function
const getPaceLimit = (run) => {
  if (run.pace_limit && run.pace_limit > 0) {
    return run.pace_limit;
  }
  // Try to get it from data object
  if (run.data && typeof run.data === 'object' && run.data.pace_limit) {
    return run.data.pace_limit;
  }
  // Try to parse data if it's a string
  if (run.data && typeof run.data === 'string') {
    try {
      const parsed = JSON.parse(run.data);
      if (parsed.pace_limit) return parsed.pace_limit;
    } catch (e) {
      // Failed to parse, ignore
    }
  }
  return 10; // Default fallback
};

const HeartRatePaceCorrelation = ({ runs, currentRun }) => {
  // Filter to similar runs as in the pace chart
  const similarRuns = runs.filter(run => {
    const targetDistance = currentRun.total_distance;
    const distanceMargin = targetDistance * 0.1;
    const targetPace = getPaceLimit(currentRun);
    const runPaceLimit = getPaceLimit(run);
    
    return Math.abs(Number(runPaceLimit) - Number(targetPace)) < 0.6 &&
      run.total_distance >= targetDistance - distanceMargin &&
      run.total_distance <= targetDistance + distanceMargin;
  });
  
  // Skip if no HR data or fewer than 2 runs
  if (similarRuns.length < 2 || !similarRuns.some(run => run.avg_hr > 0)) {
    return null;
  }
  
  // Prepare scatter plot data
  const scatterData = similarRuns
    .filter(run => run.avg_hr > 0) // Only include runs with HR data
    .map(run => ({
      x: run.avg_pace,
      y: run.avg_hr,
      label: new Date(run.date).toLocaleDateString()
    }));
  
  const data = {
    datasets: [{
      label: 'Heart Rate vs. Pace',
      data: scatterData,
      backgroundColor: 'rgba(255, 99, 132, 0.7)',
      borderColor: 'rgba(255, 99, 132, 1)',
      pointRadius: 6,
      pointHoverRadius: 10,
    }]
  };
  
  const options = {
    scales: {
      x: {
        type: 'linear',
        position: 'bottom',
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
      y: {
        title: {
          display: true,
          text: 'Heart Rate (bpm)'
        }
      }
    },
    plugins: {
      tooltip: {
        callbacks: {
          label: function(context) {
            const item = context.raw;
            const pace = item.x;
            const mins = Math.floor(pace);
            const secs = Math.round((pace - mins) * 60);
            return [
              `Date: ${item.label}`,
              `Pace: ${mins}:${secs < 10 ? '0' + secs : secs} min/mi`,
              `Heart Rate: ${Math.round(item.y)} bpm`
            ];
          }
        }
      },
      title: {
        display: true,
        text: 'Heart Rate vs. Pace Correlation',
        font: { size: 16 }
      }
    }
  };
  
  return (
    <div className="hr-pace-correlation">
      <h3>Heart Rate & Pace Relationship</h3>
      <p className="chart-subtitle">See how your heart rate changes with pace over time</p>
      <div className="chart-container">
        <Scatter data={data} options={options} />
      </div>
    </div>
  );
};

export default HeartRatePaceCorrelation; 