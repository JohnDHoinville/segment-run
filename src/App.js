import React, { useState } from 'react';
import './App.css';
import LoadingSpinner from './components/LoadingSpinner';

function App() {
  const API_URL = 'http://localhost:5001';

  const [selectedFile, setSelectedFile] = useState(null);
  const [paceLimit, setPaceLimit] = useState('');
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleFileSelect = (event) => {
    setSelectedFile(event.target.files[0]);
    setError(null);
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

  return (
    <div className="App">
      <header className="App-header">
        <h1>Running Analysis</h1>
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
              <div className="segments">
                <h3>Fast Segments</h3>
                <div className="table-container">
                  <table>
                    <thead>
                      <tr>
                        <th>Segment</th>
                        <th>Distance</th>
                        <th>Pace</th>
                        <th>Heart Rate</th>
                      </tr>
                    </thead>
                    <tbody>
                      {results.fast_segments.map((segment, index) => (
                        <tr key={index}>
                          <td>{index + 1}</td>
                          <td>{segment.distance.toFixed(2)} mi</td>
                          <td>{segment.pace.toFixed(1)} min/mi</td>
                          <td>{Math.round(segment.avg_hr)} bpm</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}

export default App;