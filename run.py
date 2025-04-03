# run.py - Script to start the web application

import os
from app import app

if __name__ == "__main__":
    # Create necessary folders if they don't exist
    os.makedirs('uploads', exist_ok=True)
    os.makedirs('results', exist_ok=True)
    os.makedirs('temp_audio', exist_ok=True)
    
    # Run the Flask application in debug mode
    app.run(debug=True, host='0.0.0.0', port=5000)