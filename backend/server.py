from flask import Flask, request, jsonify
from flask_cors import CORS
import tempfile
import os
from running import analyze_run_file
import traceback

app = Flask(__name__)
# Update CORS settings
CORS(app, resources={
    r"/*": {
        "origins": ["http://localhost:3000"],
        "methods": ["POST", "GET", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})

@app.route('/test', methods=['GET'])
def test():
    return jsonify({'status': 'Backend server is running'}), 200

@app.route('/', methods=['GET'])
def home():
    return jsonify({'message': 'Server is running'}), 200

@app.route('/analyze', methods=['POST', 'OPTIONS'])
def analyze():
    # Handle preflight request
    if request.method == 'OPTIONS':
        return '', 204
        
    try:
        print("Received request") # Debug log
        
        if 'file' not in request.files:
            print("No file in request") # Debug log
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        print(f"File received: {file.filename}") # Debug log
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
            
        if not file.filename.endswith('.gpx'):
            return jsonify({'error': 'Invalid file type. Please upload a GPX file'}), 400
        
        if 'paceLimit' not in request.form:
            return jsonify({'error': 'No pace limit provided'}), 400
            
        try:
            pace_limit = float(request.form['paceLimit'])
            print(f"Pace limit: {pace_limit}") # Debug log
            if pace_limit <= 0:
                return jsonify({'error': 'Pace limit must be greater than 0'}), 400
        except ValueError:
            return jsonify({'error': 'Invalid pace limit value'}), 400
        
        # Process the file
        temp_dir = tempfile.mkdtemp()
        temp_path = os.path.join(temp_dir, file.filename)
        file.save(temp_path)
        print(f"File saved to: {temp_path}") # Debug log
        
        try:
            # Run analysis
            total_distance, total_distance_all, fast_segments, avg_hr_all, avg_hr_fast = analyze_run_file(temp_path, pace_limit)
            
            # Format results
            results = {
                'total_distance': float(total_distance_all),
                'fast_distance': float(total_distance),
                'percentage_fast': float((total_distance/total_distance_all)*100) if total_distance_all > 0 else 0,
                'avg_hr_all': float(avg_hr_all) if avg_hr_all else 0,
                'avg_hr_fast': float(avg_hr_fast) if avg_hr_fast else 0,
                'fast_segments': [
                    {
                        'distance': float(dist),
                        'pace': float(pace),
                        'avg_hr': float(hr) if hr else 0
                    }
                    for dist, pace, hr in fast_segments
                ]
            }
            
            print("Sending response:", results)  # Debug print
            return jsonify(results)
            
        except Exception as e:
            print(f"Analysis error: {str(e)}") # Debug log
            return jsonify({'error': f'Error analyzing file: {str(e)}'}), 500
            
        finally:
            try:
                os.remove(temp_path)
                os.rmdir(temp_dir)
            except:
                pass
                
    except Exception as e:
        print(f"Server error: {str(e)}") # Debug log
        traceback.print_exc()
        return jsonify({'error': f'Server error: {str(e)}'}), 500

if __name__ == '__main__':
    print("Starting server on http://localhost:5001")
    app.run(debug=True, host='0.0.0.0', port=5001) 