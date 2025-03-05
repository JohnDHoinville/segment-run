import React, { useMemo } from 'react';
import { Line } from 'react-chartjs-2';
import './PaceProgressChart.css';

// Helper function to extract pace limit from a run - moved outside useMemo
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

const PaceProgressChart = ({ runs, currentRun }) => {
  const similarRuns = useMemo(() => {
    if (!runs || !currentRun) return [];
    
    // Filter runs with similar target pace and distance (±10%)
    const targetPace = getPaceLimit(currentRun);
    const targetDistance = currentRun.total_distance;
    const distanceMargin = targetDistance * 0.1; // 10% margin
    
    // Debug what's being filtered
    console.log("Filtering similar runs:");
    console.log("Current run:", currentRun.id, "Distance:", targetDistance, "Target pace:", targetPace);
    
    return runs
      .filter(run => {
        // Get pace limit from the run (using similar logic as in RunHistory)
        let runPaceLimit = getPaceLimit(run);
        
        // Debug each run being considered
        console.log(
          "Run:", run.id, 
          "Distance:", run.total_distance, 
          "Pace:", run.avg_pace,
          "Target:", runPaceLimit, 
          "Date:", run.date
        );
        
        // Check if pace and distance are within range
        const hasPaceLimit = true; // We always have a pace limit now with our fallback
        const isPaceInRange = hasPaceLimit && Math.abs(Number(runPaceLimit) - Number(targetPace)) < 0.6;
        const isDistanceInRange = 
          run.total_distance >= targetDistance - distanceMargin && 
          run.total_distance <= targetDistance + distanceMargin;
        
        console.log(
          `Run ${run.id} matches:`, 
          `Has pace: ${hasPaceLimit}`,
          `Pace in range: ${isPaceInRange}`,
          `Distance in range: ${isDistanceInRange}`
        );
        
        return hasPaceLimit && isPaceInRange && isDistanceInRange;
      })
      .sort((a, b) => new Date(a.date) - new Date(b.date)); // Sort by date ascending
  }, [runs, currentRun]);
  
  // After the useMemo hook, let's add more logging
  console.log("Found similar runs:", similarRuns.length, similarRuns);
  
  // If no similar runs, don't render
  if (similarRuns.length <= 0) {
    return (
      <div className="pace-progress-empty">
        <p>Not enough similar runs to show pace improvement trend.</p>
        <p>Complete more runs with similar distance and target pace to see your progress.</p>
      </div>
    );
  }
  
  // Format dates for the chart
  const labels = similarRuns.map(run => new Date(run.date).toLocaleDateString());
  
  // Format pace values (convert to seconds for better visualization)
  const paceValues = similarRuns.map(run => run.avg_pace);
  
  // Chart data
  const data = {
    labels,
    datasets: [
      {
        label: 'Average Pace (min/mi)',
        data: paceValues,
        fill: false,
        borderColor: '#4c9aff',
        tension: 0.1,
        pointBackgroundColor: '#2a71d0',
        pointRadius: 4,
      }
    ]
  };
  
  // Options for the chart
  const options = {
    scales: {
      y: {
        reverse: true, // Lower pace (faster) is better, so reverse the scale
        title: {
          display: true,
          text: 'Pace (min/mi)'
        },
        ticks: {
          callback: function(value) {
            // Format pace in min:sec
            const mins = Math.floor(value);
            const secs = Math.round((value - mins) * 60);
            return `${mins}:${secs < 10 ? '0' + secs : secs}`;
          }
        }
      },
      x: {
        title: {
          display: true,
          text: 'Date'
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
            return `Pace: ${mins}:${secs < 10 ? '0' + secs : secs} min/mi`;
          }
        }
      },
      title: {
        display: true,
        text: 'Pace Improvement Over Time',
        font: {
          size: 18
        }
      }
    }
  };
  
  return (
    <div className="pace-progress-chart">
      <h3>Pace Improvement for Similar Runs</h3>
      <p className="chart-subtitle">
        Showing runs of {currentRun.total_distance.toFixed(1)} mi ±10% with target pace of
        {` ${Math.floor(getPaceLimit(currentRun))}:${Math.round((getPaceLimit(currentRun) % 1) * 60).toString().padStart(2, '0')}`} min/mi
      </p>
      <div className="chart-container">
        <Line data={data} options={options} />
      </div>
    </div>
  );
};

export default PaceProgressChart; 