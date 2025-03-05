import sqlite3
import json

def migrate_pace_limits():
    """Update existing runs with pace_limit data from their JSON data field"""
    try:
        with sqlite3.connect('runs.db') as conn:
            cursor = conn.cursor()
            
            # First, check if pace_limit column exists and add it if not
            try:
                cursor.execute('SELECT pace_limit FROM runs LIMIT 1')
                print("pace_limit column already exists")
            except sqlite3.OperationalError:
                print("Adding pace_limit column to runs table")
                cursor.execute('ALTER TABLE runs ADD COLUMN pace_limit REAL')
                conn.commit()
                print("Successfully added pace_limit column")
            
            # Get all runs without pace_limit
            cursor.execute('SELECT id, data FROM runs WHERE pace_limit IS NULL')
            runs = cursor.fetchall()
            
            updated_count = 0
            for run_id, data_json in runs:
                try:
                    data = json.loads(data_json)
                    if 'pace_limit' in data:
                        pace_limit = data['pace_limit']
                        cursor.execute('UPDATE runs SET pace_limit = ? WHERE id = ?', 
                                      (pace_limit, run_id))
                        updated_count += 1
                    # Alternative: get it from the last slow_segments pace
                    elif 'slow_segments' in data and data['slow_segments']:
                        pace_limit = data['slow_segments'][0]['pace']
                        cursor.execute('UPDATE runs SET pace_limit = ? WHERE id = ?', 
                                      (pace_limit, run_id))
                        updated_count += 1
                except (json.JSONDecodeError, KeyError) as e:
                    print(f"Error processing run {run_id}: {e}")
                    
            conn.commit()
            print(f"Updated {updated_count} runs with pace_limit data")
    except Exception as e:
        print(f"Migration error: {e}")

if __name__ == "__main__":
    migrate_pace_limits() 