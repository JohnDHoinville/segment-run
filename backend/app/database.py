import sqlite3
import json
from datetime import datetime
import os
from werkzeug.security import generate_password_hash, check_password_hash
import traceback
from json import JSONEncoder

# Add a proper JSON encoder for Infinity values
class SafeJSONEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        return super().default(obj)
        
    def encode(self, obj):
        # Pre-process the object to handle special values
        def handle_special_values(item):
            if isinstance(item, float):
                if item == float('inf') or item == float('Infinity'):
                    return "Infinity"
                if item == float('-inf') or item == float('-Infinity'):
                    return "-Infinity"
                if item != item:  # Check for NaN
                    return "NaN"
            elif isinstance(item, dict):
                return {k: handle_special_values(v) for k, v in item.items()}
            elif isinstance(item, list):
                return [handle_special_values(i) for i in item]
            return item
            
        # Process the entire object tree
        processed_obj = handle_special_values(obj)
        return super().encode(processed_obj)

# Use this instead of the regular JSON encoder
def safe_json_dumps(obj):
    return json.dumps(obj, cls=SafeJSONEncoder)

class RunDatabase:
    def __init__(self, db_name='runs.db'):
        self.db_name = db_name
        # Only create database if it doesn't exist
        if not os.path.exists(self.db_name):
            print(f"Creating new database: {self.db_name}")
            self.init_db()
        else:
            print(f"Using existing database: {self.db_name}")
            # Ensure all tables exist (in case of schema updates)
            self.ensure_tables()

    def init_db(self):
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            # Add users table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            # Create profile table with user_id
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS profile (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    age INTEGER DEFAULT 0,
                    resting_hr INTEGER DEFAULT 0,
                    weight REAL DEFAULT 70,
                    gender INTEGER DEFAULT 1,  /* 1 for male, 0 for female */
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            ''')
            # Create runs table with all required columns
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    date TEXT NOT NULL,
                    total_distance REAL,
                    avg_pace REAL,
                    avg_hr REAL,
                    data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            ''')
            conn.commit()

            # Create default admin user
            cursor.execute('SELECT id FROM users WHERE username = ?', ('admin',))
            if not cursor.fetchone():
                password_hash = generate_password_hash('admin123')
                cursor.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)',
                             ('admin', password_hash))
                user_id = cursor.lastrowid
                cursor.execute('INSERT INTO profile (user_id, age, resting_hr) VALUES (?, 0, 0)',
                             (user_id,))
                conn.commit()
                print("Created default admin user (username: admin, password: admin123)")

    def ensure_tables(self):
        """Ensure all required tables exist without recreating the database"""
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            
            # Check if pace_limit column exists
            try:
                cursor.execute('SELECT pace_limit FROM runs LIMIT 1')
            except sqlite3.OperationalError:
                print("Adding pace_limit column to runs table")
                cursor.execute('ALTER TABLE runs ADD COLUMN pace_limit REAL')
                conn.commit()
            
            # First, check if we need to add new columns
            try:
                cursor.execute('SELECT weight, gender FROM profile LIMIT 1')
            except sqlite3.OperationalError:
                print("Adding weight and gender columns to profile table")
                cursor.execute('ALTER TABLE profile ADD COLUMN weight REAL DEFAULT 70')
                cursor.execute('ALTER TABLE profile ADD COLUMN gender INTEGER DEFAULT 1')
                conn.commit()
            
            # Create tables if they don't exist
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS profile (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    age INTEGER DEFAULT 0,
                    resting_hr INTEGER DEFAULT 0,
                    weight REAL DEFAULT 70,
                    gender INTEGER DEFAULT 1,  /* 1 for male, 0 for female */
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    date TEXT NOT NULL,
                    total_distance REAL,
                    avg_pace REAL,
                    avg_hr REAL,
                    data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            ''')
            conn.commit()

            # Check for default admin user
            cursor.execute('SELECT id FROM users WHERE username = ?', ('admin',))
            if not cursor.fetchone():
                password_hash = generate_password_hash('admin123', method='sha256')
                cursor.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)',
                             ('admin', password_hash))
                user_id = cursor.lastrowid
                cursor.execute('INSERT INTO profile (user_id, age, resting_hr) VALUES (?, 0, 0)',
                             (user_id,))
                conn.commit()
                print("Created default admin user (username: admin, password: admin123)")

    def save_run(self, user_id, run_data):
        try:
            print("Saving run data for user:", user_id)
            print("Run data to save:", run_data)
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                
                # Extract values from run_data
                data_obj = run_data.get('data', {})
                if isinstance(data_obj, str):
                    data_obj = json.loads(data_obj)
                
                print("Parsed data object:", data_obj)
                
                # Calculate total time for average pace
                total_time = 0
                for segment in data_obj.get('fast_segments', []) + data_obj.get('slow_segments', []):
                    if isinstance(segment, dict) and 'time_diff' in segment:
                        total_time += segment['time_diff']
                
                # Calculate average pace
                total_distance = data_obj.get('total_distance', 0)
                avg_pace = total_time / total_distance if total_distance > 0 else 0
                avg_hr = data_obj.get('avg_hr_all', 0)
                
                # Convert data to string if it's not already
                data_str = json.dumps(data_obj, cls=SafeJSONEncoder) if isinstance(data_obj, dict) else data_obj
                
                print("Values to insert:", {
                    'user_id': user_id,
                    'date': run_data['date'],
                    'total_distance': total_distance,
                    'avg_pace': avg_pace,
                    'avg_hr': avg_hr
                })
                
                cursor.execute('''
                    INSERT INTO runs (
                        user_id, 
                        date, 
                        total_distance, 
                        avg_pace, 
                        avg_hr, 
                        data
                    ) VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    user_id,
                    run_data['date'],
                    total_distance,
                    avg_pace,
                    avg_hr,
                    data_str
                ))
                conn.commit()
                run_id = cursor.lastrowid
                print(f"Successfully saved run {run_id} for user {user_id}")
                return run_id
        except Exception as e:
            print(f"Error saving run: {str(e)}")
            print(f"Run data: {run_data}")
            traceback.print_exc()
            raise e

    def get_all_runs(self, user_id):
        print(f"Getting runs for user {user_id} from database")
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM runs 
                WHERE user_id = ? 
                ORDER BY date DESC, created_at DESC
            ''', (user_id,))
            
            # Get column names
            columns = [description[0] for description in cursor.description]
            runs = cursor.fetchall()
            
            # Map results to dictionary using column names
            formatted_runs = []
            for run in runs:
                run_dict = {}
                for i, column in enumerate(columns):
                    value = run[i]
                    # Handle JSON data field
                    if column == 'data' and value:
                        try:
                            if isinstance(value, str):
                                value = json.loads(value)
                        except json.JSONDecodeError:
                            print(f"Error decoding JSON for run {run[0]}")
                            value = {}
                    # Ensure numeric fields have default values
                    elif column in ['total_distance', 'avg_pace', 'avg_hr', 'pace_limit']:
                        value = float(value) if value is not None else 0.0
                    run_dict[column] = value
                formatted_runs.append(run_dict)
            
            return formatted_runs

    def get_run_by_id(self, run_id, user_id=None):
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            if user_id:
                cursor.execute('SELECT * FROM runs WHERE id = ? AND user_id = ?', (run_id, user_id))
            else:
                cursor.execute('SELECT * FROM runs WHERE id = ?', (run_id,))
            # Get column names
            columns = [description[0] for description in cursor.description]
            run = cursor.fetchone()
            
            if run:
                # Map result to dictionary using column names
                run_dict = {}
                for i, column in enumerate(columns):
                    run_dict[column] = run[i]
                return run_dict
            return None

    def get_recent_runs(self, user_id, limit=5):
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM runs WHERE user_id = ? ORDER BY date DESC LIMIT ?', 
                          (user_id, limit))
            # Get column names
            columns = [description[0] for description in cursor.description]
            runs = cursor.fetchall()
            
            # Map results to dictionary using column names
            formatted_runs = []
            for run in runs:
                run_dict = {}
                for i, column in enumerate(columns):
                    run_dict[column] = run[i]
                formatted_runs.append(run_dict)
            
            return formatted_runs

    def delete_run(self, run_id):
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM runs WHERE id = ?', (run_id,))
                if cursor.rowcount == 0:
                    raise Exception(f"No run found with ID {run_id}")
                conn.commit()
                print(f"Deleted run {run_id} from database")
                return True
        except Exception as e:
            print(f"Database error deleting run {run_id}: {str(e)}")
            raise e

    def save_profile(self, user_id, age, resting_hr, weight=70, gender=1):
        print(f"\nSaving profile for user {user_id}:")
        # Convert from lbs to kg before storing (if desired):
        weight_in_kg = weight * 0.453592

        print(f"Age: {age}, Resting HR: {resting_hr}, Weight: {weight} lbs => {weight_in_kg:.1f} kg, Gender: {gender}")

        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE profile 
                SET age = ?, resting_hr = ?, weight = ?, gender = ?, updated_at = CURRENT_TIMESTAMP 
                WHERE user_id = ?
            ''', (age, resting_hr, weight_in_kg, gender, user_id))
            conn.commit()
            print("Profile saved successfully")

    def get_profile(self, user_id):
        print(f"\nGetting profile for user {user_id}")
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT age, resting_hr, weight, gender FROM profile WHERE user_id = ?', (user_id,))
            result = cursor.fetchone()
            # Convert weight from kg back to lbs
            weight_in_kg = result[2] if result else 70
            weight_in_lbs = weight_in_kg * 2.20462
            profile = {
                'age': result[0] if result else 0,
                'resting_hr': result[1] if result else 0,
                'weight': round(weight_in_lbs, 1),  # Round to 1 decimal place
                'gender': result[3] if result else 1
            }
            print("Retrieved profile:", profile)
            return profile

    def create_user(self, username, password):
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            password_hash = generate_password_hash(password, method='sha256')
            cursor.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)',
                          (username, password_hash))
            user_id = cursor.lastrowid
            cursor.execute('INSERT INTO profile (user_id, age, resting_hr) VALUES (?, 0, 0)',
                          (user_id,))
            conn.commit()
            return user_id

    def verify_user(self, username, password):
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id, password_hash FROM users WHERE username = ?', (username,))
            result = cursor.fetchone()
            if result and check_password_hash(result[1], password):
                return result[0]  # Return user_id
            return None 

    def update_password(self, user_id, current_password, new_password):
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            # Verify current password
            cursor.execute('SELECT password_hash FROM users WHERE id = ?', (user_id,))
            result = cursor.fetchone()
            if not result or not check_password_hash(result[0], current_password):
                return False
            
            # Update to new password
            new_password_hash = generate_password_hash(new_password)
            cursor.execute('UPDATE users SET password_hash = ? WHERE id = ?',
                          (new_password_hash, user_id))
            conn.commit()
            return True 

    def add_run(self, user_id, date, data, total_distance, avg_pace, avg_hr, pace_limit=None):
        """Add a new run to the database"""
        try:
            # Debug what data is being passed to add_run
            print("\n=== DATABASE: ADDING RUN ===")
            try:
                data_obj = json.loads(data) if isinstance(data, str) else data
                print(f"Database receiving advanced metrics:")
                print(f"VO2max: {data_obj.get('vo2max')}")
                print(f"Training Load: {data_obj.get('training_load')}")
                print(f"Recovery Time: {data_obj.get('recovery_time')}")
            except Exception as e:
                print(f"Error parsing data for debug: {str(e)}")
            
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO runs 
                    (user_id, date, data, total_distance, avg_pace, avg_hr, pace_limit)
                    VALUES 
                    (?, ?, ?, ?, ?, ?, ?)
                ''', (user_id, date, data, total_distance, avg_pace, avg_hr, pace_limit))
                conn.commit()
                run_id = cursor.lastrowid
                print(f"Database: Successfully saved run {run_id} with metrics")
                return run_id
        except Exception as e:
            print(f"Error adding run: {e}")
            return None 

    def get_run(self, run_id, user_id):
        """Get a specific run by ID and verify it belongs to the user"""
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id, user_id, date, data, total_distance, avg_pace, avg_hr, pace_limit FROM runs WHERE id = ? AND user_id = ?",
                    (run_id, user_id)
                )
                run = cursor.fetchone()
                
                if not run:
                    return None
                
                # Convert to dictionary with column names
                run_dict = {
                    'id': run[0],
                    'user_id': run[1],
                    'date': run[2],
                    'data': run[3],
                    'total_distance': run[4],
                    'avg_pace': run[5],
                    'avg_hr': run[6],
                    'pace_limit': run[7]
                }
                
                # Try to parse the JSON data
                if run_dict['data'] and isinstance(run_dict['data'], str):
                    try:
                        run_dict['data'] = json.loads(run_dict['data'])
                        # Debug the retrieved data
                        print("\n=== DATABASE: RETRIEVING RUN ===")
                        print(f"Retrieved run {run_id} with advanced metrics:")
                        print(f"VO2max: {run_dict['data'].get('vo2max')}")
                        print(f"Training Load: {run_dict['data'].get('training_load')}")
                        print(f"Recovery Time: {run_dict['data'].get('recovery_time')}")
                    except json.JSONDecodeError:
                        # Keep as string if can't be parsed
                        print(f"Error: Could not parse JSON data for run {run_id}")
                        pass
                
                return run_dict
            
        except Exception as e:
            print(f"Error getting run: {e}")
            traceback.print_exc()
            return None 