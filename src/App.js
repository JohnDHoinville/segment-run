import React, { useState, createContext, useContext, useEffect, useRef } from 'react';
import './App.css';
import LoadingSpinner from './components/LoadingSpinner';
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
  Popup,
  Circle,
  CircleMarker
} from 'react-leaflet';
import 'leaflet/dist/leaflet.css';

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
  const [editAge, setEditAge] = useState(age);
  const [editRestingHR, setEditRestingHR] = useState(restingHR);
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const menuRef = useRef(null);
  const API_URL = 'http://localhost:5001';

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
      const response = await fetch(`${API_URL}/profile`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          age: parseInt(editAge),
          resting_hr: parseInt(editRestingHR)
        }),
      });

      if (response.ok) {
        onSave(editAge, editRestingHR);
        setIsOpen(false);
      } else {
        const error = await response.json();
        console.error('Failed to save profile:', error);
        alert('Failed to save profile. Please try again.');
      }
    } catch (error) {
      console.error('Error saving profile:', error);
      alert('Error saving profile. Please try again.');
    }
  };

  const handleChangePassword = async () => {
    if (newPassword !== confirmPassword) {
      setError('New passwords do not match');
      return;
    }

    try {
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
        setError('');
        alert('Password updated successfully');
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
        <span className="username">{username}</span>
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
            <h3>👤 {username}</h3>
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

          {error && <div className="error-message">{error}</div>}

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
              <div className="form-group">
                <label htmlFor="profileAge">Age:</label>
                <input
                  type="number"
                  id="profileAge"
                  value={editAge}
                  onChange={(e) => setEditAge(e.target.value)}
                  min="0"
                  max="120"
                />
              </div>
              <div className="form-group">
                <label htmlFor="profileRestingHR">Resting Heart Rate (bpm):</label>
                <input
                  type="number"
                  id="profileRestingHR"
                  value={editRestingHR}
                  onChange={(e) => setEditRestingHR(e.target.value)}
                  min="30"
                  max="200"
                />
              </div>
              <button onClick={handleSave} className="save-button">Save Profile</button>
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
                />
              </div>
              <div className="form-group">
                <label htmlFor="newPassword">New Password:</label>
                <input
                  type="password"
                  id="newPassword"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                />
              </div>
              <div className="form-group">
                <label htmlFor="confirmPassword">Confirm New Password:</label>
                <input
                  type="password"
                  id="confirmPassword"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                />
              </div>
              <button onClick={handleChangePassword} className="save-button">Change Password</button>
            </div>
          )}

          <div className="profile-footer">
            <button onClick={onLogout} className="logout-button">
              Logout
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

