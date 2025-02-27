# Segment-Run: Running Analysis Application

## Overview

Segment-Run is a web application that helps runners analyze their GPX running data. It provides detailed insights into pace, heart rate, and elevation data, allowing runners to better understand their performance and track their progress over time.

## Features

- GPX file upload and analysis
- Pace-based segment analysis
- Heart rate zone tracking
- Elevation impact analysis
- Run history tracking and comparison
- Interactive route mapping
- Mile split analysis
- User authentication and profiles
- Dark/Light theme support

## Technology Stack

### Frontend

- React.js
- Chart.js for data visualization
- Leaflet.js for route mapping
- CSS3 with custom theming

### Backend

- Python Flask server
- SQLite database
- GPX parsing and analysis tools

## Installation

### Prerequisites

- Python 3.8 or higher
- Node.js 14.0 or higher
- npm or yarn package manager

### Backend Setup

1. Create and activate a virtual environment:

bash

cd backend

python -m venv venv

source venv/bin/activate # On Windows: venv\Scripts\activate

2. Install Python dependencies:

```bash
pip install -r requirements.txt
```

3. Initialize the database:

```bash
python database.py
```

4. Start the Flask server:

```bash
python server.py
```
The backend server will run on http://localhost:5001

### Frontend Setup
1. Install Node.js dependencies:

```bash
cd ../frontend
npm install
```

2. Start the React development server:

```bash
npm start
```
The application will be available at http://localhost:3000

## Usage

### User Registration/Login
1. Create a new account or use the default admin account:
   - Username: admin
   - Password: admin123

### Analyzing a Run
1. Upload a GPX file from your running device
2. Set your target pace (minutes per mile)
3. Enter your age and resting heart rate for heart rate zone analysis
4. Click "Analyze Run" to process the data

### Features
- **Segment Analysis**: View detailed breakdowns of fast and slow segments
- **Heart Rate Zones**: See time spent in different training zones
- **Route Mapping**: Visualize your run with color-coded pace segments
- **Mile Splits**: Review your pace for each mile
- **Run Comparison**: Select two runs to compare performance metrics
- **History Tracking**: View and manage your running history

## Data Analysis
The application provides:
- Total distance and time
- Fast/slow segment breakdown
- Average pace and heart rate
- Elevation gain/loss impact
- Training zone distribution
- Pace zone analysis
- Mile-by-mile breakdown

## Security
- Secure password hashing
- Session-based authentication
- Protected API endpoints
- CORS protection

## Database Schema
- Users table: Authentication and user management
- Profile table: User preferences and metrics
- Runs table: Running history and analysis data

## Contributing
1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## Troubleshooting
- Ensure both frontend and backend servers are running
- Check Python virtual environment is activated
- Verify database file permissions
- Confirm GPX file format is valid

## License
This project is licensed under the MIT License - see the LICENSE file for details

## Acknowledgments
- Chart.js for data visualization
- Leaflet.js for mapping functionality
- Flask for the backend framework
- React for the frontend framework

## Contact
For support or questions, please open an issue in the repository.