import React, { useState, useEffect } from 'react';
import { API_URL } from '../config';
import './RunHistory.css';

const RunHistory = () => {
    // IMPORTANT: Initialize runs as an empty array, never null or undefined
    const [runs, setRuns] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    // Ensure runs is always an array, even if state somehow gets corrupted
    const safeRuns = Array.isArray(runs) ? runs : [];

    useEffect(() => {
        let isMounted = true;
        
        // Safely pre-process and parse JSON that might contain Infinity values
        const safelyParseJSON = (jsonText) => {
            try {
                if (!jsonText || typeof jsonText !== 'string') {
                    console.error('Invalid JSON input:', jsonText);
                    return [];
                }
                
                // First approach: Regular expression to replace all instances of Infinity/NaN as unquoted literals
                let processed = jsonText
                    .replace(/"pace"\s*:\s*Infinity/g, '"pace":"Infinity"')
                    .replace(/"pace"\s*:\s*-Infinity/g, '"pace":"-Infinity"')
                    .replace(/"pace"\s*:\s*NaN/g, '"pace":"NaN"')
                    .replace(/:\s*Infinity/g, ':"Infinity"')
                    .replace(/:\s*-Infinity/g, ':"-Infinity"')
                    .replace(/:\s*NaN/g, ':"NaN"');
                    
                try {
                    // Try parsing the pre-processed JSON
                    return JSON.parse(processed);
                } catch (e) {
                    console.error('First approach failed:', e);
                    
                    // Second approach: More aggressive replacements
                    processed = jsonText
                        .replace(/Infinity/g, '"Infinity"')
                        .replace(/-Infinity/g, '"-Infinity"')
                        .replace(/NaN/g, '"NaN"')
                        // Fix double quotes that might have been introduced
                        .replace(/""/g, '"');
                        
                    try {
                        return JSON.parse(processed);
                    } catch (e2) {
                        console.error('Second approach failed:', e2);
                        
                        // Last resort: Try a completely different approach
                        // Convert everything that looks like a JSON object to a JS object
                        try {
                            // Using Function constructor as a last resort (safe in this context)
                            const jsObj = new Function('return ' + jsonText.replace(/Infinity/g, '"Infinity"').replace(/-Infinity/g, '"-Infinity"').replace(/NaN/g, '"NaN"'))();
                            return jsObj;
                        } catch (e3) {
                            console.error('All approaches failed. Returning empty array.');
                            console.log('Problematic JSON:', jsonText.substring(0, 500) + '...');
                            return [];
                        }
                    }
                }
            } catch (e) {
                console.error('Fatal JSON parsing error:', e);
                return [];
            }
        };

        const fetchRuns = async () => {
            console.log('Fetching runs...'); 
            
            // Always start with a known good state
            if (isMounted) {
                setLoading(true);
                setError(null);
            }
            
            try {
                const response = await fetch(`${API_URL}/runs`, {
                    method: 'GET',
                    credentials: 'include',
                    headers: {
                        'Content-Type': 'application/json',
                        'Accept': 'application/json'
                    }
                });

                if (!response.ok) {
                    throw new Error(`Failed to fetch runs: ${response.status}`);
                }

                // Safely parse JSON with error handling
                let data;
                try {
                    const text = await response.text();
                    console.log('Raw response:', text.substring(0, 100) + "...");
                    
                    // Ensure we're parsing valid JSON
                    if (!text || text.trim() === '') {
                        console.warn('Empty response from server');
                        data = [];
                    } else {
                        data = safelyParseJSON(text);
                    }
                } catch (jsonError) {
                    console.error('Error parsing JSON:', jsonError);
                    throw new Error('Invalid response format from server');
                }

                console.log('Received data:', data?.length);
                console.log('Data type:', typeof data);
                console.log('Is array:', Array.isArray(data));
                
                // Super defensive data handling
                let processedRuns = [];
                
                // Check various possible formats and convert to array
                if (Array.isArray(data)) {
                    processedRuns = data;
                } else if (data && typeof data === 'object') {
                    if (data.runs && Array.isArray(data.runs)) {
                        processedRuns = data.runs;
                    } else {
                        // Try to convert object to array as last resort
                        try {
                            processedRuns = Object.values(data);
                        } catch (e) {
                            console.error('Failed to convert object to array:', e);
                            processedRuns = [];
                        }
                    }
                }
                
                console.log('Processed runs count:', processedRuns.length);
                console.log('Is processed array:', Array.isArray(processedRuns));
                
                // Set state only if component is still mounted
                if (isMounted) {
                    // CRITICAL: Ensure we're setting an array
                    setRuns(Array.isArray(processedRuns) ? processedRuns : []);
                    setError(null);
                }
            } catch (err) {
                console.error('Error fetching runs:', err);
                // Set state only if component is still mounted
                if (isMounted) {
                    setError(err.message);
                    // CRITICAL: Set runs to empty array on error, never null or undefined
                    setRuns([]);
                }
            } finally {
                if (isMounted) {
                    setLoading(false);
                }
            }
        };

        fetchRuns();
        
        // Cleanup function to prevent state updates on unmounted component
        return () => {
            isMounted = false;
        };
    }, []);

    // Render loading state
    if (loading) {
        return <div className="loading-indicator">Loading runs history...</div>;
    }

    // Render error state
    if (error) {
        return <div className="error-message">Error: {error}</div>;
    }

    // Render empty state
    if (!Array.isArray(safeRuns) || safeRuns.length === 0) {
        return (
            <div className="run-history-container">
                <h2>Run History</h2>
                <p className="no-runs-message">No runs found. Upload a GPX file to get started!</p>
            </div>
        );
    }

    // Only get here if safeRuns is definitely an array with items
    return (
        <div className="run-history-container">
            <h2>Run History</h2>
            <div className="runs-list">
                {safeRuns.map((run, index) => {
                    // More defensive checks for each run item
                    const runId = run?.id || index;
                    const date = run?.date || 'Unknown Date';
                    const distance = (run?.total_distance !== undefined) 
                        ? Number(run.total_distance).toFixed(2) 
                        : '0';
                    const pace = formatPace(run?.avg_pace);
                    const heartRate = run?.avg_hr 
                        ? Math.round(Number(run.avg_hr)) 
                        : null;
                    
                    // Extract fast segments information
                    let fastSegments = [];
                    try {
                        // Access fast_segments from data object
                        if (run.data && run.data.fast_segments && Array.isArray(run.data.fast_segments)) {
                            fastSegments = run.data.fast_segments;
                        }
                    } catch (e) {
                        console.error(`Error processing fast segments for run ${runId}:`, e);
                    }
                        
                    return (
                        <div key={runId} className="run-item">
                            <h3>Run on {date}</h3>
                            <p>Distance: {distance} miles</p>
                            <p>Average Pace: {pace} min/mile</p>
                            {heartRate && <p>Average Heart Rate: {heartRate} bpm</p>}
                            
                            {/* Fast segments section */}
                            {fastSegments.length > 0 && (
                                <div className="fast-segments">
                                    <h4>Fast Segments</h4>
                                    {fastSegments.map((segment, i) => {
                                        const segmentDistance = segment.distance ? 
                                            Number(segment.distance).toFixed(2) : '0';
                                        const segmentPace = formatPace(segment.pace);
                                        
                                        return (
                                            <div key={i} className="segment-item">
                                                <p>Segment {i+1}: {segmentDistance} miles at {segmentPace} min/mile</p>
                                            </div>
                                        );
                                    })}
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>
        </div>
    );
};

// Helper function to format pace (seconds to min:sec)
const formatPace = (paceInSeconds) => {
    if (!paceInSeconds) return '0:00';
    try {
        const paceNum = Number(paceInSeconds);
        if (isNaN(paceNum)) return '0:00';
        
        const minutes = Math.floor(paceNum / 60);
        const seconds = Math.floor(paceNum % 60);
        return `${minutes}:${seconds.toString().padStart(2, '0')}`;
    } catch (e) {
        console.error('Error formatting pace:', e);
        return '0:00';
    }
};

export default RunHistory; 