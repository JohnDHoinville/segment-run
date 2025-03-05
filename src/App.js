/* eslint-disable react-hooks/exhaustive-deps */
import React, { useState, createContext, useContext, useEffect, useRef, useMemo } from 'react';
import './App.css';
import LoadingSpinner from './components/LoadingSpinner';
import LoginForm from './components/LoginForm';
import TrainingZones from './components/TrainingZones';
import AdvancedMetrics from './components/AdvancedMetrics';
import RacePredictions from './components/RacePredictions';
import { API_URL } from './config';
import { Bar, Line } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  Title,
  Tooltip as ChartTooltip,
  Legend,
  Filler
} from 'chart.js';
import { 
  MapContainer, 
  TileLayer, 
  Polyline,
  Tooltip as MapTooltip,
  Circle,
  CircleMarker
} from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import PaceProgressChart from './components/PaceProgressChart';

// Register ChartJS components
ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  Title,
  ChartTooltip,
  Legend,
  Filler
);

// Create theme context
const ThemeContext = createContext();

// Add theme provider component
const ThemeProvider = ({ children }) => {
  const [isDarkMode, setIsDarkMode] = useState(false);
  return (
    <ThemeContext.Provider value={{ isDarkMode, setIsDarkMode }}>
      <div className={`theme ${isDarkMode ? 'dark' : 'light'}`}>
        {children}
      </div>
    </ThemeContext.Provider>
  );
};

// Add theme toggle component
const ThemeToggle = () => {
  const { isDarkMode, setIsDarkMode } = useContext(ThemeContext);
  return (
    <button 
      className="theme-toggle"
      onClick={() => setIsDarkMode(!isDarkMode)}
      aria-label="Toggle dark mode"
    >
      {isDarkMode ? '☀️' : '🌙'}
    </button>
  );
};

