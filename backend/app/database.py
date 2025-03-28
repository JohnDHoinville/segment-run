import sqlite3
import json
from datetime import datetime
import os
import threading
from werkzeug.security import generate_password_hash, check_password_hash
import traceback
from json import JSONEncoder

try:
    import psycopg2
    from psycopg2.extras import DictCursor
    POSTGRES_AVAILABLE = True
except (ImportError, SystemError) as e:
    print(f"PostgreSQL support disabled: {str(e)}")
    POSTGRES_AVAILABLE = False

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
            
            print(f"Connecting to database. DATABASE_URL exists: {database_url is not None}")
            
            if database_url and POSTGRES_AVAILABLE:
                print(f"Using PostgreSQL connection with DATABASE_URL")
                
                # Parse the URL and create connection string
                try:
                    # Handle Heroku-specific "postgres://" vs "postgresql://" prefix
                    if database_url.startswith('postgres://'):
                        # Heroku uses postgres:// but psycopg2 wants postgresql://
                        database_url = database_url.replace('postgres://', 'postgresql://', 1)
                        print("Converted postgres:// to postgresql:// for psycopg2 compatibility")
                    
                    url = urlparse(database_url)
                    print(f"Database host: {url.hostname}, Database name: {url.path[1:] if url.path else 'None'}")
                    
                    # Connect to PostgreSQL with explicit connection parameters
                    try:
                        self.conn = psycopg2.connect(
                            dbname=url.path[1:] if url.path else 'postgres',
                            user=url.username,
                            password=url.password,
                            host=url.hostname,
                            port=url.port
                        )
                        self.cursor = self.conn.cursor(cursor_factory=DictCursor)
                        print("PostgreSQL connection established successfully")
                    except psycopg2.OperationalError as op_error:
                        print(f"PostgreSQL operational error: {str(op_error)}")
                        # Try direct connection string approach
                        print("Trying connection string approach instead")
                        self.conn = psycopg2.connect(database_url)
                        self.cursor = self.conn.cursor(cursor_factory=DictCursor)
                        print("PostgreSQL connection via connection string successful")
                except Exception as pg_error:
                    print(f"Error establishing PostgreSQL connection: {str(pg_error)}")
                    traceback.print_exc()
                    print("Falling back to SQLite")
                    self.conn = sqlite3.connect(self.db_name, check_same_thread=False)
                    self.conn.row_factory = sqlite3.Row
                    self.cursor = self.conn.cursor()
            else:
                # Fallback to SQLite for local development
                print("No DATABASE_URL found or PostgreSQL not available, using SQLite database")
                self.conn = sqlite3.connect(self.db_name, check_same_thread=False)
                self.conn.row_factory = sqlite3.Row
                self.cursor = self.conn.cursor()
                
            # Test the connection
            try:
                if POSTGRES_AVAILABLE and isinstance(self.conn, psycopg2.extensions.connection):
                    self.cursor.execute("SELECT 1")
                else:
                    self.cursor.execute("SELECT 1")
                print("Database connection test successful")
            except Exception as test_error:
                print(f"Database connection test failed: {str(test_error)}")
                traceback.print_exc()
                # If the connection test fails, try to reconnect or refresh
                if POSTGRES_AVAILABLE and isinstance(self.conn, psycopg2.extensions.connection):
                    try:
                        self.conn.close()
                        # Simplest fallback - connect to SQLite instead
                        self.conn = sqlite3.connect(self.db_name, check_same_thread=False)
                        self.conn.row_factory = sqlite3.Row
                        self.cursor = self.conn.cursor()
                        print("Reconnected using SQLite after PostgreSQL test failure")
                    except Exception as fallback_error:
                        print(f"Failed to reconnect: {str(fallback_error)}")
                        raise
                
            # Store the current thread ID
            self.conn_thread_id = threading.get_ident()
            
            # Print database type confirmation
            if POSTGRES_AVAILABLE and isinstance(self.conn, psycopg2.extensions.connection):
                print("Using PostgreSQL database")
            else:
                print("Using SQLite database")
                
        except Exception as e:
            print(f"Error connecting to database: {e}")
            traceback.print_exc()
            # Set conn and cursor to None to ensure we know they're invalid
            self.conn = None
            self.cursor = None
            raise
            
    def check_connection(self):
        """Reconnect if we're in a different thread from the one that created the connection"""
        current_thread_id = threading.get_ident()
        
        # First check if we need to reconnect due to thread change
        thread_mismatch = self.conn_thread_id != current_thread_id
        
        # Also check if connection is None or potentially invalid
        connection_invalid = self.conn is None or self.cursor is None
        
        if thread_mismatch or connection_invalid:
            print(f"Connection check: Thread mismatch: {thread_mismatch}, Connection invalid: {connection_invalid}")
            print(f"Thread ID mismatch. Connection thread: {self.conn_thread_id}, Current thread: {current_thread_id}")
            try:
                # Close existing connection
                if self.cursor:
                    try:
                        self.cursor.close()
                    except Exception as cursor_error:
                        print(f"Error closing cursor: {str(cursor_error)}")
                        
                if self.conn:
                    try:
                        self.conn.close()
                    except Exception as conn_error:
                        print(f"Error closing connection: {str(conn_error)}")
                        
                # Create a new connection
                self.connect()
                print(f"Successfully reconnected in thread {current_thread_id}")
                return True
            except Exception as e:
                print(f"Error reconnecting to database: {e}")
                traceback.print_exc()
                # Try one more time as a last resort
                try:
                    print("Attempting emergency reconnection...")
                    self.conn = None
                    self.cursor = None
                    self.connect()
                    print("Emergency reconnection successful")
                    return True
                except Exception as emergency_error:
                    print(f"Emergency reconnection failed: {str(emergency_error)}")
                    raise
        
        # Connection is valid
        return False

    def init_db(self):
        try:
            if isinstance(self.conn, psycopg2.extensions.connection) and POSTGRES_AVAILABLE:
                # PostgreSQL initialization
                # First check if the tables already exist
                self.cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = 'users'
                    )
                """)
                users_exists = self.cursor.fetchone()[0]
                
                if not users_exists:
                    print("Creating PostgreSQL users table")
                    self.cursor.execute("""
                        CREATE TABLE IF NOT EXISTS users (
                            id SERIAL PRIMARY KEY,
                            username VARCHAR(255) UNIQUE NOT NULL,
                            password_hash VARCHAR(255) NOT NULL,
                            email VARCHAR(255)
                        )
                    """)
                else:
                    # Check if email column exists
                    self.cursor.execute("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.columns 
                            WHERE table_schema = 'public' 
                            AND table_name = 'users' 
                            AND column_name = 'email'
                        )
                    """)
                    email_exists = self.cursor.fetchone()[0]
                    
                    if not email_exists:
                        print("Adding email column to users table")
                        self.cursor.execute("""
                            ALTER TABLE users ADD COLUMN email VARCHAR(255)
                        """)
                
                # Check if runs table exists
                self.cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = 'runs'
                    )
                """)
                runs_exists = self.cursor.fetchone()[0]
                
                if not runs_exists:
                    print("Creating PostgreSQL runs table")
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
                    
                # Check if profiles table exists
                self.cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = 'profiles'
                    )
                """)
                profiles_exists = self.cursor.fetchone()[0]
                
                if not profiles_exists:
                    print("Creating PostgreSQL profiles table")
                    self.cursor.execute("""
                        CREATE TABLE IF NOT EXISTS profiles (
                            id SERIAL PRIMARY KEY,
                            user_id INTEGER REFERENCES users(id) UNIQUE,
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
                    password_hash TEXT NOT NULL,
                        email TEXT
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
                        user_id INTEGER UNIQUE,
                        age INTEGER,
                        resting_hr INTEGER,
                        weight REAL,
                        gender INTEGER,
                        FOREIGN KEY (user_id) REFERENCES users (id)
                    )
                """)
            self.conn.commit()
            print("Database initialization complete")
        except Exception as e:
            print(f"Error initializing database: {e}")
            traceback.print_exc()
            try:
                self.conn.rollback()
            except:
                pass
            raise

    def ensure_tables(self):
        try:
            if isinstance(self.conn, psycopg2.extensions.connection) and POSTGRES_AVAILABLE:
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
        print(f"\n=== SAVE RUN CALLED ===")
        print(f"User ID: {user_id}")
        print(f"Run data: {run_data.get('date')}, distance: {run_data.get('total_distance')}")
        
        try:
            # Check if we need to reconnect
            connection_status = self.check_connection()
            print(f"Connection check completed. Reconnection performed: {connection_status}")
            
            # Verify we have a valid connection
            if self.conn is None or self.cursor is None:
                print("ERROR: Database connection is not valid after check_connection")
                try:
                    # Emergency reconnection attempt
                    print("Attempting emergency reconnection...")
                    self.connect()
                    print("Emergency reconnection successful")
                except Exception as emergency_error:
                    print(f"Emergency reconnection failed: {str(emergency_error)}")
                    return None
            
            # Extract key fields and apply proper type conversions
            user_id = int(user_id) if user_id else None
            if not user_id:
                print("ERROR: Invalid user_id (None or 0)")
                return None
            
            run_date = str(run_data.get('date', datetime.now().strftime('%Y-%m-%d')))
            
            # For numerical fields, ensure they're proper types
            total_distance = float(run_data.get('total_distance', 0))
            avg_pace = float(run_data.get('avg_pace', 0))
            avg_hr = float(run_data.get('avg_hr', 0) or 0)  # Handle None
            pace_limit = float(run_data.get('pace_limit', 0) or 0)  # Handle None
            
            # Ensure JSON data is properly serialized
            data_json = None
            if 'data' in run_data:
                if isinstance(run_data['data'], str):
                    data_json = run_data['data']  # Already a JSON string
                else:
                    # Convert to JSON string
                    try:
                        # Use safe_json_dumps for better handling of special values
                        data_json = safe_json_dumps(run_data['data'])
                    except Exception as json_err:
                        print(f"Error serializing run data: {str(json_err)}")
                        traceback.print_exc()
                        # Try standard json dumps as fallback
                        try:
                            data_json = json.dumps(run_data['data'])
                        except:
                            # Last resort: simplified data object
                            data_json = json.dumps({
                                "total_distance": total_distance,
                                "avg_pace": avg_pace,
                                "avg_hr": avg_hr
                            })
            else:
                data_json = json.dumps({})  # Empty if no data
            
            print(f"Saving run to database:")
            print(f"  User ID: {user_id}")
            print(f"  Date: {run_date}")
            print(f"  Distance: {total_distance}")
            print(f"  Avg Pace: {avg_pace}")
            print(f"  Avg HR: {avg_hr}")
            print(f"  JSON data size: {len(data_json) if data_json else 0} bytes")
            
            # Check database type
            using_postgres = POSTGRES_AVAILABLE and isinstance(self.conn, psycopg2.extensions.connection)
            print(f"Database type: {'PostgreSQL' if using_postgres else 'SQLite'}")
            
            if using_postgres:
                # PostgreSQL save - use transaction with explicit commit
                original_autocommit = self.conn.autocommit
                self.conn.autocommit = False
                
                try:
                    print("Using PostgreSQL database")
                    
                    # Start transaction
                    self.cursor.execute("BEGIN")
                    
                    # Verify the user exists
                    self.cursor.execute("SELECT id FROM users WHERE id = %s", (user_id,))
                    user_record = self.cursor.fetchone()
                    if not user_record:
                        print(f"ERROR: User ID {user_id} does not exist in the database")
                        self.conn.rollback()
                        return None
                    
                    # Handle oversized JSON by removing detailed segment data if needed
                    if data_json and len(data_json) > 1000000:  # If > 1MB
                        print("WARNING: JSON data is very large, truncating detailed segments")
                        data_obj = json.loads(data_json)
                        # Keep only summary data, remove detailed segments
                        if 'fast_segments' in data_obj:
                            data_obj['fast_segments'] = data_obj['fast_segments'][:5] if data_obj['fast_segments'] else []
                        if 'slow_segments' in data_obj:
                            data_obj['slow_segments'] = data_obj['slow_segments'][:5] if data_obj['slow_segments'] else []
                        data_json = json.dumps(data_obj)
                    
                    # Insert the run data
                    print("Executing INSERT for PostgreSQL")
                    try:
                        self.cursor.execute("""
                            INSERT INTO runs (user_id, date, data, total_distance, avg_pace, avg_hr, pace_limit)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                            RETURNING id
                        """, (user_id, run_date, data_json, total_distance, avg_pace, avg_hr, pace_limit))
                    except psycopg2.Error as pg_query_error:
                        print(f"PostgreSQL query error: {str(pg_query_error)}")
                        traceback.print_exc()
                        # Try again with a smaller data object if the issue might be the size
                        if "value too long" in str(pg_query_error) or "out of range" in str(pg_query_error):
                            print("Trying again with simplified data object")
                            simplified_data = {
                                "total_distance": total_distance,
                                "avg_pace": avg_pace,
                                "avg_hr": avg_hr,
                                "message": "Data was too large to store in full"
                            }
                            self.cursor.execute("""
                                INSERT INTO runs (user_id, date, data, total_distance, avg_pace, avg_hr, pace_limit)
                                VALUES (%s, %s, %s, %s, %s, %s, %s)
                                RETURNING id
                            """, (user_id, run_date, json.dumps(simplified_data), total_distance, avg_pace, avg_hr, pace_limit))
                        else:
                            # Re-raise if it's not a size issue
                            raise
                    
                    # Get the ID
                    result = self.cursor.fetchone()
                    if not result:
                        print("ERROR: PostgreSQL INSERT did not return an ID")
                        self.conn.rollback()
                        return None
                        
                    run_id = result[0]
                    print(f"PostgreSQL run_id from RETURNING: {run_id}")
                    
                    # Commit transaction
                    self.conn.commit()
                    print(f"Transaction committed for run_id: {run_id}")
                    return run_id
                    
                except Exception as pg_error:
                    # Roll back on error
                    print(f"PostgreSQL save error: {str(pg_error)}")
                    traceback.print_exc()
                    try:
                        self.conn.rollback()
                        print("Transaction rolled back")
                    except Exception as rollback_error:
                        print(f"Rollback error: {str(rollback_error)}")
                    
                    # Attempt reconnection as this might be a connection issue
                    try:
                        print("Attempting reconnection after save error...")
                        self.conn = None
                        self.cursor = None
                        self.connect()
                        print("Reconnection successful, but save failed")
                    except Exception as reconnect_err:
                        print(f"Reconnection failed: {str(reconnect_err)}")
                        
                    return None
                finally:
                    # Restore original autocommit setting
                    try:
                        self.conn.autocommit = original_autocommit
                    except:
                        pass  # Ignore if connection was lost
            else:
                # SQLite save - use transaction with explicit commit
                try:
                    print("Using SQLite database")
                    
                    # Start transaction
                    self.cursor.execute("BEGIN TRANSACTION")
                    
                    # Verify the user exists
                    self.cursor.execute("SELECT id FROM users WHERE id = ?", (user_id,))
                    user_record = self.cursor.fetchone()
                    if not user_record:
                        print(f"ERROR: User ID {user_id} does not exist in the database")
                        self.cursor.execute("ROLLBACK")
                        return None
                    
                    # Insert the run data
                    print("Executing INSERT for SQLite")
                    self.cursor.execute("""
                        INSERT INTO runs (user_id, date, data, total_distance, avg_pace, avg_hr, pace_limit)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (user_id, run_date, data_json, total_distance, avg_pace, avg_hr, pace_limit))
                    
                    # Get the ID
                    run_id = self.cursor.lastrowid
                    if not run_id:
                        print("ERROR: SQLite INSERT did not return a lastrowid")
                        self.cursor.execute("ROLLBACK")
                        return None
                        
                    print(f"SQLite run_id from lastrowid: {run_id}")
                    
                    # Commit transaction
                    self.cursor.execute("COMMIT")
                    print(f"Transaction committed for run_id: {run_id}")
                    return run_id
                    
                except Exception as sqlite_error:
                    # Roll back on error
                    print(f"SQLite save error: {str(sqlite_error)}")
                    traceback.print_exc()
                    try:
                        self.cursor.execute("ROLLBACK")
                        print("Transaction rolled back")
                    except Exception as rollback_error:
                        print(f"Rollback error: {str(rollback_error)}")
                    return None
                
        except Exception as e:
            print(f"Unexpected error saving run: {str(e)}")
            traceback.print_exc()
            
            try:
                # Additional roll back if outer transaction exists
                if POSTGRES_AVAILABLE and isinstance(self.conn, psycopg2.extensions.connection):
                    self.conn.rollback()
                    print("Outer transaction rolled back (PostgreSQL)")
                else:
                    self.cursor.execute("ROLLBACK")
                    print("Outer transaction rolled back (SQLite)")
            except Exception as rollback_error:
                print(f"Outer rollback error: {str(rollback_error)}")
            
            return None

    def get_all_runs(self, user_id):
        try:
            # Check if we need to reconnect
            self.check_connection()
            
            print(f"Retrieving runs for user ID: {user_id}")
            
            # Validate and convert user_id
            user_id = int(user_id) if user_id else None
            if not user_id:
                print("Invalid user ID")
                return []
            
            # Use a try-except block to handle query issues
            try:
                if POSTGRES_AVAILABLE and isinstance(self.conn, psycopg2.extensions.connection):
                    # PostgreSQL query
                    self.cursor.execute("""
                        SELECT id, user_id, date, data, total_distance, avg_pace, avg_hr, pace_limit
                        FROM runs 
                        WHERE user_id = %s 
                        ORDER BY date DESC
                    """, (user_id,))
                else:
                    # SQLite query
                    self.cursor.execute("""
                        SELECT id, user_id, date, data, total_distance, avg_pace, avg_hr, pace_limit
                        FROM runs 
                        WHERE user_id = ? 
                        ORDER BY date DESC
                    """, (user_id,))
                
                # Fetch all results
                runs = self.cursor.fetchall()
                
                if not runs:
                    print("No runs found for this user")
                    return []
                
                print(f"Found {len(runs)} runs")
                
                # Convert to list of dictionaries with proper handling
                result = []
                for run in runs:
                    try:
                        # Start with a basic dictionary conversion 
                        run_dict = dict(run)
                        
                        # Handle data field which should be JSON
                        if 'data' in run_dict and run_dict['data']:
                            # If it's a string, try to parse it
                            if isinstance(run_dict['data'], str):
                                try:
                                    run_dict['data'] = json.loads(run_dict['data'])
                                except json.JSONDecodeError:
                                    print(f"Failed to parse JSON data for run ID {run_dict.get('id')}")
                                    run_dict['data'] = {}
                            # If it's already a dict/object (from psycopg2), use as is
                                
                        # Make sure other fields have sensible defaults
                        for field in ['total_distance', 'avg_pace', 'avg_hr', 'pace_limit']:
                            if field not in run_dict or run_dict[field] is None:
                                run_dict[field] = 0
                        
                        result.append(run_dict)
                    except Exception as run_error:
                        print(f"Error processing run record: {str(run_error)}")
                        traceback.print_exc()
                        # Skip this run but continue with others
                
                return result
                
            except Exception as query_error:
                print(f"Database query error: {str(query_error)}")
                traceback.print_exc()
                try:
                    self.conn.rollback()
                except:
                    pass
                return []
            
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
            if POSTGRES_AVAILABLE and isinstance(self.conn, psycopg2.extensions.connection):
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
            if POSTGRES_AVAILABLE and isinstance(self.conn, psycopg2.extensions.connection):
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
            if POSTGRES_AVAILABLE and isinstance(self.conn, psycopg2.extensions.connection):
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
            
            if POSTGRES_AVAILABLE and isinstance(self.conn, psycopg2.extensions.connection):
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
            
            if POSTGRES_AVAILABLE and isinstance(self.conn, psycopg2.extensions.connection):
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
            if POSTGRES_AVAILABLE and isinstance(self.conn, psycopg2.extensions.connection):
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
            
            if POSTGRES_AVAILABLE and isinstance(self.conn, psycopg2.extensions.connection):
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
            if POSTGRES_AVAILABLE and isinstance(self.conn, psycopg2.extensions.connection):
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
                if POSTGRES_AVAILABLE and isinstance(self.conn, psycopg2.extensions.connection):
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
            if POSTGRES_AVAILABLE and isinstance(self.conn, psycopg2.extensions.connection):
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
            if POSTGRES_AVAILABLE and isinstance(self.conn, psycopg2.extensions.connection):
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
            
            if POSTGRES_AVAILABLE and isinstance(self.conn, psycopg2.extensions.connection):
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
            
            if POSTGRES_AVAILABLE and isinstance(self.conn, psycopg2.extensions.connection):
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
            
            if POSTGRES_AVAILABLE and isinstance(self.conn, psycopg2.extensions.connection):
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