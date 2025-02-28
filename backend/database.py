import sqlite3
import json
from datetime import datetime
import os
from werkzeug.security import generate_password_hash, check_password_hash
import traceback

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
                password_hash = generate_password_hash('admin123')
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
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                
                # Extract values from run_data
                data_obj = run_data.get('data', {})
                total_distance = data_obj.get('total_distance')
                avg_pace = data_obj.get('avg_pace')
                avg_hr = data_obj.get('avg_hr_all')
                
                # Convert data to string if it's not already
                data_str = json.dumps(data_obj) if isinstance(data_obj, dict) else data_obj
                
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
                print(f"Successfully saved run for user {user_id}")
                return cursor.lastrowid
        except Exception as e:
            print(f"Error saving run: {str(e)}")
            print(f"Run data: {run_data}")
            traceback.print_exc()
            raise e

    def get_all_runs(self, user_id):
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM runs WHERE user_id = ? ORDER BY date DESC', (user_id,))
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

    def save_profile(self, user_id, age, resting_hr):
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE profile 
                SET age = ?, resting_hr = ?, updated_at = CURRENT_TIMESTAMP 
                WHERE user_id = ?
            ''', (age, resting_hr, user_id))
            conn.commit()

    def get_profile(self, user_id):
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT age, resting_hr FROM profile WHERE user_id = ?', (user_id,))
            result = cursor.fetchone()
            return {
                'age': result[0] if result else 0,
                'resting_hr': result[1] if result else 0
            }

    def create_user(self, username, password):
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            password_hash = generate_password_hash(password)
            cursor.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)',
                          (username, password_hash))
            user_id = cursor.lastrowid
            # Create initial profile for user
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