// Add ProfileMenu component after ThemeToggle
const ProfileMenu = ({ username, age, restingHR, onSave, onLogout }) => {
  const { isDarkMode, setIsDarkMode } = useContext(ThemeContext);
  const [isOpen, setIsOpen] = useState(false);
  const [activeTab, setActiveTab] = useState('profile');
  const [editAge, setEditAge] = useState(age || '');
  const [editRestingHR, setEditRestingHR] = useState(restingHR || '');
  const [editWeight, setEditWeight] = useState('70');
  const [editGender, setEditGender] = useState('1');
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const menuRef = useRef(null);

  // Update local state when props change
  useEffect(() => {
    setEditAge(age || '');
    setEditRestingHR(restingHR || '');
    // Get weight and gender from profile
    fetch(`${API_URL}/profile`, { credentials: 'include' })
      .then(res => res.json())
      .then(data => {
        setEditWeight(data.weight?.toString() || '70');
        setEditGender(data.gender?.toString() || '1');
      });
  }, [age, restingHR]);

  // Close menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (menuRef.current && !menuRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSave = async () => {
    try {
      setError('');
      setSuccessMessage('');
      
      const response = await fetch(`${API_URL}/profile`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          age: parseInt(editAge),
          resting_hr: parseInt(editRestingHR),
          weight: parseFloat(editWeight),
          gender: parseInt(editGender)
        }),
      });

      if (response.ok) {
        onSave(editAge, editRestingHR);
        setSuccessMessage('Profile updated successfully');
      } else {
        const error = await response.json();
        setError(error.message || 'Failed to save profile');
      }
    } catch (error) {
      setError('Error saving profile. Please try again.');
    }
  };

  const handleChangePassword = async () => {
    try {
      setError('');
      setSuccessMessage('');

      if (newPassword !== confirmPassword) {
        setError('New passwords do not match');
        return;
      }

      const response = await fetch(`${API_URL}/auth/change-password`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword
        }),
      });

      if (response.ok) {
        setCurrentPassword('');
        setNewPassword('');
        setConfirmPassword('');
        setSuccessMessage('Password updated successfully');
      } else {
        const error = await response.json();
        setError(error.message || 'Failed to update password');
      }
    } catch (error) {
      setError('Error updating password');
    }
  };

  return (
    <div className="profile-menu" ref={menuRef}>
      <div className="user-menu">
        <span className="username">👤 {username}</span>
        <button 
          className="hamburger-button"
          onClick={() => setIsOpen(!isOpen)}
          aria-label="Menu"
        >
          ☰
        </button>
      </div>
      
      {isOpen && (
        <div className="profile-dropdown">
          <div className="profile-header">
            <h3>Profile Settings</h3>
            <button 
              className="close-button"
              onClick={() => setIsOpen(false)}
              aria-label="Close"
            >
              ×
            </button>
          </div>

          <div className="profile-tabs">
            <button 
              className={activeTab === 'profile' ? 'active' : ''}
              onClick={() => setActiveTab('profile')}
            >
              Profile
            </button>
            <button 
              className={activeTab === 'security' ? 'active' : ''}
              onClick={() => setActiveTab('security')}
            >
              Security
            </button>
          </div>

          {error && <div className="profile-error">{error}</div>}
          {successMessage && <div className="profile-success">{successMessage}</div>}

          {activeTab === 'profile' ? (
            <div className="profile-content">
              <div className="theme-toggle-container">
                <label>Theme</label>
                <button 
                  className="theme-toggle-button"
                  onClick={() => setIsDarkMode(!isDarkMode)}
                >
                  {isDarkMode ? '☀️ Light Mode' : '🌙 Dark Mode'}
                </button>
              </div>

              <div className="profile-stats">
                <div className="stat-item">
                  <span className="stat-label">Current Age</span>
                  <span className="stat-value">{age || 'Not set'}</span>
                </div>
                <div className="stat-item">
                  <span className="stat-label">Current Resting HR</span>
                  <span className="stat-value">{restingHR || 'Not set'} {restingHR && 'bpm'}</span>
                </div>
              </div>

              <div className="form-group">
                <label htmlFor="profileAge">Update Age:</label>
                <input
                  type="number"
                  id="profileAge"
                  value={editAge}
                  onChange={(e) => setEditAge(e.target.value)}
                  min="0"
                  max="120"
                  placeholder="Enter your age"
                />
              </div>

              <div className="form-group">
                <label htmlFor="profileRestingHR">Update Resting Heart Rate (bpm):</label>
                <input
                  type="number"
                  id="profileRestingHR"
                  value={editRestingHR}
                  onChange={(e) => setEditRestingHR(e.target.value)}
                  min="30"
                  max="200"
                  placeholder="Enter resting heart rate"
                />
              </div>

              <div className="form-group">
                <label htmlFor="weight">Weight (lbs):</label>
                <input
                  type="number"
                  id="weight"
                  value={editWeight}
                  onChange={(e) => setEditWeight(e.target.value)}
                  placeholder="Enter your weight in lbs"
                />
              </div>

              <div className="form-group">
                <label htmlFor="gender">Gender:</label>
                <select
                  id="gender"
                  value={editGender}
                  onChange={(e) => setEditGender(e.target.value)}
                >
                  <option value="1">Male</option>
                  <option value="0">Female</option>
                </select>
              </div>

              <button onClick={handleSave} className="save-button">
                Save Changes
              </button>
            </div>
          ) : (
            <div className="security-content">
              <div className="form-group">
                <label htmlFor="currentPassword">Current Password:</label>
                <input
                  type="password"
                  id="currentPassword"
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                  placeholder="Enter current password"
                />
              </div>

              <div className="form-group">
                <label htmlFor="newPassword">New Password:</label>
                <input
                  type="password"
                  id="newPassword"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="Enter new password"
                />
              </div>

              <div className="form-group">
                <label htmlFor="confirmPassword">Confirm New Password:</label>
                <input
                  type="password"
                  id="confirmPassword"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Confirm new password"
                />
              </div>

              <button onClick={handleChangePassword} className="save-button">
                Update Password
              </button>
            </div>
          )}

          <div className="profile-footer">
            <button onClick={onLogout} className="logout-button">
              Sign Out
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

// Add these chart preparation functions
const preparePaceChart = (run) => {
  const data = typeof run.data === 'string' ? JSON.parse(run.data) : run.data;
  
  // Create quarter-mile interpolated data from mile splits
  const quarterMileSplits = [];
  const mileSplits = data.mile_splits || [];
  
  for (let i = 0; i < mileSplits.length - 1; i++) {
    const currentSplit = mileSplits[i];
    const nextSplit = mileSplits[i + 1];
    
    // Add current mile point
    quarterMileSplits.push({
      distance: currentSplit.mile,
      pace: currentSplit.split_pace
    });
    
    // Add three quarter points between miles
    for (let q = 1; q <= 3; q++) {
      const fraction = q / 4;
      const interpolatedPace = currentSplit.split_pace + 
        (nextSplit.split_pace - currentSplit.split_pace) * fraction;
      
      quarterMileSplits.push({
        distance: currentSplit.mile + fraction,
        pace: interpolatedPace
      });
    }
  }
  
  // Add the last mile point
  if (mileSplits.length > 0) {
    const lastSplit = mileSplits[mileSplits.length - 1];
    quarterMileSplits.push({
      distance: lastSplit.mile,
      pace: lastSplit.split_pace
    });
  }

  return {
    labels: quarterMileSplits.map(split => `Mile ${split.distance.toFixed(2)}`),
    datasets: [{
      label: 'Pace',
      data: quarterMileSplits.map(split => split.pace),
      borderColor: 'var(--accent-primary)',
      backgroundColor: 'rgba(112, 193, 179, 0.2)',
      fill: true,
      tension: 0.4
    }]
  };
};

const prepareHRChart = (run) => {
  const data = typeof run.data === 'string' ? JSON.parse(run.data) : run.data;
  
  // Create quarter-mile interpolated data from mile splits
  const quarterMileSplits = [];
  const mileSplits = data.mile_splits || [];
  
  for (let i = 0; i < mileSplits.length - 1; i++) {
    const currentSplit = mileSplits[i];
    const nextSplit = mileSplits[i + 1];
    
    // Add current mile point
    quarterMileSplits.push({
      distance: currentSplit.mile,
      hr: currentSplit.avg_hr
    });
    
    // Add three quarter points between miles
    for (let q = 1; q <= 3; q++) {
      const fraction = q / 4;
      const interpolatedHR = currentSplit.avg_hr + 
        (nextSplit.avg_hr - currentSplit.avg_hr) * fraction;
      
      quarterMileSplits.push({
        distance: currentSplit.mile + fraction,
        hr: interpolatedHR
      });
    }
  }
  
  // Add the last mile point
  if (mileSplits.length > 0) {
    const lastSplit = mileSplits[mileSplits.length - 1];
    quarterMileSplits.push({
      distance: lastSplit.mile,
      hr: lastSplit.avg_hr
    });
  }

  return {
    labels: quarterMileSplits.map(split => `Mile ${split.distance.toFixed(2)}`),
    datasets: [{
      label: 'Heart Rate',
      data: quarterMileSplits.map(split => split.hr),
      borderColor: 'var(--fast-color)',
      backgroundColor: 'rgba(231, 111, 81, 0.2)',
      fill: true,
      tension: 0.4
    }]
  };
};

const paceChartOptions = {
  responsive: true,
  plugins: {
    legend: {
      position: 'top',
    },
    title: {
      display: true,
      text: 'Pace by Quarter Mile'
    }
  },
  scales: {
    x: {
      title: {
        display: true,
        text: 'Distance'
      },
      ticks: {
        maxRotation: 45,
        minRotation: 45
      }
    },
    y: {
      title: {
        display: true,
        text: 'min/mile'
      }
    }
  }
};

const hrChartOptions = {
  responsive: true,
  plugins: {
    legend: {
      position: 'top',
    },
    title: {
      display: true,
      text: 'Heart Rate by Quarter Mile'
    }
  },
  scales: {
    x: {
      title: {
        display: true,
        text: 'Distance'
      },
      ticks: {
        maxRotation: 45,
        minRotation: 45
      }
    },
    y: {
      title: {
        display: true,
        text: 'bpm'
      }
    }
  }
};

// Add these chart preparation functions
const preparePaceComparisonData = (run1, run1Data, run2, run2Data) => {
  const getFastPace = (data) => {
    if (!data?.fast_segments?.length) return null;
    return data.fast_segments.reduce((sum, seg) => sum + (seg.pace || 0), 0) / data.fast_segments.length;
  };

  const getSlowPace = (data) => {
    if (!data?.slow_segments?.length) return null;
    return data.slow_segments.reduce((sum, seg) => sum + (seg.pace || 0), 0) / data.slow_segments.length;
  };

  return {
    labels: ['Fast Segments', 'Slow Segments', 'Overall'],
    datasets: [
      {
        label: `Run 1 (${run1.total_distance?.toFixed(1) || 'N/A'} mi)`,
        data: [
          getFastPace(run1Data) || 0,
          getSlowPace(run1Data) || 0,
          run1.avg_pace || 0
        ],
        backgroundColor: 'rgba(75, 192, 192, 0.5)',
      },
      {
        label: `Run 2 (${run2.total_distance?.toFixed(1) || 'N/A'} mi)`,
        data: [
          getFastPace(run2Data) || 0,
          getSlowPace(run2Data) || 0,
          run2.avg_pace || 0
        ],
        backgroundColor: 'rgba(255, 99, 132, 0.5)',
      }
    ]
  };
};

const prepareHRComparisonData = (run1Data, run2Data) => {
  return {
    labels: ['Fast Segments', 'Slow Segments', 'Overall'],
    datasets: [
      {
        label: `Run 1 (${run1Data.total_distance?.toFixed(1) || 'N/A'} mi)`,
        data: [
          run1Data?.avg_hr_fast || 0,
          run1Data?.avg_hr_slow || 0,
          run1Data?.avg_hr_all || 0
        ],
        backgroundColor: 'rgba(75, 192, 192, 0.5)',
      },
      {
        label: `Run 2 (${run2Data.total_distance?.toFixed(1) || 'N/A'} mi)`,
        data: [
          run2Data?.avg_hr_fast || 0,
          run2Data?.avg_hr_slow || 0,
          run2Data?.avg_hr_all || 0
        ],
        backgroundColor: 'rgba(255, 99, 132, 0.5)',
      }
    ]
  };
};

const comparisonChartOptions = {
  responsive: true,
  scales: {
    y: {
      beginAtZero: true,
    }
  },
  plugins: {
    legend: {
      display: true,
      position: 'top'
    },
    title: {
      display: true,
      text: (ctx) => {
        // Check first dataset point to determine if this is pace or HR chart
        const firstValue = ctx.chart.data.datasets[0].data[0];
        if (firstValue > 50) { // Assuming this is HR data
          return 'Heart Rate Comparison (bpm)';
        } else {
          return 'Pace Comparison (min/mi)';
        }
      }
    },
    tooltip: {
      callbacks: {
        label: function(context) {
          const value = context.parsed.y;
          const label = context.dataset.label;
          // Check if this is pace or HR data
          if (value < 50) { // Assuming this is pace data
            return `${label}: ${value.toFixed(1)} min/mi`;
          } else {
            return `${label}: ${Math.round(value)} bpm`;
          }
        }
      }
    }
  }
};

// Add this utility function at the top of the file
const formatTime = (minutes) => {
  const hours = Math.floor(minutes / 60);
  const mins = Math.floor(minutes % 60);
  const secs = Math.round((minutes % 1) * 60);
  
  if (hours > 0) {
    return `${hours}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }
  return `${mins}:${secs.toString().padStart(2, '0')}`;
};

// Add this near the top of the file with other context definitions
const TableContext = createContext();

// Add this provider component
const TableProvider = ({ children }) => {
  const [openTables, setOpenTables] = useState(new Set());
  
  return (
    <TableContext.Provider value={{ openTables, setOpenTables }}>
      {children}
    </TableContext.Provider>
  );
};

// Update the CollapsibleTable component to use the context
const CollapsibleTable = ({ title, children, id }) => {
  const { openTables, setOpenTables } = useContext(TableContext);
  const isOpen = openTables.has(id);
  
  const toggleTable = () => {
    const newOpenTables = new Set(openTables);
    if (isOpen) {
      newOpenTables.delete(id);
    } else {
      newOpenTables.add(id);
    }
    setOpenTables(newOpenTables);
  };

  return (
    <div className="collapsible-table">
      <div 
        className="collapsible-header" 
        onClick={toggleTable}
      >
        <h4>{title}</h4>
        <span className="toggle-icon">{isOpen ? '▼' : '▶'}</span>
      </div>
      {isOpen && children}
    </div>
  );
};

// Add a loading animation component
const LoadingOverlay = () => (
  <div className="loading-overlay">
    <div className="loading-spinner"></div>
    <p>Analyzing your run...</p>
  </div>
);

const InfoTooltip = ({ text }) => (
  <span className="info-tooltip" title={text}>ⓘ</span>
);

const ErrorMessage = ({ message }) => (
  <div className="error-message">
    <span className="error-icon">⚠️</span>
    <p>{message}</p>
    <button className="retry-button" onClick={() => window.location.reload()}>
      Try Again
    </button>
  </div>
);

const SuccessMessage = ({ message }) => (
  <div className="success-message">
    <span className="success-icon">✓</span>
    <p>{message}</p>
  </div>
);

// Add this helper function near the top of your file
const calculateAveragePace = (segments) => {
  if (!segments || segments.length === 0) return 0;
  return segments.reduce((sum, segment) => sum + segment.pace, 0) / segments.length;
};

function App() {
  const API_URL = 'http://localhost:5001';

  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState(null);
  const [selectedFile, setSelectedFile] = useState(null);
  const [fileName, setFileName] = useState('');
  const [runDate, setRunDate] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [saveStatus, setSaveStatus] = useState('');
  const [paceLimit, setPaceLimit] = useState(10);
  const [age, setAge] = useState('');
  const [restingHR, setRestingHR] = useState('');
  const [runHistory, setRunHistory] = useState([]);
  const [compareMode, setCompareMode] = useState(false);
  const [comparedRuns, setComparedRuns] = useState([]);
  const [userId, setUserId] = useState(null);
  const [username, setUsername] = useState('');
  const [selectedRunId, setSelectedRunId] = useState(null);

  // Define fetchRunHistory first
  const fetchRunHistory = useMemo(() => async () => {
    try {
      const response = await fetch(`${API_URL}/runs`, {
        credentials: 'include'
      });
      if (response.ok) {
        const data = await response.json();
        console.log('Run history data:', data);  // Debug log
        setRunHistory(data);
      }
    } catch (error) {
      console.error('Error loading run history:', error);
    }
  }, [API_URL]);

  // Now we can use fetchRunHistory in useEffect
  useEffect(() => {
    if (isAuthenticated) {
      fetchRunHistory();
    }
  }, [isAuthenticated, fetchRunHistory]);

  // Check authentication status on mount
  useEffect(() => {
    const checkAuth = async () => {
      try {
        console.log('Checking auth at:', `${API_URL}/auth/check`);
        const response = await fetch(`${API_URL}/auth/check`, {
          credentials: 'include'
        });
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        console.log('Auth check response:', data);
        if (data.authenticated) {
          setUserId(data.user_id);
          setIsAuthenticated(true);
        } else {
          setIsAuthenticated(false);
          setUserId(null);
        }
      } catch (error) {
        console.error('Auth check error details:', error);
        console.log('Auth check failed:', error);
        setIsAuthenticated(false);
        setUserId(null);
      }
    };
    checkAuth();
  }, []);

  // Load profile on mount
  useEffect(() => {
    const loadProfile = async () => {
      try {
        const response = await fetch(`${API_URL}/profile`, {
          credentials: 'include'
        });
        if (response.ok) {
      const data = await response.json();
          setAge(data.age?.toString() || '0');
          setRestingHR(data.resting_hr?.toString() || '0');
        } else {
          console.error('Failed to load profile');
        }
    } catch (error) {
        console.error('Error loading profile:', error);
      }
    };

    if (userId) {
      loadProfile();
    }
  }, [userId]);

  const handleProfileSave = (newAge, newRestingHR) => {
    setAge(newAge.toString());
    setRestingHR(newRestingHR.toString());
  };

  const handleFileChange = (event) => {
    const file = event.target.files?.[0];
    if (!file) {
      setSelectedFile(null);
      setFileName('');
      setError('');
      return;
    }

    setSelectedFile(file);
    setFileName(file.name);
    setError('');

    // Extract date from filename
    const dateMatch = file.name.match(/\d{4}-\d{2}-\d{2}/);
    if (dateMatch) {
      setRunDate(dateMatch[0]);
    } else {
      // If no date in filename, use current date
      const today = new Date();
      setRunDate(today.toISOString().split('T')[0]);
    }
  };

  const handleSaveRun = async (results) => {
    if (!runDate) {
      throw new Error('No run date available');
    }

    try {
      const response = await fetch(`${API_URL}/runs`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        credentials: 'include',
        body: JSON.stringify({
          date: runDate,
          data: results
        })
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.message || 'Failed to save run');
      }

      setSaveStatus('Run saved successfully!');
      await fetchRunHistory();
    } catch (error) {
      console.error('Error saving run:', error);
      throw error;
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setSaveStatus('');
    setError('');

    if (!selectedFile) {
      setError('Please select a file');
      setLoading(false);
      return;
    }

    console.log('Uploading file:', selectedFile.name);
    console.log('File size:', selectedFile.size);
    console.log('File type:', selectedFile.type);
    console.log('Form data:', {
      paceLimit,
      age,
      restingHR
    });

    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('paceLimit', paceLimit || 10);
    formData.append('age', age || 0);
    formData.append('restingHR', restingHR || 0);

    try {
      console.log('Sending request to:', `${API_URL}/analyze`);
      const response = await fetch(`${API_URL}/analyze`, {
        method: 'POST',
        credentials: 'include',
        body: formData
      });

      console.log('Response status:', response.status);
      const responseData = await response.json();
      console.log('Response data:', responseData);

      if (!response.ok) {
        console.error('Server error:', responseData);
        throw new Error(responseData.error || 'Failed to analyze run');
      }

      console.log('Analysis results:', responseData);
      console.log('Training zones:', responseData.data?.training_zones);
      setResults(responseData.data);
      setSaveStatus(responseData.saved ? 'Run saved successfully!' : 'Run analyzed but not saved');
    } catch (error) {
      console.error('Error:', error);
      setError(error.message || 'Failed to analyze run');
    } finally {
      setLoading(false);
    }
  };

  // Update the chart data preparation function
  const prepareChartData = (results) => {
    if (!results || !results.fast_segments || !results.slow_segments) {
      return {
        labels: [],
        datasets: []
      };
    }

    const allSegments = [
      ...results.fast_segments.map(s => ({...s, type: 'fast'})),
      ...results.slow_segments.map(s => ({...s, type: 'slow'}))
    ].sort((a, b) => new Date(a.start_time) - new Date(b.start_time));

    const datasets = [
      {
        label: 'Pace (min/mile)',
        data: allSegments.map(segment => segment.pace),
        backgroundColor: allSegments.map(segment => 
          segment.type === 'fast' ? 'rgba(75, 192, 192, 0.6)' : 'rgba(192, 75, 75, 0.6)'
        ),
        borderColor: allSegments.map(segment => 
          segment.type === 'fast' ? 'rgba(75, 192, 192, 1)' : 'rgba(192, 75, 75, 1)'
        ),
        borderWidth: 1,
        yAxisID: 'y',
        type: 'bar'
      },
      {
        label: 'Heart Rate (bpm)',
        data: allSegments.map(segment => segment.avg_hr),
        borderColor: 'rgba(255, 99, 132, 1)',
        borderWidth: 2,
        yAxisID: 'y1',
        type: 'line',
        pointRadius: 4,
        fill: false,
        tension: 0.1
      }
    ];

    // Only add elevation data if it exists
    if (results.elevation_data && results.elevation_data.length > 0) {
      datasets.push({
        label: 'Elevation (ft)',
        data: results.elevation_data.map(point => point.elevation),
        borderColor: 'rgba(153, 102, 255, 1)',
        borderWidth: 2,
        yAxisID: 'y2',
        type: 'line',
        pointRadius: 0,
        fill: true,
        backgroundColor: 'rgba(153, 102, 255, 0.1)',
        tension: 0.4
      });
    }

    return {
      labels: allSegments.map(segment => 
        new Date(segment.start_time).toLocaleTimeString([], { 
          hour: '2-digit', 
          minute: '2-digit' 
        })
      ),
      datasets
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
        beginAtZero: false,
        position: 'left',
        title: {
          display: true,
          text: 'Pace (min/mile)'
        },
        afterDataLimits: (scale) => {
          const range = scale.max - scale.min;
          scale.max += range * 0.25;
          scale.min -= range * 0.25;
        }
      },
      y1: {
        beginAtZero: false,
        position: 'right',
        grid: {
          drawOnChartArea: false,
        },
        title: {
          display: true,
          text: 'Heart Rate (bpm)'
        },
        afterDataLimits: (scale) => {
          const range = scale.max - scale.min;
          scale.max += range * 0.25;
          scale.min -= range * 0.25;
        }
      },
      y2: {
        beginAtZero: false,
        position: 'right',
        grid: {
          drawOnChartArea: false,
        },
        title: {
          display: true,
          text: 'Elevation (ft)'
        }
      }
    },
    plugins: {
      legend: {
        position: 'top',
      },
      title: {
        display: true,
        text: 'Segment Analysis'
      },
      tooltip: {
        callbacks: {
          label: function(context) {
            const label = context.dataset.label || '';
            const value = context.parsed.y;
            const allSegments = [
              ...results.fast_segments.map(s => ({...s, type: 'fast'})),
              ...results.slow_segments.map(s => ({...s, type: 'slow'}))
            ].sort((a, b) => new Date(a.start_time) - new Date(b.start_time));
            const segment = allSegments[context.dataIndex];

            if (!segment) return `${label}: ${value.toFixed(1)}`;

            return [
              `${label}: ${value.toFixed(1)}`,
              `Distance: ${segment.distance.toFixed(2)} mi`,
              `Type: ${segment.type === 'fast' ? 'Fast' : 'Slow'} Segment`
            ];
          }
        }
      }
    }
  };

  // Update Mile Splits component
  const MileSplits = ({ splits }) => {
    if (!splits || splits.length === 0) return null;

    return (
      <div className="mile-splits">
        <h4>Mile Splits</h4>
        <div className="table-container">
          <table className="splits-table">
            <thead>
              <tr>
                <th>Mile</th>
                <th>Split Time</th>
                <th>Pace</th>
                <th>Heart Rate</th>
              </tr>
            </thead>
            <tbody>
              {splits.map((split, index) => (
                <tr key={index}>
                  <td>{split.mile}</td>
                  <td>{formatTime(split.split_time)}</td>
                  <td>{formatTime(split.split_pace)} /mi</td>
                  <td>{Math.round(split.avg_hr)} bpm</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  };

  // Add this new component
  const RouteMap = ({ routeData, fastSegments, slowSegments }) => {
    // Set a default center (we'll update it when we have data)
    const [center, setCenter] = useState([42.5, -83.2]); // Default to Michigan area
    
    useEffect(() => {
      // Calculate center from first valid segment
      if (routeData && routeData.length > 0) {
        const firstSegment = routeData[0];
        if (firstSegment.coordinates && firstSegment.coordinates.length > 0) {
          // Use the first coordinate of the first segment
          setCenter(firstSegment.coordinates[0]);
          console.log('Setting map center to:', firstSegment.coordinates[0]);
        }
      }
    }, [routeData]);

    // Process segments for display
    const processedSegments = useMemo(() => {
      if (!routeData || !routeData.length) return { line_types: [], sample_positions: [], total_lines: 0 };

      return {
        line_types: routeData.map(segment => ({
          type: segment.type,
          coordinates: segment.coordinates
        })),
        sample_positions: routeData.map(segment => segment.coordinates),
        total_lines: routeData.length
      };
    }, [routeData]);

    return (
      <div className="route-map">
        <MapContainer 
          center={center} 
          zoom={15} 
          style={{ height: '400px', width: '100%' }}
          key={`${center[0]}-${center[1]}`} // Force re-render when center changes
        >
          <TileLayer
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          />
          {processedSegments.line_types.map((segment, index) => (
            <Polyline
              key={index}
              positions={segment.coordinates}
              pathOptions={{
                color: segment.type === 'fast' ? '#4CAF50' : '#FF5252',
                weight: 3
              }}
            >
              <MapTooltip>
                {`${segment.type.charAt(0).toUpperCase() + segment.type.slice(1)} Segment`}
              </MapTooltip>
            </Polyline>
          ))}
        </MapContainer>
      </div>
    );
  };

  const PaceAnalysis = ({ results, paceZones, elevationImpact }) => {
    if (!results || !paceZones) return null;

    return (
      <div className="pace-analysis">
        <h3>Pace Analysis</h3>
        
        {/* Pace Zones */}
        <div className="pace-zones">
          <h4>Recommended Training Paces</h4>
          {Object.entries(paceZones).map(([zone, data]) => (
            <div key={zone} className="pace-zone-item">
              <h5>{zone}</h5>
              <p className="pace-range">
                {data.range[0].toFixed(1)} - {data.range[1].toFixed(1)} min/mile
              </p>
              <p className="pace-description">{data.description}</p>
            </div>
          ))}
        </div>

        {/* Elevation vs Pace Chart */}
        <div className="elevation-pace-chart">
          <h4>Elevation Impact on Pace</h4>
          <Line
            data={{
              labels: elevationImpact.map((_, i) => i + 1),
              datasets: [
                {
                  label: 'Pace',
                  data: elevationImpact.map(d => d.pace),
                  borderColor: 'rgb(75, 192, 192)',
                  yAxisID: 'y'
                },
                {
                  label: 'Elevation Change',
                  data: elevationImpact.map(d => d.elevation_change),
                  borderColor: 'rgb(153, 102, 255)',
                  yAxisID: 'y1'
                }
              ]
            }}
            options={{
              responsive: true,
              scales: {
                y: {
                  title: { display: true, text: 'Pace (min/mile)' }
                },
                y1: {
                  position: 'right',
                  title: { display: true, text: 'Elevation Change (ft)' }
                }
              }
            }}
          />
        </div>
      </div>
    );
  };

  const RunHistory = ({ runs, onCompareRuns, onRunDeleted }) => {
    console.log("Run history data with pace limits:", runs);

    // Debug the first few runs to see exact pace_limit values
    if (runs && runs.length > 0) {
      console.log("First run pace_limit:", runs[0].pace_limit);
      console.log("First run pace_limit type:", typeof runs[0].pace_limit);
      console.log("First run data:", runs[0].data);
    }

    // Sort runs by date in descending order (newest first)
    const sortedRuns = [...runs].sort((a, b) => {
      return new Date(b.date) - new Date(a.date);
    });

    // Function to extract pace limit either from run.pace_limit or from run.data.pace_limit
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
      return null;
    };

    // Add safety check for missing data
    const safeNumber = (value, decimals = 2) => {
      if (typeof value === 'string') {
        value = parseFloat(value);
      }
      return typeof value === 'number' && !isNaN(value) ? value.toFixed(decimals) : 'N/A';
    };

    // Helper function to get distance from run data
    const getRunDistance = (run) => {
      // Try different possible locations of the distance data
      const possibleDistances = [
        run.distance,  // This is what the server is sending
        run.total_distance,
        typeof run.data === 'string' ? JSON.parse(run.data)?.total_distance : run.data?.total_distance
      ];

      // Return the first valid number found
      return possibleDistances.find(d => typeof d === 'number' && !isNaN(d));
    };

    // Find the selected run
    const selectedRun = useMemo(() => {
      return runs.find(run => run.id === selectedRunId);
    }, [runs, selectedRunId]);

    // Handle row click to show more details
    const handleRowClick = (runId) => {
      setSelectedRunId(runId === selectedRunId ? null : runId);
    };

    if (!runs || runs.length === 0) {
      return (
        <div className="run-history">
          <h2>Run History</h2>
          <p>No runs available</p>
        </div>
      );
    }

    return (
      <div className="run-history">
        <h2>Run History</h2>
        <div className="history-controls">
          <button 
            onClick={() => window.location.reload(true)}
            className="refresh-button"
          >
            Refresh Data
          </button>
        </div>
        {error && <div className="error-message">{error}</div>}
        <table className="history-table">
          <thead>
            <tr>
              <th>Select</th>
              <th>Date</th>
              <th>Distance</th>
              <th>Avg Pace</th>
              <th>Avg HR</th>
              <th>Target Pace</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {sortedRuns.map(run => (
              <tr 
                key={run.id} 
                onClick={() => handleRowClick(run.id)} 
                className={selectedRunId === run.id ? 'selected-run' : ''}
              >
                <td>
                  <input
                    type="checkbox"
                    checked={selectedRunId === run.id}
                    onChange={(e) => e.stopPropagation()}
                  />
                </td>
                <td>{new Date(run.date).toLocaleDateString()}</td>
                <td>{safeNumber(getRunDistance(run))} mi</td>
                <td>{safeNumber(run.avg_pace, 1)} min/mi</td>
                <td>{safeNumber(run.avg_hr, 0)} bpm</td>
                <td>
                  {(getPaceLimit(run)) ? 
                    (() => {
                      const paceLimit = getPaceLimit(run);
                      const mins = Math.floor(paceLimit);
                      const secs = Math.round((paceLimit - mins) * 60);
                      return `${mins}:${secs < 10 ? '0' + secs : secs} min/mi`;
                    })() : 
                    'N/A'}
                </td>
                <td>
                  <button 
                    className="delete-button"
                    onClick={(e) => {
                      e.stopPropagation();
                      onRunDeleted(run.id);
                    }}
                  >
                    🗑️
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        
        {/* Add the pace improvement chart when a run is selected */}
        {selectedRun && (
          <PaceProgressChart 
            runs={runs} 
            currentRun={selectedRun} 
          />
        )}
      </div>
    );
  };

  const RunComparison = ({ runs, onClose }) => {
    if (!runs || runs.length !== 2) {
      return <div>Please select two runs to compare</div>;
    }

    const [run1, run2] = runs;

    // Add debug logging
    console.log('Raw run data:', {
      run1: {
        date: run1.date,
        total_distance: run1.total_distance,
        avg_pace: run1.avg_pace,
        avg_hr: run1.avg_hr,
        data: run1.data
      },
      run2: {
        date: run2.date,
        total_distance: run2.total_distance,
        avg_pace: run2.avg_pace,
        avg_hr: run2.avg_hr,
        data: run2.data
      }
    });

    // Safely parse the data with error handling
    let run1Data, run2Data;
    try {
      run1Data = typeof run1.data === 'string' ? JSON.parse(run1.data) : run1.data;
      run2Data = typeof run2.data === 'string' ? JSON.parse(run2.data) : run2.data;

      // Add debug logging for parsed data
      console.log('Parsed run data:', {
        run1Data: {
          total_distance: run1Data.total_distance,
          fast_distance: run1Data.fast_distance,
          slow_distance: run1Data.slow_distance
        },
        run2Data: {
          total_distance: run2Data.total_distance,
          fast_distance: run2Data.fast_distance,
          slow_distance: run2Data.slow_distance
        }
      });
    } catch (error) {
      console.error('Error parsing run data:', error);
      return <div>Error loading run data</div>;
    }

    // Add safety checks for required data
    if (!run1Data || !run2Data) {
      return <div>Missing run data</div>;
    }

    const safeNumber = (value, decimals = 2) => {
      return typeof value === 'number' && !isNaN(value) ? value.toFixed(decimals) : 'N/A';
    };

    // Try to get total distance from either the run object or the parsed data
    const getTotalDistance = (run, runData) => {
      if (typeof run.total_distance === 'number') return run.total_distance;
      if (typeof runData.total_distance === 'number') return runData.total_distance;
      return null;
    };

    const run1Distance = getTotalDistance(run1, run1Data);
    const run2Distance = getTotalDistance(run2, run2Data);

    console.log('Calculated distances:', { run1Distance, run2Distance });

    return (
      <div className="run-comparison">
        <div className="comparison-header">
          <h2>Run Comparison</h2>
          <div className="comparison-controls">
            <button onClick={onClose} className="back-button">
              Back to Runs
            </button>
            <button onClick={onClose} className="close-button">×</button>
          </div>
        </div>

        <div className="comparison-grid">
          <div className="comparison-column">
            <h3>Run 1: {new Date(run1.date).toLocaleDateString()}</h3>
            <div className="comparison-stats">
              <div className="stat-item">
                <label>Total Distance:</label>
                <span>{safeNumber(run1Distance)} mi</span>
              </div>
              <div className="stat-item">
                <label>Average Pace:</label>
                <span>{safeNumber(run1.avg_pace, 1)} min/mi</span>
              </div>
              <div className="stat-item">
                <label>Average HR:</label>
                <span>{safeNumber(run1.avg_hr, 0)} bpm</span>
              </div>
              <div className="stat-item">
                <label>Fast Distance:</label>
                <span>
                  {safeNumber(run1Data.fast_distance)} mi 
                  ({safeNumber(run1Data.percentage_fast, 1)}%)
                </span>
              </div>
              <div className="stat-item">
                <label>Slow Distance:</label>
                <span>
                  {safeNumber(run1Data.slow_distance)} mi 
                  ({safeNumber(run1Data.percentage_slow, 1)}%)
                </span>
              </div>
            </div>
          </div>

          <div className="comparison-column">
            <h3>Run 2: {new Date(run2.date).toLocaleDateString()}</h3>
            <div className="comparison-stats">
              <div className="stat-item">
                <label>Total Distance:</label>
                <span>{safeNumber(run2Distance)} mi</span>
              </div>
              <div className="stat-item">
                <label>Average Pace:</label>
                <span>{safeNumber(run2.avg_pace, 1)} min/mi</span>
              </div>
              <div className="stat-item">
                <label>Average HR:</label>
                <span>{safeNumber(run2.avg_hr, 0)} bpm</span>
              </div>
              <div className="stat-item">
                <label>Fast Distance:</label>
                <span>
                  {safeNumber(run2Data.fast_distance)} mi 
                  ({safeNumber(run2Data.percentage_fast, 1)}%)
                </span>
              </div>
              <div className="stat-item">
                <label>Slow Distance:</label>
                <span>
                  {safeNumber(run2Data.slow_distance)} mi 
                  ({safeNumber(run2Data.percentage_slow, 1)}%)
                </span>
              </div>
            </div>
          </div>
        </div>

        <div className="comparison-charts">
          <div className="chart-container">
            <h4>Pace Comparison</h4>
            <Bar 
              data={preparePaceComparisonData(run1, run1Data, run2, run2Data)} 
              options={comparisonChartOptions} 
            />
          </div>
          <div className="chart-container">
            <h4>Heart Rate Comparison</h4>
            <Bar 
              data={prepareHRComparisonData(run1Data, run2Data)} 
              options={comparisonChartOptions} 
            />
          </div>
        </div>
      </div>
    );
  };

  // Update the handleCompareRuns function
  const handleCompareRuns = async (selectedRunIds) => {
    try {
      console.log('Comparing runs:', selectedRunIds);
      const runsToCompare = runHistory.filter(run => selectedRunIds.includes(run.id));
      
      if (runsToCompare.length !== 2) {
        setError('Please select exactly 2 runs to compare');
        return;
      }

      setComparedRuns(runsToCompare);
      setCompareMode(true);
    } catch (error) {
      console.error('Error comparing runs:', error);
      setError('Failed to compare runs');
    }
  };

  const handleRunDeleted = async (runId) => {
    try {
      console.log(`Attempting to delete run ${runId}`);
      const response = await fetch(`${API_URL}/runs/${runId}`, {
        method: 'DELETE',
        credentials: 'include'
      });

      if (response.status === 401) {
        setUserId(null);
        setError('Please log in to delete runs');
        return;
      }

      // Refresh the run history after successful deletion
      console.log(`Successfully deleted run ${runId}`);
      fetchRunHistory();
    } catch (error) {
      console.error('Error deleting run:', error);
      setError(error.message || 'Failed to delete run');
    }
  };

  const handleLogin = async (userId, username) => {
    console.log('Login successful, setting state:', { userId, username });
    setUserId(userId);
    setUsername(username);
    setIsAuthenticated(true);
    // Wait a moment for session to be set before fetching data
    await new Promise(resolve => setTimeout(resolve, 100));
    fetchRunHistory();
  };

  const handleLogout = async () => {
    try {
      await fetch(`${API_URL}/auth/logout`, {
        method: 'POST',
        credentials: 'include'
      });
      setUserId(null);
      setUsername('');
      setIsAuthenticated(false);
      setUser(null);
    } catch (error) {
      console.error('Logout error:', error);
    }
  };

  // Add a helper function for safe number formatting
  const formatNumber = (value, decimals = 2) => {
    return (value || 0).toFixed(decimals);
  };

  return (
    <ThemeProvider>
      <TableProvider>
        <div className="App">
          {loading && <LoadingSpinner />}
          {error && <ErrorMessage message={error} />}
          
          {!isAuthenticated ? (
            <LoginForm onLogin={handleLogin} />
          ) : (
            <>
              <header className="App-header">
                <div className="header-controls">
                  <ProfileMenu 
                    username={username}
                    age={age}
                    restingHR={restingHR}
                    onSave={handleProfileSave}
                    onLogout={handleLogout}
                  />
                </div>
                <h1>{runDate ? `Running Analysis for ${runDate}` : 'Running Analysis'}</h1>
                <p className="subtitle">Upload your GPX file to analyze pace and heart rate data</p>
              </header>
              
              <main className="App-main">
                {saveStatus && (
                  <div className="save-status">
                    {saveStatus}
                  </div>
                )}
                
                <div className="upload-section">
                  <form onSubmit={handleSubmit} className="analysis-form">
                    <div className="file-upload">
                      <label htmlFor="file" className="file-upload-label">
                        <div className="file-upload-box">
                          <span className="upload-icon">📁</span>
                          <span className="upload-text">
                            {fileName || 'Choose GPX file'}
                          </span>
                        </div>
                      </label>
                      <input
                        type="file"
                        id="file"
                        accept=".gpx"
                        onChange={handleFileChange}
                        style={{ display: 'none' }}
                      />
                    </div>
                    
                    <div className="form-group">
                      <label htmlFor="paceLimit">
                        Target Pace (min/mile)
                        <InfoTooltip text="This is the pace threshold that determines fast vs. slow segments" />
                      </label>
                      <input
                        type="number"
                        id="paceLimit"
                        value={paceLimit || ''}
                        onChange={(e) => {
                          const value = parseFloat(e.target.value);
                          setPaceLimit(isNaN(value) ? 10.0 : value);
                        }}
                        step="0.1"
                        min="4"
                        max="20"
                      />
                    </div>
                    
                    <button type="submit" disabled={loading || !selectedFile}>
                      {loading ? <LoadingSpinner /> : 'Analyze Run'}
                    </button>
                  </form>
                </div>

                {loading ? (
                  <LoadingOverlay />
                ) : results && (
                  <div className="results">
                    <h2>Analysis Results</h2>
                    
                    <div className="results-grid">
                      <div className="result-item">
                        <h3>Total Distance</h3>
                        <p className="result-value">{formatNumber(results?.total_distance || 0)}</p>
                        <p className="result-unit">miles</p>
                        <div className="hr-item">
                          <p className="result-label">Overall Heart Rate</p>
                          <p className="result-value-secondary">{formatNumber(results?.avg_hr_all || 0, 0)}</p>
                          <p className="result-unit">bpm</p>
                        </div>
                      </div>
                      
                      <div className="result-item">
                        <h3>Fast Distance</h3>
                        <p className="result-value">{formatNumber(results?.fast_distance || 0)}</p>
                        <p className="result-unit">miles</p>
                        <p className="result-percentage">
                          ({formatNumber(results?.percentage_fast || 0, 1)}% of total)
                        </p>
                        <div className="avg-pace">
                          <p className="result-label">Average Pace</p>
                          <p className="result-value-secondary">
                            {formatTime(calculateAveragePace(results?.fast_segments || []))}
                          </p>
                          <p className="result-unit">/mile</p>
                        </div>
                      </div>

                      <div className="result-item">
                        <h3>Slow Distance</h3>
                        <p className="result-value">{formatNumber(results?.slow_distance || 0)}</p>
                        <p className="result-unit">miles</p>
                        <p className="result-percentage">
                          ({formatNumber(results?.percentage_slow || 0, 1)}% of total)
                        </p>
                        <div className="avg-pace">
                          <p className="result-label">Average Pace</p>
                          <p className="result-value-secondary">
                            {formatTime(calculateAveragePace(results?.slow_segments || []))}
                          </p>
                          <p className="result-unit">/mile</p>
                        </div>
                      </div>
                    </div>

                    <div className="segments">
                      {console.log("Results object:", results)}
                      {console.log("Training zones:", results?.training_zones)}
                      
                      {results?.training_zones && (
                        console.log("Attempting to render training zones") ||
                        <TrainingZones zones={results.training_zones} />
                      )}

                      <h3>Route Map</h3>
                      <RouteMap 
                        routeData={results?.route_data || []} 
                        fastSegments={results?.fast_segments || []} 
                        slowSegments={results?.slow_segments || []} 
                      />
                      
                      {results && results.pace_zones && (
                        <PaceAnalysis 
                          results={results}
                          paceZones={results.pace_zones}
                          elevationImpact={results.elevation_impact}
                        />
                      )}

                      {/* Add the AdvancedMetrics component */}
                      <AdvancedMetrics 
                        vo2max={results.vo2max}
                        trainingLoad={results.training_load}
                        recoveryTime={results.recovery_time}
                      />

                      {/* Add Mile Splits listing */}
                      <CollapsibleTable
                        title={`Mile Splits (${results?.mile_splits?.length || 0})`}
                        id="mile-splits"
                      >
                        <table>
                          <thead>
                            <tr>
                              <th>Mile #</th>
                              <th>Distance</th>
                              <th>Pace</th>
                              <th>Avg HR</th>
                            </tr>
                          </thead>
                          <tbody>
                            {results?.mile_splits?.map((split, index) => (
                              <tr key={index}>
                                <td>{index + 1}</td>
                                <td>{formatNumber(split.distance)} mi</td>
                                <td>{formatTime(split.pace)} /mi</td>
                                <td>{formatNumber(split.avg_hr, 0)} bpm</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </CollapsibleTable>

                      <h3>Mile Splits</h3>
                      <MileSplits splits={results?.mile_splits || []} />
                      
                      <CollapsibleTable 
                        title={`Fast Segments (${results?.fast_segments?.length || 0})`} 
                        id="fast-segments"
                      >
                        <table>
                          <thead>
                            <tr>
                              <th>Segment</th>
                              <th>Start Time</th>
                              <th>End Time</th>
                              <th>Distance</th>
                              <th>Pace</th>
                              <th>Best Pace</th>
                              <th>Heart Rate</th>
                            </tr>
                          </thead>
                          <tbody>
                            {results?.fast_segments?.map((segment, index) => (
                              <tr key={index}>
                                <td>{index + 1}</td>
                                <td>{new Date(segment.start_time).toLocaleTimeString()}</td>
                                <td>{new Date(segment.end_time).toLocaleTimeString()}</td>
                                <td>{formatNumber(segment.distance)} mi</td>
                                <td>{formatTime(segment.pace)} /mi</td>
                                <td>{segment.best_pace ? formatTime(segment.best_pace) : formatTime(segment.pace)} /mi</td>
                                <td>{formatNumber(segment.avg_hr)} bpm</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </CollapsibleTable>

                      <CollapsibleTable 
                        title={`Slow Segments (${results?.slow_segments?.length || 0})`} 
                        id="slow-segments"
                      >
                        <table>
                          <thead>
                            <tr>
                              <th>Segment</th>
                              <th>Start Time</th>
                              <th>End Time</th>
                              <th>Distance</th>
                              <th>Pace</th>
                              <th>Best Pace</th>
                              <th>Heart Rate</th>
                            </tr>
                          </thead>
                          <tbody>
                            {results?.slow_segments?.map((segment, index) => (
                              <tr key={index}>
                                <td>{index + 1}</td>
                                <td>{new Date(segment.start_time).toLocaleTimeString()}</td>
                                <td>{new Date(segment.end_time).toLocaleTimeString()}</td>
                                <td>{formatNumber(segment.distance)} mi</td>
                                <td>{formatTime(segment.pace)} /mi</td>
                                <td>{segment.best_pace ? formatTime(segment.best_pace) : formatTime(segment.pace)} /mi</td>
                                <td>{formatNumber(segment.avg_hr)} bpm</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </CollapsibleTable>
                    </div>

                    {results && results.pace_zones && (
                      <PaceAnalysis 
                        results={results}
                        paceZones={results.pace_zones}
                        elevationImpact={results.elevation_impact}
                      />
                    )}

                    {/* Add Race Predictions */}
                    {results?.race_predictions && (
                      <RacePredictions predictions={results.race_predictions} />
                    )}
                  </div>
                )}

                {/* Move RunHistory outside of any conditional rendering */}
                <div className="history-section">
                  {!compareMode ? (
                    <RunHistory 
                      runs={runHistory} 
                      onCompareRuns={handleCompareRuns}
                      onRunDeleted={handleRunDeleted}
                    />
                  ) : (
                    <RunComparison 
                      runs={comparedRuns}
                      onClose={() => setCompareMode(false)}
                    />
                  )}
                </div>
              </main>
            </>
          )}
        </div>
      </TableProvider>
    </ThemeProvider>
  );
}

export default App;