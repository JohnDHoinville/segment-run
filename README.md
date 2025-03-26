# Run Analysis Application

## Overview

Run Analysis is a comprehensive web application for runners to analyze their GPX data, track performance over time, and gain insights into their training. The application processes run data to provide detailed metrics, visualizations, and personalized training recommendations.

## Application Sections

### 1. User Authentication & Profile
- **Login/Register:** Secure user authentication system
- **User Profile:** Manage age, weight, resting heart rate, and other personal metrics
- **Theme Toggle:** Switch between light and dark mode for comfortable viewing

### 2. Run Analysis Dashboard
- **GPX Upload:** Upload and analyze GPX files from any GPS device
- **Pace Analysis:** Breakdown of fast and slow segments based on target pace
- **Heart Rate Zones:** Time spent in different heart rate training zones
- **Mile Splits:** Detailed pace information for each mile
- **Elevation Analysis:** Impact of elevation changes on pace
- **Route Map:** Interactive map showing the run route with color-coded pace segments
- **Advanced Metrics:** VO2max estimation, training load, and recovery time recommendations

### 3. Run History
- **History Table:** View all past runs with key metrics
- **Expandable Details:** Click to see fast segments and additional information
- **Run Comparison:** Select and compare two runs side-by-side
- **Run Deletion:** Remove unwanted entries from your history

### 4. Advanced Analysis Tools
- **Custom Segments:** Define and track specific portions of your routes over time
- **Pace Consistency:** Analyze how steady your pace is throughout your runs
- **Fatigue Analysis:** Track how your pace changes over the course of a run
- **Heart Rate vs. Pace Correlation:** Understand the relationship between effort and pace
- **Pace Progress Chart:** Track improvement in similar runs over time
- **Race Predictions:** Estimate race times for standard distances based on your data

## Technology Stack

### Frontend
- **React 18:** Component-based UI architecture
- **Chart.js 4:** Data visualization for pace, heart rate, and other metrics
- **Leaflet.js:** Interactive maps for route visualization
- **React-Chartjs-2:** React wrapper for Chart.js
- **React-Leaflet:** React components for Leaflet maps
- **CSS3:** Custom styling with responsive design
- **Context API:** State management for theme and table collapsing

### Backend
- **Flask 2.0:** Python web framework
- **SQLite:** Database for user and run storage
- **Flask-CORS:** Cross-origin resource sharing support
- **Python GPX Parser:** Custom GPX file processing
- **Werkzeug:** Security and authentication utilities
- **pytz/tzlocal:** Timezone handling

## Setup Instructions

### Prerequisites
- Python 3.8+ installed
- Node.js 14+ installed
- npm or yarn package manager
- Git (optional, for cloning the repository)

### Backend Setup
1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create and activate a virtual environment:
   ```bash
   # For Windows
   python -m venv venv
   venv\Scripts\activate

   # For macOS/Linux
   python -m venv venv
   source venv/bin/activate
   ```

3. Install required Python packages:
   ```bash
   pip install -r requirements.txt
   ```

4. Initialize the database (if needed):
   ```bash
   python database.py
   ```

### Frontend Setup
1. From the project root, install Node.js dependencies:
   ```bash
   npm install
   ```

## Running the Application

### Start the Backend Server
From the backend directory with the virtual environment activated:
```bash
python server.py
```
The backend will run on http://localhost:5001

### Start the Frontend Development Server
From the project root:
```bash
npm start
```
The frontend will run on http://localhost:3000

## User Guide

### Uploading and Analyzing a Run
1. Log in to your account
2. Click the "Upload GPX" button
3. Select a GPX file from your device
4. Enter your target pace (e.g., 9:30 min/mile)
5. Click "Analyze Run"

### Interpreting Results
- **Pace Analysis:** See segments where you ran faster or slower than your target
- **Mile Splits:** Review your pace for each mile
- **Heart Rate Zones:** Check your time spent in different training zones
- **Route Map:** Visualize your route with color-coded segments (green for fast, red for slow)
- **Advanced Metrics:** View VO2max, training load, and recovery recommendations

### Run History and Comparison
1. View your run history in the History table
2. Select two runs using the checkboxes
3. Click "Compare Runs" to see a side-by-side comparison

### Custom Segments
1. Navigate to the Custom Segments section
2. Define segments with start and end distances
3. Analyze how your performance changes over time for specific portions of your routes

## Troubleshooting

### Common Issues
- **Backend Connection Error:** Ensure the Flask server is running on port 5001
- **GPX File Error:** Verify your GPX file is in standard format
- **Missing Data:** Ensure your GPX file includes both time and location data
- **Slow Performance:** Large GPX files may take longer to process

### Support
For additional help or to report issues, please contact the development team or open an issue on the repository.

## License
This project is licensed under the MIT License - see the LICENSE file for details.