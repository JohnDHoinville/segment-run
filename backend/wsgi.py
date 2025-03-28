from dotenv import load_dotenv
import os

# Load environment variables from .flaskenv
load_dotenv('.flaskenv')

# Change relative import to absolute import 
from server import app

if __name__ == "__main__":
    # Get port from environment variable (default to 5001 if not set)
    port = int(os.environ.get('PORT', 5001))
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=False
    )