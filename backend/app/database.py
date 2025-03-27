import sqlite3
import json
from datetime import datetime
import os
import threading
from werkzeug.security import generate_password_hash, check_password_hash
import traceback
from json import JSONEncoder
import psycopg2
from psycopg2.extras import DictCursor
from urllib.parse import urlparse

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
                    return 'Infinity'
                elif item == float('-inf') or item == float('-Infinity'):
                    return '-Infinity'
            return item

        if isinstance(obj, dict):
            obj = {k: handle_special_values(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            obj = [handle_special_values(item) for item in obj]
        return super().encode(obj)

def safe_json_dumps(obj):
    return SafeJSONEncoder().encode(obj)

class RunDatabase:
    def __init__(self, db_name='runs.db'):
        self.db_name = db_name
        self.conn = None
        self.cursor = None
        self.conn_thread_id = None
        self.connect()
        self.init_db()

    def connect(self):
        try:
            # Get database URL from environment variable
            database_url = os.getenv('DATABASE_URL')
            if database_url:
                # Parse the URL and create connection string
                url = urlparse(database_url)
                self.conn = psycopg2.connect(
                    dbname=url.path[1:],
                    user=url.username,
                    password=url.password,
                    host=url.hostname,
                    port=url.port
                )
                self.cursor = self.conn.cursor(cursor_factory=DictCursor)
            else:
                # Fallback to SQLite for local development
                self.conn = sqlite3.connect(self.db_name, check_same_thread=False)
                self.conn.row_factory = sqlite3.Row
                self.cursor = self.conn.cursor()
                
            # Store the current thread ID
            self.conn_thread_id = threading.get_ident()
        except Exception as e:
            print(f"Error connecting to database: {e}")
            raise
            
    def check_connection(self):
        """Reconnect if we're in a different thread from the one that created the connection"""
        current_thread_id = threading.get_ident()
        if self.conn_thread_id != current_thread_id:
            print(f"Thread ID mismatch. Connection thread: {self.conn_thread_id}, Current thread: {current_thread_id}")
            try:
                # Close existing connection
                if self.cursor:
                    self.cursor.close()
                if self.conn:
                    self.conn.close()
                    
                # Create a new connection
                self.connect()
                print(f"Successfully reconnected in thread {current_thread_id}")
            except Exception as e:
                print(f"Error reconnecting to database: {e}")
                raise

    def init_db(self):
        try:
            if isinstance(self.conn, psycopg2.extensions.connection):
                # PostgreSQL initialization
                self.cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id SERIAL PRIMARY KEY,
                        username VARCHAR(255) UNIQUE NOT NULL,
                        password_hash VARCHAR(255) NOT NULL
                    )
                """)
                self.cursor.execute("""
                    CREATE TABLE IF NOT EXISTS runs (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER REFERENCES users(id),
                        date DATE NOT NULL,
                        data JSONB,
                        total_distance FLOAT,
                        avg_pace FLOAT,
                        avg_hr FLOAT,
                        pace_limit FLOAT
                    )
                """)
                self.cursor.execute("""
                    CREATE TABLE IF NOT EXISTS profiles (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER REFERENCES users(id),
                        age INTEGER,
                        resting_hr INTEGER,
                        weight FLOAT,
                        gender INTEGER
                    )
                """)
            else:
                # SQLite initialization
                self.cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        password_hash TEXT NOT NULL
                    )
                """)
                self.cursor.execute("""
                    CREATE TABLE IF NOT EXISTS runs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        date TEXT NOT NULL,
                        data TEXT,
                        total_distance REAL,
                        avg_pace REAL,
                        avg_hr REAL,
                        pace_limit REAL,
                        FOREIGN KEY (user_id) REFERENCES users (id)
                    )
                """)
                self.cursor.execute("""
                    CREATE TABLE IF NOT EXISTS profiles (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        age INTEGER,
                        resting_hr INTEGER,
                        weight REAL,
                        gender INTEGER,
                        FOREIGN KEY (user_id) REFERENCES users (id)
                    )
                """)
            self.conn.commit()
        except Exception as e:
            print(f"Error initializing database: {e}")
            self.conn.rollback()
            raise

    def ensure_tables(self):
        try:
            if isinstance(self.conn, psycopg2.extensions.connection):
                # PostgreSQL table check
                self.cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = 'users'
                    )
                """)
                if not self.cursor.fetchone()[0]:
                    self.init_db()
            else:
                # SQLite table check
                self.cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='users'
                """)
                if not self.cursor.fetchone():
                    self.init_db()
        except Exception as e:
            print(f"Error ensuring tables: {e}")
            self.conn.rollback()
            raise

    def save_run(self, user_id, run_data):
        try:
            # Check if we need to reconnect
            self.check_connection()
            
            if isinstance(self.conn, psycopg2.extensions.connection):
                # PostgreSQL save
                self.cursor.execute("""
                    INSERT INTO runs (user_id, date, data, total_distance, avg_pace, avg_hr, pace_limit)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    user_id,
                    run_data['date'],
                    json.dumps(run_data['data']),
                    run_data['total_distance'],
                    run_data['avg_pace'],
                    run_data.get('avg_hr'),
                    run_data.get('pace_limit')
                ))
            else:
                # SQLite save
                self.cursor.execute("""
                    INSERT INTO runs (user_id, date, data, total_distance, avg_pace, avg_hr, pace_limit)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    user_id,
                    run_data['date'],
                    json.dumps(run_data['data']),
                    run_data['total_distance'],
                    run_data['avg_pace'],
                    run_data.get('avg_hr'),
                    run_data.get('pace_limit')
                ))
            self.conn.commit()
            return self.cursor.lastrowid
        except Exception as e:
            print(f"Error saving run: {e}")
            traceback.print_exc()
            try:
                self.conn.rollback()
            except:
                pass  # Ignore rollback errors
            return None

    def get_all_runs(self, user_id):
        try:
            # Check if we need to reconnect
            self.check_connection()
            
            if isinstance(self.conn, psycopg2.extensions.connection):
                # PostgreSQL query
                self.cursor.execute("""
                    SELECT * FROM runs 
                    WHERE user_id = %s 
                    ORDER BY date DESC
                """, (user_id,))
            else:
                # SQLite query
                self.cursor.execute("""
                    SELECT * FROM runs 
                    WHERE user_id = ? 
                    ORDER BY date DESC
                """, (user_id,))
            runs = self.cursor.fetchall()
            return [dict(run) for run in runs]
        except Exception as e:
            print(f"Error getting all runs: {e}")
            traceback.print_exc()
            try:
                self.conn.rollback()
            except:
                pass  # Ignore rollback errors
            return []

    def get_run_by_id(self, run_id, user_id=None):
        try:
            if isinstance(self.conn, psycopg2.extensions.connection):
                # PostgreSQL query
                if user_id:
                    self.cursor.execute("""
                        SELECT * FROM runs 
                        WHERE id = %s AND user_id = %s
                    """, (run_id, user_id))
                else:
                    self.cursor.execute("""
                        SELECT * FROM runs 
                        WHERE id = %s
                    """, (run_id,))
            else:
                # SQLite query
                if user_id:
                    self.cursor.execute("""
                        SELECT * FROM runs 
                        WHERE id = ? AND user_id = ?
                    """, (run_id, user_id))
                else:
                    self.cursor.execute("""
                        SELECT * FROM runs 
                        WHERE id = ?
                    """, (run_id,))
            run = self.cursor.fetchone()
            return dict(run) if run else None
        except Exception as e:
            print(f"Error getting run by id: {e}")
            self.conn.rollback()
            raise

    def get_recent_runs(self, user_id, limit=5):
        try:
            if isinstance(self.conn, psycopg2.extensions.connection):
                # PostgreSQL query
                self.cursor.execute("""
                    SELECT * FROM runs 
                    WHERE user_id = %s 
                    ORDER BY date DESC 
                    LIMIT %s
                """, (user_id, limit))
            else:
                # SQLite query
                self.cursor.execute("""
                    SELECT * FROM runs 
                    WHERE user_id = ? 
                    ORDER BY date DESC 
                    LIMIT ?
                """, (user_id, limit))
            runs = self.cursor.fetchall()
            return [dict(run) for run in runs]
        except Exception as e:
            print(f"Error getting recent runs: {e}")
            self.conn.rollback()
            raise

    def delete_run(self, run_id):
        try:
            if isinstance(self.conn, psycopg2.extensions.connection):
                # PostgreSQL delete
                self.cursor.execute("""
                    DELETE FROM runs 
                    WHERE id = %s
                """, (run_id,))
            else:
                # SQLite delete
                self.cursor.execute("""
                    DELETE FROM runs 
                    WHERE id = ?
                """, (run_id,))
            self.conn.commit()
        except Exception as e:
            print(f"Error deleting run: {e}")
            self.conn.rollback()
            raise

    def save_profile(self, user_id, age, resting_hr, weight=70, gender=1):
        try:
            # Check if we need to reconnect
            self.check_connection()
            
            # Ensure all values are properly typed
            user_id = int(user_id) if user_id else None
            age = int(age) if age else 30
            resting_hr = int(resting_hr) if resting_hr else 60
            weight = float(weight) if weight else 70.0
            gender = int(gender) if gender is not None else 0
            
            print(f"Saving profile: user_id={user_id}, age={age}, resting_hr={resting_hr}, weight={weight}, gender={gender}")
            
            if isinstance(self.conn, psycopg2.extensions.connection):
                # PostgreSQL save/update
                self.cursor.execute("""
                    INSERT INTO profiles (user_id, age, resting_hr, weight, gender)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (user_id) 
                    DO UPDATE SET age = %s, resting_hr = %s, weight = %s, gender = %s
                """, (user_id, age, resting_hr, weight, gender,
                      age, resting_hr, weight, gender))
            else:
                # SQLite save/update
                self.cursor.execute("""
                    INSERT OR REPLACE INTO profiles (user_id, age, resting_hr, weight, gender)
                    VALUES (?, ?, ?, ?, ?)
                """, (user_id, age, resting_hr, weight, gender))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error saving profile: {e}")
            traceback.print_exc()
            try:
                self.conn.rollback()
            except:
                pass  # Ignore rollback errors
            return False

    def get_profile(self, user_id):
        try:
            # Check if we need to reconnect
            self.check_connection()
            
            if isinstance(self.conn, psycopg2.extensions.connection):
                # PostgreSQL query
                self.cursor.execute("""
                    SELECT * FROM profiles 
                    WHERE user_id = %s
                """, (user_id,))
            else:
                # SQLite query
                self.cursor.execute("""
                    SELECT * FROM profiles 
                    WHERE user_id = ?
                """, (user_id,))
            
            profile = self.cursor.fetchone()
            
            if profile:
                return dict(profile)
            
            # If no profile exists, create a default one
            print(f"No profile found for user {user_id}, creating default")
            default_profile = {
                'user_id': user_id,
                'age': 30,
                'resting_hr': 60,
                'weight': 70,
                'gender': 0
            }
            
            # Save the default profile
            self.save_profile(
                user_id=user_id,
                age=default_profile['age'],
                resting_hr=default_profile['resting_hr'],
                weight=default_profile['weight'],
                gender=default_profile['gender']
            )
            
            return default_profile
        except Exception as e:
            print(f"Error getting profile: {e}")
            traceback.print_exc()
            try:
                self.conn.rollback()
            except:
                pass  # Ignore rollback errors
            
            # Return a default profile even on error
            return {
                'user_id': user_id,
                'age': 30,
                'resting_hr': 60, 
                'weight': 70,
                'gender': 0
            }

    def create_user(self, username, password):
        try:
            password_hash = generate_password_hash(password)
            if isinstance(self.conn, psycopg2.extensions.connection):
                # PostgreSQL insert
                self.cursor.execute("""
                    INSERT INTO users (username, password_hash)
                    VALUES (%s, %s)
                    RETURNING id
                """, (username, password_hash))
            else:
                # SQLite insert
                self.cursor.execute("""
                    INSERT INTO users (username, password_hash)
                    VALUES (?, ?)
                """, (username, password_hash))
            self.conn.commit()
            return self.cursor.lastrowid
        except Exception as e:
            print(f"Error creating user: {e}")
            self.conn.rollback()
            raise

    def verify_user(self, username, password):
        try:
            # Check if we need to reconnect
            self.check_connection()
            
            if isinstance(self.conn, psycopg2.extensions.connection):
                # PostgreSQL query
                self.cursor.execute("""
                    SELECT id, password_hash FROM users WHERE username = %s
                """, (username,))
            else:
                # SQLite query
                self.cursor.execute("""
                    SELECT id, password_hash FROM users WHERE username = ?
                """, (username,))
                
            user = self.cursor.fetchone()
            if user and check_password_hash(user['password_hash'], password):
                return user['id']
            return None
        except Exception as e:
            print(f"Error verifying user: {e}")
            traceback.print_exc()
            try:
                self.conn.rollback()
            except:
                pass  # Ignore rollback errors
            return None

    def update_password(self, user_id, current_password, new_password):
        try:
            if isinstance(self.conn, psycopg2.extensions.connection):
                # PostgreSQL query
                self.cursor.execute("""
                    SELECT password_hash FROM users 
                    WHERE id = %s
                """, (user_id,))
            else:
                # SQLite query
                self.cursor.execute("""
                    SELECT password_hash FROM users 
                    WHERE id = ?
                """, (user_id,))
            user = self.cursor.fetchone()
            if user and check_password_hash(user['password_hash'], current_password):
                new_hash = generate_password_hash(new_password)
                if isinstance(self.conn, psycopg2.extensions.connection):
                    # PostgreSQL update
                    self.cursor.execute("""
                        UPDATE users 
                        SET password_hash = %s 
                        WHERE id = %s
                    """, (new_hash, user_id))
                else:
                    # SQLite update
                    self.cursor.execute("""
                        UPDATE users 
                        SET password_hash = ? 
                        WHERE id = ?
                    """, (new_hash, user_id))
                self.conn.commit()
                return True
            return False
        except Exception as e:
            print(f"Error updating password: {e}")
            self.conn.rollback()
            raise

    def add_run(self, user_id, date, data, total_distance, avg_pace, avg_hr, pace_limit=None):
        try:
            if isinstance(self.conn, psycopg2.extensions.connection):
                # PostgreSQL insert
                self.cursor.execute("""
                    INSERT INTO runs (user_id, date, data, total_distance, avg_pace, avg_hr, pace_limit)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (user_id, date, json.dumps(data), total_distance, avg_pace, avg_hr, pace_limit))
            else:
                # SQLite insert
                self.cursor.execute("""
                    INSERT INTO runs (user_id, date, data, total_distance, avg_pace, avg_hr, pace_limit)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (user_id, date, json.dumps(data), total_distance, avg_pace, avg_hr, pace_limit))
            self.conn.commit()
            return self.cursor.lastrowid
        except Exception as e:
            print(f"Error adding run: {e}")
            self.conn.rollback()
            raise

    def get_run(self, run_id, user_id):
        try:
            if isinstance(self.conn, psycopg2.extensions.connection):
                # PostgreSQL query
                self.cursor.execute("""
                    SELECT * FROM runs 
                    WHERE id = %s AND user_id = %s
                """, (run_id, user_id))
            else:
                # SQLite query
                self.cursor.execute("""
                    SELECT * FROM runs 
                    WHERE id = ? AND user_id = ?
                """, (run_id, user_id))
            run = self.cursor.fetchone()
            return dict(run) if run else None
        except Exception as e:
            print(f"Error getting run: {e}")
            self.conn.rollback()
            raise

    def get_user_by_id(self, user_id):
        try:
            # Check if we need to reconnect
            self.check_connection()
            
            if isinstance(self.conn, psycopg2.extensions.connection):
                # PostgreSQL query
                self.cursor.execute("""
                    SELECT id, username, password_hash FROM users WHERE id = %s
                """, (user_id,))
            else:
                # SQLite query
                self.cursor.execute("""
                    SELECT id, username, password_hash FROM users WHERE id = ?
                """, (user_id,))
                
            user = self.cursor.fetchone()
            if user:
                return dict(user)
            return None
        except Exception as e:
            print(f"Error getting user by ID: {e}")
            traceback.print_exc()
            try:
                self.conn.rollback()
            except:
                pass  # Ignore rollback errors
            return None
            
    def get_user_by_username(self, username):
        try:
            # Check if we need to reconnect
            self.check_connection()
            
            if isinstance(self.conn, psycopg2.extensions.connection):
                # PostgreSQL query
                self.cursor.execute("""
                    SELECT id, username, password_hash FROM users WHERE username = %s
                """, (username,))
            else:
                # SQLite query
                self.cursor.execute("""
                    SELECT id, username, password_hash FROM users WHERE username = ?
                """, (username,))
                
            user = self.cursor.fetchone()
            if user:
                return dict(user)
            return None
        except Exception as e:
            print(f"Error getting user by username: {e}")
            traceback.print_exc()
            try:
                self.conn.rollback()
            except:
                pass  # Ignore rollback errors
            return None

    def register_user(self, username, password, email):
        try:
            # Check if we need to reconnect
            self.check_connection()
            
            # Hash the password
            password_hash = generate_password_hash(password)
            
            if isinstance(self.conn, psycopg2.extensions.connection):
                # PostgreSQL insert
                self.cursor.execute("""
                    INSERT INTO users (username, password_hash, email)
                    VALUES (%s, %s, %s)
                    RETURNING id
                """, (username, password_hash, email))
                user_id = self.cursor.fetchone()[0]
            else:
                # SQLite insert
                self.cursor.execute("""
                    INSERT INTO users (username, password_hash, email)
                    VALUES (?, ?, ?)
                """, (username, password_hash, email))
                user_id = self.cursor.lastrowid
                
            self.conn.commit()
            return user_id
        except Exception as e:
            print(f"Error registering user: {e}")
            traceback.print_exc()
            try:
                self.conn.rollback()
            except:
                pass  # Ignore rollback errors
            return None 