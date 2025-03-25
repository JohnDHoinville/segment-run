from dotenv import load_dotenv
import os

# Load environment variables from .flaskenv
load_dotenv('.flaskenv')

# Change relative import to absolute import 
from server import app

if __name__ == '__main__':
    port = 5001  # Match React configuration
    app.run(
        host='localhost',
        port=port,
        debug=True
    )