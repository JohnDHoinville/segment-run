# Running Analysis Tool

A web application that analyzes GPX files from running activities to provide detailed pace and heart rate analysis. The tool helps runners identify segments where they exceeded their target pace and provides corresponding heart rate data.

## Features

- GPX file upload and analysis
- Target pace setting
- Detailed analysis results including:
  - Total distance covered
  - Distance run faster than target pace
  - Average heart rate (overall and during fast segments)
  - Detailed breakdown of fast segments

## Tech Stack

### Frontend

- React.js
- CSS for styling
- Fetch API for backend communication

### Backend

- Python
- Flask server
- GPX file parsing
- Data analysis algorithms

## Getting Started

### Prerequisites

- Node.js
- Python 3.x
- pip (Python package manager)

### Installation

1. Clone the repository:
1. 

bash

git clone https://github.com/JohnDHoinville/segment-run.git

cd segment-run

**2. Install frontend dependencies:**

bash

npm install

**3. Install backend dependencies:**

bash

cd backend

pip install -r requirements.txt


### Running the Application


1. Start the backend server:

bash

cd backend

python server.py

2. In a new terminal, start the frontend development server:

bash

npm start


3. Open your browser and navigate to `http://localhost:3000`

## Usage

1. Click "Choose GPX File" to upload your running data
2. Enter your target pace in minutes per mile
3. Click "Analyze Run" to process your data
4. View the analysis results, including:
   - Total distance
   - Fast segments analysis
   - Heart rate data


## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
