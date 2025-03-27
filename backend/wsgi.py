from dotenv import load_dotenv
import os
from ultra_minimal import app

# Load environment variables from .flaskenv
load_dotenv('.flaskenv')

# Change relative import to absolute import 

if __name__ == "__main__":
    app.run()