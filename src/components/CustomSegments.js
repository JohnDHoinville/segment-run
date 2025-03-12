import React, { useState, useEffect } from 'react';
import { Line } from 'react-chartjs-2';
import './CustomSegments.css';

const CustomSegments = ({ runs, currentRun }) => {
  console.log("CustomSegments component rendering", { runs: runs?.length, currentRun });
  const [segments, setSegments] = useState([]);
  const [name, setName] = useState('');
  const [startDistance, setStartDistance] = useState(0);
  const [endDistance, setEndDistance] = useState(1);
  const [activeSegment, setActiveSegment] = useState(null);
  const [segmentResults, setSegmentResults] = useState(null);

  // Add a safe JSON stringify helper function
  const safeStringify = (obj) => {
    return JSON.stringify(obj, (key, value) => {
      // Handle Infinity, -Infinity and NaN
      if (typeof value === 'number' && !isFinite(value)) {
        if (value === Infinity) return "Infinity";
        if (value === -Infinity) return "-Infinity";
        return null; // NaN becomes null
      }
      return value;
    });
  };

  // Add a safe JSON parse helper function
  const safeParse = (jsonString) => {
    try {
      return JSON.parse(jsonString, (key, value) => {
        // Convert back from string to actual values
        if (value === "Infinity") return Infinity;
        if (value === "-Infinity") return -Infinity;
        return value;
      });
    } catch (e) {
      console.error("Error parsing JSON:", e);
      return null;
    }
  };

  // Load saved segments from localStorage
  useEffect(() => {
    try {
      const savedSegments = localStorage.getItem('customSegments');
      console.log("Loading saved segments:", savedSegments);
      
      if (savedSegments) {
        const parsed = safeParse(savedSegments);
        
        if (Array.isArray(parsed) && parsed.length > 0) {
          console.log("Found saved segments:", parsed.length);
          setSegments(parsed);
        } else {
          console.log("No valid segments found, adding demo segments");
          createDemoSegments();
        }
      } else {
        console.log("No segments in localStorage, adding demo segments");
        createDemoSegments();
      }
    } catch (error) {
      console.error("Error loading segments:", error);
      createDemoSegments();
    }
  }, [currentRun?.total_distance]);

  // Save segments to localStorage when they change
  useEffect(() => {
    localStorage.setItem('customSegments', safeStringify(segments));
  }, [segments]);

  const handleAddSegment = (e) => {
    e.preventDefault();
    if (!name.trim()) return;
    
    const newSegment = {
      id: Date.now(),
      name: name.trim(),
      startDistance: parseFloat(startDistance),
      endDistance: parseFloat(endDistance)
    };
    
    const updatedSegments = [...segments, newSegment];
    setSegments(updatedSegments);
    
    // Force save to localStorage immediately
    localStorage.setItem('customSegments', safeStringify(updatedSegments));
    
    // Reset form
    setName('');
    setStartDistance(0);
    setEndDistance(1);
    
    console.log("Added new segment:", newSegment);
    console.log("Updated segments in storage:", updatedSegments);
  };

  const handleDeleteSegment = (id) => {
    // First check if this is the active segment
    if (activeSegment && activeSegment.id === id) {
      setActiveSegment(null);
      setSegmentResults(null);
    }
    
    const updatedSegments = segments.filter(segment => segment.id !== id);
    setSegments(updatedSegments);
    
    // Force save to localStorage immediately
    localStorage.setItem('customSegments', safeStringify(updatedSegments));
    
    console.log("Deleted segment ID:", id);
    console.log("Remaining segments:", updatedSegments);
  };

  const analyzeSegment = (segment) => {
    setActiveSegment(segment);
    
    // Debug the data structure
    console.log("Analyzing segment:", segment);
    console.log("Current run data structure:", currentRun?.data);
    
    // Changed filter criteria: The run just needs to cover the start of the segment
    // (instead of requiring it to cover the entire end distance)
    const validRuns = runs.filter(run => 
      run.total_distance >= segment.startDistance + 0.5 // Just need to cover 0.5 miles into the segment
    );
    
    console.log("Found valid runs by distance:", validRuns.length);
    
    if (validRuns.length < 1) {
      setSegmentResults({
        error: "No runs with sufficient data cover this segment. Try creating a segment with a shorter distance."
      });
      return;
    }
    
    // Extract the relevant segment data from each run
    const results = validRuns.map(run => {
      // Always add estimated flag to track when we're estimating vs using real mile splits
      let estimated = false;
      
      // Get mile splits or point data to analyze the segment
      let segmentData = run.data?.mile_splits || [];
      let parsed = null;
      
      // Try to parse the data if it's a string
      if (typeof run.data === 'string') {
        try {
          parsed = JSON.parse(run.data);
          segmentData = parsed.mile_splits || [];
        } catch (e) {
          estimated = true;
          console.error("Failed to parse run data:", e);
          segmentData = [];
        }
      } else if (run.data && typeof run.data === 'object') {
        parsed = run.data;
        if (Array.isArray(run.data.mile_splits)) {
          segmentData = run.data.mile_splits;
        }
      }
      
      console.log(`Run ${run.id} mile splits:`, segmentData.length);
      
      // If we have no mile splits but do have an overall pace, we can estimate the segment
      if (segmentData.length === 0 || segmentData.length < segment.endDistance) {
        estimated = true;
        console.log(`Run ${run.id} using estimated data from overall pace`);
        
        // Calculate segment distance
        const segmentDistanceValue = Math.min(segment.endDistance, run.total_distance) - segment.startDistance;
        
        // If the segment is beyond the run distance, skip this run
        if (segmentDistanceValue <= 0) {
          return null;
        }
        
        return {
          id: run.id,
          date: run.date,
          distance: segmentDistanceValue.toFixed(2),
          pace: run.avg_pace || 10, // Use the overall run pace
          avgHR: run.avg_hr || 0,
          estimated: true // Mark this as estimated data
        };
      }
      
      // Normal path for runs with mile splits data
      // Calculate segment performance based on mile splits
      let segmentDistance = Math.min(segment.endDistance, segmentData.length) - segment.startDistance;
      
      // If the segment starts beyond our mile splits data, skip this run
      if (segmentDistance <= 0) {
        return null;
      }
      
      let segmentTime = 0;
      let totalHR = 0;
      let hrCount = 0;
      
      // Sum up the time for each mile in the segment
      for (let mile = Math.floor(segment.startDistance); mile < Math.min(Math.ceil(segment.endDistance), segmentData.length); mile++) {
        const split = segmentData[mile];
        if (!split) continue;
        
        // For first and last mile, we need to calculate partial miles
        let mileContribution = 1.0; // Full mile by default
        
        if (mile === Math.floor(segment.startDistance)) {
          // First mile - only count the fraction
          mileContribution = 1 - (segment.startDistance - mile);
        }
        
        if (mile === Math.floor(segment.endDistance) && segment.endDistance < segmentData.length) {
          // Last mile - only count the fraction
          mileContribution = segment.endDistance - Math.floor(segment.endDistance);
        }
        
        segmentTime += split.pace * mileContribution;
        
        if (split.avg_hr) {
          totalHR += split.avg_hr * mileContribution;
          hrCount += mileContribution;
        }
      }
      
      // When calculating final pace, check for invalid values
      if (segmentDistance <= 0 || !isFinite(segmentDistance) || segmentTime <= 0 || !isFinite(segmentTime)) {
        // If we have invalid values, use the overall run pace as a fallback
        console.log(`Run ${run.id} has invalid segment data, using overall pace as estimate`);
        return {
          id: run.id,
          date: run.date,
          distance: segment.endDistance - segment.startDistance,
          pace: run.avg_pace || 10, // Fallback to overall pace or default
          avgHR: run.avg_hr || 0,
          estimated: true // Mark as estimated
        };
      }
      
      // Calculate average pace and HR for the segment
      const segmentPace = segmentTime / segmentDistance;
      
      // Validate the calculated pace
      const validPace = isFinite(segmentPace) && segmentPace > 0 ? segmentPace : run.avg_pace || 10;
      
      const segmentHR = hrCount > 0 ? totalHR / hrCount : 0;
      
      return {
        id: run.id,
        date: run.date,
        distance: parseFloat(segmentDistance.toFixed(2)),
        pace: validPace,
        avgHR: segmentHR > 0 ? segmentHR : 0,
        estimated: estimated
      };
    });
    
    // Filter out null results and sort by date
    const validResults = results.filter(r => r !== null);
    const sortedResults = validResults.sort((a, b) => new Date(a.date) - new Date(b.date));
    
    console.log("Final segment results:", sortedResults);

    if (sortedResults.length === 0) {
      setSegmentResults({
        error: "No runs with valid data could be analyzed for this segment."
      });
      return;
    }
    
    // Format values for display
    const formatPace = (pace) => {
      // Handle invalid values
      if (!isFinite(pace) || pace <= 0) {
        return "N/A";
      }
      
      const mins = Math.floor(pace);
      const secs = Math.round((pace - mins) * 60);
      return `${mins}:${secs < 10 ? '0' + secs : secs}`;
    };

    // Prepare chart data
    const chartData = {
      labels: sortedResults.map(result => new Date(result.date).toLocaleDateString()),
      datasets: [
        {
          label: 'Segment Pace',
          data: sortedResults.map(result => {
            // Ensure pace values are valid numbers for the chart
            const pace = result.pace;
            return isFinite(pace) && pace > 0 ? pace : null;
          }),
          fill: false,
          borderColor: '#4c9aff',
          backgroundColor: 'rgba(76, 154, 255, 0.5)',
          tension: 0.3,
          pointRadius: 5,
          pointStyle: sortedResults.map(result => result.estimated ? 'triangle' : 'circle'),
          pointBackgroundColor: sortedResults.map(result => result.estimated ? '#ff9500' : '#4c9aff')
        }
      ]
    };

    // Chart options
    const chartOptions = {
      scales: {
        y: {
          reverse: true, // Lower pace is better
          title: {
            display: true,
            text: 'Pace (min/mi)'
          },
          ticks: {
            callback: function(value) {
              return formatPace(value);
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
              const result = sortedResults[context.dataIndex];
              return [
                result.estimated ? '⚠️ Estimated from overall pace' : 'Segment Pace',
                `Pace: ${formatPace(result.pace)}`,
                `Distance: ${result.distance} mi`,
                result.avgHR > 0 ? `Heart Rate: ${Math.round(result.avgHR)} bpm` : 'No HR data'
              ];
            }
          }
        },
        legend: {
          display: false
        }
      }
    };

    setSegmentResults({
      results: sortedResults,
      chartData,
      chartOptions
    });
  };
  
  // Format pace
  const formatPace = (pace) => {
    // Handle invalid values
    if (!isFinite(pace) || pace <= 0) {
      return "N/A";
    }
    
    const mins = Math.floor(pace);
    const secs = Math.round((pace - mins) * 60);
    return `${mins}:${secs < 10 ? '0' + secs : secs}`;
  };
  
  // Prepare chart data if we have segment results
  const chartData = segmentResults?.results ? {
    labels: segmentResults.results.map(result => new Date(result.date).toLocaleDateString()),
    datasets: [
      {
        label: 'Segment Pace',
        data: segmentResults.results.map(result => result.pace),
        fill: false,
        borderColor: '#4c9aff',
        tension: 0.1
      }
    ]
  } : null;
  
  const chartOptions = {
    scales: {
      y: {
        reverse: true,
        title: {
          display: true,
          text: 'Pace (min/mi)'
        },
        ticks: {
          callback: function(value) {
            return formatPace(value);
          }
        }
      }
    },
    plugins: {
      tooltip: {
        callbacks: {
          label: function(context) {
            return `Pace: ${formatPace(context.raw)}`;
          }
        }
      }
    }
  };
  
  // Helper function to create demo segments
  const createDemoSegments = () => {
    const demoSegments = [
      {
        id: Date.now(),
        name: "First Mile",
        startDistance: 0,
        endDistance: 1
      },
      {
        id: Date.now() + 1,
        name: "Last Mile",
        startDistance: Math.max(0, Math.floor(currentRun?.total_distance || 3) - 1),
        endDistance: Math.floor(currentRun?.total_distance || 3)
      },
      {
        id: Date.now() + 2,
        name: "Middle Section",
        startDistance: 1,
        endDistance: 2
      }
    ];
    setSegments(demoSegments);
    localStorage.setItem('customSegments', safeStringify(demoSegments));
    console.log("Created and saved demo segments:", demoSegments);
  }
  
  return (
    <div className="custom-segments">
      <h3>Custom Segments</h3>
      <p className="chart-subtitle">Define and analyze specific portions of your routes</p>
      
      <div className="segments-container">
        <div className="segments-list">
          <form onSubmit={handleAddSegment} className="add-segment-form">
            <h4>Create New Segment</h4>
            <div className="form-group">
              <label>Segment Name:</label>
              <input 
                type="text" 
                value={name} 
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g., Hill Section" 
                required
              />
            </div>
            
            <div className="form-group">
              <label>Start Distance (miles):</label>
              <input 
                type="number" 
                value={startDistance} 
                onChange={(e) => setStartDistance(e.target.value)}
                min="0" 
                step="0.1" 
                required
              />
            </div>
            
            <div className="form-group">
              <label>End Distance (miles):</label>
              <input 
                type="number" 
                value={endDistance} 
                onChange={(e) => setEndDistance(e.target.value)}
                min={parseFloat(startDistance) + 0.1}
                step="0.1" 
                required
              />
            </div>
            
            <button type="submit">Add Segment</button>
          </form>
          
          <div className="saved-segments">
            <h4>Saved Segments</h4>
            {segments.length === 0 ? (
              <p className="no-segments">No segments defined yet.</p>
            ) : (
              <ul>
                {segments.map(segment => (
                  <li 
                    key={segment.id} 
                    className={activeSegment?.id === segment.id ? 'active' : ''}
                    onClick={() => analyzeSegment(segment)}
                  >
                    <div className="segment-info">
                      <span className="segment-name">{segment.name}</span>
                      <span className="segment-range">
                        {segment.startDistance} - {segment.endDistance} mi
                      </span>
                    </div>
                    <button 
                      className="delete-btn"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDeleteSegment(segment.id);
                      }}
                    >
                      🗑️
                    </button>
                  </li>
                ))}
              </ul>
            )}
            
            {segments.length > 0 && !activeSegment && (
              <button 
                className="analyze-btn"
                onClick={() => analyzeSegment(segments[0])}
              >
                Analyze First Segment
              </button>
            )}
          </div>
        </div>
        
        <div className="segment-analysis">
          {!activeSegment && (
            <div className="no-segment-selected">
              <div className="empty-state">
                <div className="empty-icon">📏</div>
                <h4>Select a Segment to Analyze</h4>
                <p>Create custom segments to track specific portions of your runs over time.</p>
                <p className="tip">Try creating segments for hills, intervals, or the final push!</p>
              </div>
            </div>
          )}
          
          {activeSegment && !segmentResults && (
            <div className="segment-loading">
              <div className="spinner-small"></div>
              <p>Analyzing segment data...</p>
            </div>
          )}
          
          {activeSegment && segmentResults?.error && (
            <div className="segment-error">
              <p>{segmentResults.error}</p>
            </div>
          )}
          
          {activeSegment && !segmentResults?.error && (
            <div className="segment-results">
              <h4>{activeSegment.name} Analysis</h4>
              <p className="segment-description">
                Showing pace trends for miles {activeSegment.startDistance} - {activeSegment.endDistance}
              </p>
              
              {chartData && (
                <div className="segment-chart">
                  <Line data={chartData} options={chartOptions} />
                </div>
              )}
              
              <div className="segment-details">
                <h4>Run Details</h4>
                <table>
                  <thead>
                    <tr>
                      <th>Date</th>
                      <th>Distance</th>
                      <th>Pace</th>
                      <th>Heart Rate</th>
                    </tr>
                  </thead>
                  <tbody>
                    {segmentResults.results.map((result, i) => (
                      <tr key={i}>
                        <td>{new Date(result.date).toLocaleDateString()}</td>
                        <td>{result.distance} mi</td>
                        <td>
                          {formatPace(result.pace)} 
                          {result.estimated && <span className="estimated-marker" title="Estimated from overall pace">*</span>}
                        </td>
                        <td>{result.avgHR ? Math.round(result.avgHR) + ' bpm' : 'N/A'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              
              {segmentResults.results.some(r => r.estimated) && (
                <div className="segment-legend">
                  * Estimated from overall run pace (mile split data not available)
                </div>
              )}
            </div>
          )}
        </div>
      </div>
      
      {process.env.NODE_ENV === 'development' && (
        <div className="debug-actions" style={{marginTop: '20px', borderTop: '1px solid #eee', paddingTop: '10px'}}>
          <button 
            onClick={() => {
              const stored = localStorage.getItem('customSegments');
              console.log("Current localStorage segments:", stored);
              console.log("Parsed:", stored ? safeParse(stored) : []);
              console.log("Current state segments:", segments);
            }}
            style={{fontSize: '12px', padding: '4px 8px'}}
          >
            Debug Segments
          </button>
          <button 
            onClick={() => {
              // Force re-sync segments from localStorage
              const savedSegments = localStorage.getItem('customSegments');
              if (savedSegments) {
                const parsed = safeParse(savedSegments);
                setSegments(parsed);
                console.log("Re-synced segments from localStorage:", parsed);
              }
            }}
            style={{fontSize: '12px', padding: '4px 8px', marginLeft: '8px'}}
          >
            Sync from Storage
          </button>
          <button 
            onClick={() => {
              // Force save current segments to localStorage
              localStorage.setItem('customSegments', safeStringify(segments));
              console.log("Forced save to localStorage:", segments);
            }}
            style={{fontSize: '12px', padding: '4px 8px', marginLeft: '8px'}}
          >
            Force Save
          </button>
        </div>
      )}
    </div>
  );
};

export default CustomSegments; 