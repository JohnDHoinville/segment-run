import React, { useState } from 'react';
import './App.css';
import LoadingSpinner from './components/LoadingSpinner';
import { Bar } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
} from 'chart.js';

// Register ChartJS components
ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
);

function App() {
  const API_URL = 'http://localhost:5001';

  const [selectedFile, setSelectedFile] = useState(null);
  const [paceLimit, setPaceLimit] = useState('');
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [runDate, setRunDate] = useState(null);

  const handleFileSelect = (event) => {
    setSelectedFile(event.target.files[0]);
    setError(null);
    
    // Extract date from filename
    const filename = event.target.files[0].name;
    const dateMatch = filename.match(/\d{4}-\d{2}-\d{2}/);
    if (dateMatch) {
      const date = new Date(dateMatch[0]);
      setRunDate(date.toLocaleDateString('en-US', { 
        weekday: 'long',
        year: 'numeric', 
        month: 'long', 
        day: 'numeric' 
      }));
    }
  };

  const testBackendConnection = async () => {
    try {
      const response = await fetch(`${API_URL}/test`);
      const data = await response.json();
      console.log('Backend connection test:', data);
      return true;
    } catch (error) {
      console.error('Backend connection test failed:', error);
      return false;
    }
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError(null);
    
    // Test connection first
    const isConnected = await testBackendConnection();
    if (!isConnected) {
      setError(`Cannot connect to backend server. Please make sure it is running on ${API_URL}`);
      return;
    }

    if (!selectedFile) {
      setError('Please select a GPX file');
      return;
    }
    if (!paceLimit) {
      setError('Please enter a pace limit');
      return;
    }
    if (paceLimit <= 0) {
      setError('Pace limit must be greater than 0');
      return;
    }
    if (!selectedFile.name.endsWith('.gpx')) {
      setError('Please select a valid GPX file');
      return;
    }

    setLoading(true);
    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('paceLimit', paceLimit);

    try {
      console.log('Sending request to:', `${API_URL}/analyze`);
      const response = await fetch(`${API_URL}/analyze`, {
        method: 'POST',
        body: formData,
        mode: 'cors',
      });
      
      console.log('Response received:', response);
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `Server error: ${response.status}`);
      }

      const data = await response.json();
      setResults(data);
    } catch (error) {
      console.error('Detailed error:', error);
      setError(error.message || 'Failed to connect to server');
    } finally {
      setLoading(false);
    }
  };

  // Update the chart data preparation function
  const prepareChartData = (segments) => {
    return {
      labels: segments.map((segment, index) => {
        const startTime = segment.start_time ? 
          new Date(segment.start_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 
          `Segment ${index + 1}`;
        return startTime;
      }),
      datasets: [
        {
          label: 'Average Pace (min/mile)',
          data: segments.map(segment => segment.pace),
          backgroundColor: 'rgba(75, 192, 192, 0.6)',
          borderColor: 'rgba(75, 192, 192, 1)',
          borderWidth: 1,
          yAxisID: 'y'
        },
        {
          label: 'Average Heart Rate (bpm)',
          data: segments.map(segment => segment.avg_hr),
          backgroundColor: 'rgba(255, 99, 132, 0.6)',
          borderColor: 'rgba(255, 99, 132, 1)',
          borderWidth: 1,
          yAxisID: 'y1'
        }
      ]
    };
  };

  // Update chart options
  const chartOptions = {
    responsive: true,
    scales: {
      x: {
        title: {
          display: true,
          text: 'Segment Time Range'
        }
      },
      y: {
        beginAtZero: true,
        position: 'left',
        title: {
          display: true,
          text: 'Pace (min/mile)'
        }
      },
      y1: {
        beginAtZero: true,
        position: 'right',
        grid: {
          drawOnChartArea: false,
        },
        title: {
          display: true,
          text: 'Heart Rate (bpm)'
        }
      }
    },
    plugins: {
      legend: {
        position: 'top',
      },
      title: {
        display: true,
        text: 'Fast Segments Analysis'
      },
      tooltip: {
        callbacks: {
          label: function(context) {
            const label = context.dataset.label || '';
            const value = context.parsed.y;
            const segment = results.fast_segments[context.dataIndex];
            return [
              `${label}: ${value.toFixed(1)}`,
              `Distance: ${segment.distance.toFixed(2)} mi`,
              `Duration: ${segment.duration || 'N/A'}`
            ];
          }
        }
      }
    }
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>
          {runDate ? `Running Analysis for ${runDate}` : 'Running Analysis'}
        </h1>
        <p className="subtitle">Upload your GPX file to analyze pace and heart rate data</p>
      </header>
      
      <main className="App-main">
        {error && (
          <div className="error-message">
            <p>❌ {error}</p>
          </div>
        )}
        
        <div className="upload-section">
          <form onSubmit={handleSubmit} className="analysis-form">
            <div className="form-group file-input-group">
              <label htmlFor="file">
                <div className="file-upload-box">
                  <i className="upload-icon">📁</i>
                  <span>{selectedFile ? selectedFile.name : 'Choose GPX File'}</span>
                </div>
              </label>
              <input
                type="file"
                id="file"
                accept=".gpx"
                onChange={handleFileSelect}
                className="hidden"
              />
            </div>
            
            <div className="form-group">
              <label htmlFor="paceLimit">Target Pace (min/mile):</label>
              <input
                type="number"
                id="paceLimit"
                value={paceLimit}
                onChange={(e) => setPaceLimit(e.target.value)}
                step="0.1"
                min="0"
                placeholder="Enter target pace"
                className="pace-input"
              />
            </div>
            
            <button 
              type="submit" 
              disabled={loading || !selectedFile || !paceLimit}
              className={`submit-button ${loading ? 'loading' : ''}`}
            >
              {loading ? 'Analyzing...' : 'Analyze Run'}
            </button>
          </form>
        </div>

        {loading && <LoadingSpinner />}

        {results && !loading && (
          <div className="results">
            <h2>Analysis Results</h2>
            <div className="results-grid">
              <div className="result-item">
                <h3>Total Distance</h3>
                <p className="result-value">{results.total_distance.toFixed(2)}</p>
                <p className="result-unit">miles</p>
              </div>
              
              <div className="result-item">
                <h3>Fast Distance</h3>
                <p className="result-value">{results.fast_distance.toFixed(2)}</p>
                <p className="result-unit">miles</p>
                <p className="result-percentage">
                  ({results.percentage_fast.toFixed(1)}% of total)
                </p>
                <div className="avg-pace">
                  <p className="result-label">Average Pace</p>
                  <p className="result-value-secondary">
                    {(results.fast_segments.reduce((sum, segment) => sum + segment.pace, 0) / 
                      results.fast_segments.length).toFixed(1)}
                  </p>
                  <p className="result-unit">min/mile</p>
                </div>
              </div>
              
              <div className="result-item">
                <h3>Average Heart Rate</h3>
                <div className="hr-container">
                  <div className="hr-item">
                    <p className="result-label">Overall</p>
                    <p className="result-value">{Math.round(results.avg_hr_all)}</p>
                    <p className="result-unit">bpm</p>
                  </div>
                  <div className="hr-item">
                    <p className="result-label">Fast Segments</p>
                    <p className="result-value">{Math.round(results.avg_hr_fast)}</p>
                    <p className="result-unit">bpm</p>
                  </div>
                </div>
              </div>
            </div>

            {results.fast_segments.length > 0 && (
              <>
                <div className="segments">
                  <h3>Fast Segments</h3>
                  <div className="chart-container">
                    <Bar 
                      data={prepareChartData(results.fast_segments)} 
                      options={chartOptions}
                    />
                  </div>
                  <div className="table-container">
                    <table>
                      <thead>
                        <tr>
                          <th>Segment</th>
                          <th>Start Time</th>
                          <th>End Time</th>
                          <th>Distance</th>
                          <th>Pace</th>
                          <th>Heart Rate</th>
                        </tr>
                      </thead>
                      <tbody>
                        {results.fast_segments.map((segment, index) => (
                          <tr key={index}>
                            <td>{index + 1}</td>
                            <td>{segment.start_time ? 
                              new Date(segment.start_time).toLocaleTimeString() : 'N/A'}</td>
                            <td>{segment.end_time ? 
                              new Date(segment.end_time).toLocaleTimeString() : 'N/A'}</td>
                            <td>{segment.distance.toFixed(2)} mi</td>
                            <td>{segment.pace.toFixed(1)} min/mi</td>
                            <td>{Math.round(segment.avg_hr)} bpm</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </>
            )}
          </div>
        )}
      </main>
    </div>
  );
}

export default App;