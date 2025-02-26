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


# Reset Git


The repository belongs to "JohnDHoinville" but you're trying to push as "JohnAlfaJango". Here's how to fix this:

* First, remove the existing credentials from your system:

  **git** **config** **--global** **--unset** **user.name**

  **git** **config** **--global** **--unset** **user.email**
* Remove the stored credentials (on macOS):

  **git** **credential-osxkeychain** **erase**

  **host**=**github.com**

  **protocol**=**https**

(Press return twice after entering these lines)

* Set up your correct GitHub credentials:

  **git** **config** **--global** **user.name** **"JohnDHoinville"**

  **git** **config** **--global** **user.email** **"your-email@example.com"**
* Now try pushing again:

  **git** **push** **-u** **origin** **master**

Alternatively, you can also:

* Use SSH instead of HTTPS by updating your remote URL:

  **git** **remote** **set-url** **origin** **git@github.com:JohnDHoinville/segment-run.git**
* Or update your GitHub credentials in your system's credential manager/keychain.

Make sure you're using the GitHub account that has access to the repository (JohnDHoinville in this case).