// Add LoginForm component after ProfileMenu
const LoginForm = ({ onLogin }) => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [isRegistering, setIsRegistering] = useState(false);
  const [error, setError] = useState('');
  const API_URL = 'http://localhost:5001';

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    try {
      const endpoint = isRegistering ? '/auth/register' : '/auth/login';
      console.log('Attempting to fetch:', `${API_URL}${endpoint}`);
      
      const response = await fetch(`${API_URL}${endpoint}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        credentials: 'include',
        body: JSON.stringify({
          username: username.trim(),
          password: password
        })
      });

      console.log('Response received:', response.status);
      const data = await response.json();

      if (response.ok) {
        onLogin(data.user_id, username);
      } else {
        setError(data.error || 'Authentication failed');
      }
    } catch (error) {
      console.error('Login error details:', error);
      setError('Network error. Please check if the server is running.');
    }
  };

  return (
    <div className="login-container">
      <h2>{isRegistering ? 'Register' : 'Login'}</h2>
      {error && <div className="error-message">{error}</div>}
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label htmlFor="username">Username:</label>
          <input
            type="text"
            id="username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
          />
        </div>
        <div className="form-group">
          <label htmlFor="password">Password:</label>
          <input
            type="password"
            id="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </div>
        <div className="form-actions">
          <button type="submit">
            {isRegistering ? 'Register' : 'Login'}
          </button>
          <button 
            type="button"
            onClick={() => setIsRegistering(!isRegistering)}
          >
            {isRegistering ? 'Switch to Login' : 'Switch to Register'}
          </button>
        </div>
      </form>
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

function App() {
  const API_URL = 'http://localhost:5001';

  const [selectedFile, setSelectedFile] = useState(null);
  const [paceLimit, setPaceLimit] = useState('');
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [runDate, setRunDate] = useState(null);
  const [age, setAge] = useState('');
  const [restingHR, setRestingHR] = useState('');
  const [mapLayers, setMapLayers] = useState({
    pace: true,
    elevation: true,
    heartRate: true
  });
  const [runHistory, setRunHistory] = useState([]);
  const [compareMode, setCompareMode] = useState(false);
  const [comparedRuns, setComparedRuns] = useState([]);
  const [saveStatus, setSaveStatus] = useState('');
  const [userId, setUserId] = useState(null);
  const [username, setUsername] = useState('');

  // Add near the top of the App component
  useEffect(() => {
    console.log('Run History State:', {
      isAuthenticated: !!userId,
      userId,
      runHistory,
      compareMode,
      comparedRuns
    });
  }, [userId, runHistory, compareMode, comparedRuns]);

  // Update fetchRunHistory with more logging
  const fetchRunHistory = async () => {
    if (!userId) {
      console.log('No userId, skipping fetch');
      return;
    }

    try {
      console.log('Fetching run history...');
      const response = await fetch(`${API_URL}/runs`, {
        credentials: 'include'
      });
      
      if (response.status === 401) {
        console.log('Unauthorized, clearing history');
        setError('Please log in to view run history');
        return;
      }

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      console.log('Received run history:', data);
      setRunHistory(data);
    } catch (error) {
      console.error('Error fetching run history:', error);
      setError('Failed to load run history');
    }
  };

  // Update useEffect to fetch run history when userId changes
  useEffect(() => {
    if (userId) {
      fetchRunHistory();
    }
  }, [userId]);

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
    setLoading(true);
    setSaveStatus('');

    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('paceLimit', paceLimit);
    formData.append('age', age);
    formData.append('restingHR', restingHR);

    try {
      console.log('Sending request to:', `${API_URL}/analyze`);
      const response = await fetch(`${API_URL}/analyze`, {
        method: 'POST',
        credentials: 'include',
        body: formData
      });

      if (response.status === 401) {
        console.log('Session expired or invalid. Redirecting to login...');
        setError('Please log in to analyze runs');
        setLoading(false);
        return;
      }

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      console.log('Received data:', data);
      setResults(data);
      if (data.saved) {
        setSaveStatus('Run saved successfully');
        // Fetch updated run history after saving new run
        fetchRunHistory();
      }
    } catch (error) {
      console.error('Error:', error);
      setError('Failed to analyze run. Please try again.');
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

  // Update Mile Splits component with labels
  const MileSplits = ({ splits }) => {
    if (!splits || splits.length === 0) return null;

    return (
      <div className="mile-splits">
        <h4>Mile Splits</h4>
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
                <td>{split.split_time.toFixed(2)} min</td>
                <td>{split.split_pace.toFixed(2)} min/mi</td>
                <td>{Math.round(split.avg_hr)} bpm</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  };

  // Add this new component
  const RouteMap = ({ segments }) => {
    const [activeLayers, setActiveLayers] = useState({
      pace: true,
      elevation: true,
      heartRate: true
    });

    if (!segments || !segments.route_data) {
      console.log('Missing required data:', { segments });
      return null;
    }

    // Debug logging
    const paceLimit = Number(segments.pace_limit);
    console.log('Route Analysis:', {
      pace_limit: paceLimit,
      total_points: segments.route_data.length,
      first_point: segments.route_data[0]?.start_point
    });

    // Create lines based on pace threshold
    const lines = [];
    let currentLine = {
      positions: [],
      type: 'slow',  // Start with slow
      pace: 0,
      avgHR: 0,
      elevation: 0,
      hrCount: 0,
      pointCount: 0
    };

    // Ensure we have valid coordinates for the first point
    const firstPoint = segments.route_data[0]?.start_point;
    const defaultCenter = [42.528866, -83.281525];  // Default center
    const center = firstPoint && !isNaN(firstPoint.lat) && !isNaN(firstPoint.lon) ? 
      [Number(firstPoint.lat), Number(firstPoint.lon)] : 
      defaultCenter;

    console.log('Map center:', center);

    segments.route_data.forEach((point, index) => {
      // Get coordinates from start_point
      const lat = Number(point.start_point?.lat);
      const lon = Number(point.start_point?.lon);
      if (isNaN(lat) || isNaN(lon)) {
        console.log('Invalid coordinates:', point.start_point);
        return;  // Skip this point
      }

      const pointPace = Number(point.pace);
      const isFast = !isNaN(pointPace) && !isNaN(paceLimit) && pointPace <= paceLimit;

      // Start first line
      if (index === 0) {
        currentLine.type = isFast ? 'fast' : 'slow';
      }

      // Check if pace type changed
      if ((isFast && currentLine.type === 'slow') || (!isFast && currentLine.type === 'fast')) {
        // End current line
        if (currentLine.positions.length > 0) {
          currentLine.pace = currentLine.pointCount > 0 ? currentLine.pace / currentLine.pointCount : 0;
          currentLine.avgHR = currentLine.hrCount > 0 ? currentLine.avgHR / currentLine.hrCount : 0;
          currentLine.elevation = currentLine.pointCount > 0 ? currentLine.elevation / currentLine.pointCount : 0;
          lines.push({...currentLine});
        }
        // Start new line
        currentLine = {
          positions: [[lat, lon]],
          type: isFast ? 'fast' : 'slow',
          pace: pointPace || 0,
          avgHR: point.hr || 0,
          elevation: point.elevation || 0,
          hrCount: point.hr ? 1 : 0,
          pointCount: 1
        };
      } else {
        // Continue current line
        currentLine.positions.push([lat, lon]);
        currentLine.pace += pointPace || 0;
        currentLine.avgHR += point.hr || 0;
        currentLine.elevation += point.elevation || 0;
        if (point.hr) currentLine.hrCount++;
        currentLine.pointCount++;
      }
    });

    // Add the last line
    if (currentLine.positions.length > 0) {
      currentLine.pace = currentLine.pointCount > 0 ? currentLine.pace / currentLine.pointCount : 0;
      currentLine.avgHR = currentLine.hrCount > 0 ? currentLine.avgHR / currentLine.hrCount : 0;
      currentLine.elevation = currentLine.pointCount > 0 ? currentLine.elevation / currentLine.pointCount : 0;
      lines.push({...currentLine});
    }

    console.log('Line segments:', {
      total_lines: lines.length,
      line_types: lines.map(l => l.type),
      sample_positions: lines[0]?.positions.slice(0, 2)
    });

    return (
      <div className="map-container">
        <div className="map-controls">
          <div className="layer-toggles">
            <label>
              <input
                type="checkbox"
                checked={activeLayers.pace}
                onChange={(e) => setActiveLayers({...activeLayers, pace: e.target.checked})}
              />
              Pace
            </label>
            <label>
              <input
                type="checkbox"
                checked={activeLayers.elevation}
                onChange={(e) => setActiveLayers({...activeLayers, elevation: e.target.checked})}
              />
              Elevation
            </label>
            <label>
              <input
                type="checkbox"
                checked={activeLayers.heartRate}
                onChange={(e) => setActiveLayers({...activeLayers, heartRate: e.target.checked})}
              />
              Heart Rate
            </label>
          </div>
        </div>
        
        <MapContainer center={center} zoom={14} style={{ height: '400px', width: '100%' }}>
          <TileLayer
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          />
          {activeLayers.pace && lines.map((line, index) => (
            <Polyline
              key={index}
              positions={line.positions}
              pathOptions={{
                color: line.type === 'fast' ? 'var(--fast-color)' : 'var(--slow-color)',
                weight: 4
              }}
            >
              <MapTooltip sticky>
                <div>
                  <strong>Pace:</strong> {line.pace ? line.pace.toFixed(2) : 'N/A'} min/mile
                  {activeLayers.heartRate && <div><strong>HR:</strong> {line.avgHR ? Math.round(line.avgHR) : 'N/A'} bpm</div>}
                  {activeLayers.elevation && <div><strong>Elevation:</strong> {line.elevation ? line.elevation.toFixed(0) : 'N/A'} ft</div>}
                </div>
              </MapTooltip>
            </Polyline>
          ))}
        </MapContainer>
        <div className="map-legend">
          <div className="legend-item">
            <div className="legend-color legend-fast"></div>
            <span>Fast Pace (≤ {segments.pace_limit} min/mile)</span>
          </div>
          <div className="legend-item">
            <div className="legend-color legend-slow"></div>
            <span>Slow Pace ({'>'}  {segments.pace_limit} min/mile)</span>
          </div>
        </div>
      </div>
    );
  };

  const TrainingZones = ({ zones }) => {
    if (!zones) return null;

    return (
      <div className="training-zones">
        <h3>Heart Rate Training Zones</h3>
        <div className="zones-container">
          {Object.entries(zones).map(([zone, data]) => (
            <div key={zone} className="zone-item" style={{ borderLeft: `4px solid ${data.color}` }}>
              <div className="zone-header">
                <h4>{zone} - {data.name}</h4>
                <span className="zone-range">
                  {data.range[0]}-{data.range[1]} bpm
                </span>
              </div>
              <div className="zone-stats">
                <div className="zone-percentage">
                  {data.percentage.toFixed(1)}%
                  <div 
                    className="percentage-bar" 
                    style={{ 
                      width: `${data.percentage}%`,
                      backgroundColor: data.color 
                    }} 
                  />
                </div>
                <div className="zone-time">
                  {Math.floor(data.time / 60)}:{(data.time % 60).toString().padStart(2, '0')}
                </div>
              </div>
              <p className="zone-description">{data.description}</p>
            </div>
          ))}
        </div>
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
    const [selectedRuns, setSelectedRuns] = useState([]);
    const [error, setError] = useState('');

    // Sort runs by date in descending order (newest first)
    const sortedRuns = [...(runs || [])].sort((a, b) => {
      return new Date(b.date) - new Date(a.date);
    });

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

    const handleRowClick = (runId) => {
      setSelectedRuns(prev => {
        if (prev.includes(runId)) {
          return prev.filter(id => id !== runId);
        }
        if (prev.length < 2) {
          return [...prev, runId];
        }
        return prev;
      });
    };

    const handleCompare = () => {
      if (selectedRuns.length === 2) {
        onCompareRuns(selectedRuns);
      }
    };

    const handleDelete = async (runId) => {
      if (window.confirm('Are you sure you want to delete this run?')) {
        try {
          await onRunDeleted(runId);
          setSelectedRuns(prev => prev.filter(id => id !== runId));
        } catch (error) {
          setError(error.message || 'Failed to delete run');
        }
      }
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
            onClick={handleCompare}
            disabled={selectedRuns.length !== 2}
            className="compare-button"
          >
            Compare Selected Runs ({selectedRuns.length}/2)
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
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {sortedRuns.map(run => {
              const distance = getRunDistance(run);
              
              return (
                <tr 
                  key={run.id}
                  className={selectedRuns.includes(run.id) ? 'selected' : ''}
                >
                  <td>
                    <input
                      type="checkbox"
                      checked={selectedRuns.includes(run.id)}
                      onChange={() => handleRowClick(run.id)}
                      onClick={(e) => e.stopPropagation()}
                    />
                  </td>
                  <td>{new Date(run.date).toLocaleDateString()}</td>
                  <td>{safeNumber(run.distance)} mi</td>
                  <td>{safeNumber(run.avg_pace, 1)} min/mi</td>
                  <td>{safeNumber(run.avg_hr, 0)} bpm</td>
                  <td>
                    <button 
                      className="delete-button"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDelete(run.id);
                      }}
                    >
                      🗑️
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
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

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `Failed to delete run: ${response.status}`);
      }

      // Refresh the run history after successful deletion
      console.log(`Successfully deleted run ${runId}`);
      fetchRunHistory();
    } catch (error) {
      console.error('Error deleting run:', error);
      setError(error.message || 'Failed to delete run');
    }
  };

  const handleLogin = (userId, username) => {
    setUserId(userId);
    setUsername(username);
  };

  const handleLogout = async () => {
    try {
      await fetch(`${API_URL}/auth/logout`, {
        method: 'POST',
        credentials: 'include'
      });
      setUserId(null);
    } catch (error) {
      console.error('Logout error:', error);
    }
  };

  return (
    <ThemeProvider>
      <div className="App">
        {loading && <LoadingSpinner />}
        {error && <div className="error-message">{error}</div>}
        
        {!userId ? (
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
                  
                  <div className="form-group">
                    <label htmlFor="age">Age (for HR zones):</label>
                    <input
                      type="number"
                      id="age"
                      value={age}
                      onChange={(e) => setAge(e.target.value)}
                      min="0"
                      max="120"
                      placeholder="Enter your age"
                      className="age-input"
                    />
                  </div>
                  
                  <div className="form-group">
                    <label htmlFor="restingHR">Resting Heart Rate (bpm):</label>
                    <input
                      type="number"
                      id="restingHR"
                      value={restingHR}
                      onChange={(e) => setRestingHR(e.target.value)}
                      min="30"
                      max="200"
                      placeholder="Enter resting heart rate"
                      className="hr-input"
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

              {results && !loading && (
                <div className="results">
                  <h2>Analysis Results</h2>
                  <div className="results-grid">
                    <div className="result-item">
                      <h3>Total Distance</h3>
                      <p className="result-value">{results.total_distance.toFixed(2)}</p>
                      <p className="result-unit">miles</p>
                      <div className="hr-item">
                        <p className="result-label">Overall Heart Rate</p>
                        <p className="result-value-secondary">{Math.round(results.avg_hr_all)}</p>
                        <p className="result-unit">bpm</p>
                      </div>
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
                      <div className="hr-item">
                        <p className="result-label">Average Heart Rate</p>
                        <p className="result-value-secondary">{Math.round(results.avg_hr_fast)}</p>
                        <p className="result-unit">bpm</p>
                      </div>
                    </div>

                    <div className="result-item">
                      <h3>Slow Distance</h3>
                      <p className="result-value">{results.slow_distance.toFixed(2)}</p>
                      <p className="result-unit">miles</p>
                      <p className="result-percentage">
                        ({results.percentage_slow.toFixed(1)}% of total)
                      </p>
                      <div className="avg-pace">
                        <p className="result-label">Average Pace</p>
                        <p className="result-value-secondary">
                          {(results.slow_segments.reduce((sum, segment) => sum + segment.pace, 0) / 
                            results.slow_segments.length).toFixed(1)}
                        </p>
                        <p className="result-unit">min/mile</p>
                      </div>
                      <div className="hr-item">
                        <p className="result-label">Average Heart Rate</p>
                        <p className="result-value-secondary">{Math.round(results.avg_hr_slow)}</p>
                        <p className="result-unit">bpm</p>
                      </div>
                    </div>
                  </div>

                  <div className="segments">
                    {results && results.training_zones && (
                      <TrainingZones zones={results.training_zones} />
                    )}

                    <h3>Route Map</h3>
                    <RouteMap segments={results} />
                    
                    <h3>Segment Analysis</h3>
                    <div className="chart-container">
                      <Bar data={prepareChartData(results)} options={chartOptions} />
                    </div>
                    <MileSplits splits={results.mile_splits} />
                    <div className="table-container">
                      <h4>Fast Segments</h4>
                      <table>
                        <thead>
                          <tr>
                            <th>Segment</th>
                            <th>Start Time</th>
                            <th>End Time</th>
                            <th>Distance</th>
                            <th>Avg Pace</th>
                            <th>Best Pace</th>
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
                              <td>{segment.best_pace ? segment.best_pace.toFixed(1) : segment.pace.toFixed(1)} min/mi</td>
                              <td>{Math.round(segment.avg_hr)} bpm</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>

                      <h4>Slow Segments</h4>
                      <table>
                        <thead>
                          <tr>
                            <th>Segment</th>
                            <th>Start Time</th>
                            <th>End Time</th>
                            <th>Distance</th>
                            <th>Avg Pace</th>
                            <th>Best Pace</th>
                            <th>Heart Rate</th>
                          </tr>
                        </thead>
                        <tbody>
                          {results.slow_segments.map((segment, index) => (
                            <tr key={index}>
                              <td>{index + 1}</td>
                              <td>{segment.start_time ? 
                                new Date(segment.start_time).toLocaleTimeString() : 'N/A'}</td>
                              <td>{segment.end_time ? 
                                new Date(segment.end_time).toLocaleTimeString() : 'N/A'}</td>
                              <td>{segment.distance.toFixed(2)} mi</td>
                              <td>{segment.pace.toFixed(1)} min/mi</td>
                              <td>{segment.best_pace ? segment.best_pace.toFixed(1) : segment.pace.toFixed(1)} min/mi</td>
                              <td>{Math.round(segment.avg_hr)} bpm</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>

                  {results && results.pace_zones && (
                    <PaceAnalysis 
                      results={results}
                      paceZones={results.pace_zones}
                      elevationImpact={results.elevation_impact}
                    />
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
    </ThemeProvider>
  );
}

export default App;