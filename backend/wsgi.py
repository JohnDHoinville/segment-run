from dotenv import load_dotenv
import os

# Load environment variables from .flaskenv
load_dotenv('.flaskenv')

from server import app

if __name__ == '__main__':
    port = int(os.environ.get('FLASK_RUN_PORT', 5001))
    app.run(
        host='localhost',
        port=port,
        debug=True
    )