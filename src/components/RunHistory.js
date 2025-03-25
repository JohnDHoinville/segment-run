import React, { useState, useEffect } from 'react';
import { API_URL } from '../config';
import './RunHistory.css';

const RunHistory = () => {
    console.log('RunHistory rendering'); // Debug log
    const [runs, setRuns] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const fetchRuns = async () => {
            console.log('Fetching runs...'); // Debug log
            try {
                const response = await fetch(`${API_URL}/runs`, {
                    method: 'GET',
                    credentials: 'include',
                    headers: {
                        'Content-Type': 'application/json',
                        'Accept': 'application/json'
                    }
                });

                console.log('Response status:', response.status); // Debug log
                if (!response.ok) {
                    throw new Error(`Failed to fetch runs: ${response.status}`);
                }

                const data = await response.json();
                console.log('Received data type:', typeof data); // Debug log
                console.log('Is data array?', Array.isArray(data)); // Debug log
                
                // Ensure we're working with an array
                const runsArray = Array.isArray(data) ? data : [];
                console.log('Processed runs count:', runsArray.length); // Debug log
                
                setRuns(runsArray);
            } catch (err) {
                console.error('Error fetching runs:', err);
                setError(err.message);
                setRuns([]); // Ensure we set an empty array on error
            } finally {
                setLoading(false);
            }
        };

        fetchRuns();
    }, []);

    // Add debug logs for state
    console.log('Current state:', { 
        runs: runs, 
        isArray: Array.isArray(runs),
        length: runs?.length,
        loading, 
        error 
    }); // Debug log

    if (loading) {
        return <div className="loading-indicator">Loading runs history...</div>;
    }

    if (error) {
        return <div className="error-message">Error: {error}</div>;
    }

    // Defensive check before rendering
    if (!Array.isArray(runs)) {
        console.error('runs is not an array:', runs); // Debug log
        return <div className="error-message">Error: Invalid data format received from server</div>;
    }

    return (
        <div className="run-history-container">
            <h2>Run History</h2>
            {runs.length > 0 ? (
                <div className="runs-list">
                    {runs.map(run => (
                        <div key={run.id} className="run-item">
                            <h3>Run on {run.date}</h3>
                            <p>Distance: {run.total_distance?.toFixed(2) || 0} miles</p>
                            <p>Average Pace: {formatPace(run.avg_pace)} min/mile</p>
                            {run.avg_hr && <p>Average Heart Rate: {Math.round(run.avg_hr)} bpm</p>}
                        </div>
                    ))}
                </div>
            ) : (
                <p className="no-runs-message">No runs found. Upload a GPX file to get started!</p>
            )}
        </div>
    );
};

// Helper function to format pace (seconds to min:sec)
const formatPace = (paceInSeconds) => {
    if (!paceInSeconds) return '0:00';
    const minutes = Math.floor(paceInSeconds / 60);
    const seconds = Math.floor(paceInSeconds % 60);
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
};

export default RunHistory; 