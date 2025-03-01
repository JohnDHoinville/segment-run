from dotenv import load_dotenv
import os

# Load environment variables from .flaskenv
load_dotenv('.flaskenv')

from backend.server import app

if __name__ == '__main__':
    port = 5000  # Match React configuration
    app.run(
        host='localhost',
        port=port,
        debug=True
    )