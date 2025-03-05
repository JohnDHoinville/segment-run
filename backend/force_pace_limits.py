import sqlite3
import json

def force_pace_limits():
    """Force default pace limits for runs with NULL values"""
    try:
        with sqlite3.connect('runs.db') as conn:
            cursor = conn.cursor()
            
            # Get all runs with NULL pace_limit 
            cursor.execute('SELECT id, data FROM runs WHERE pace_limit IS NULL')
            runs = cursor.fetchall()
            
            updated_count = 0
            for run_id, data_json in runs:
                try:
                    # Default to 10 min/mile if we can't extract it
                    pace_limit = 10.0
                    
                    # Try to extract from data if possible
                    if data_json:
                        data = json.loads(data_json)
                        # Check if explicit pace_limit is in data
                        if 'pace_limit' in data:
                            pace_limit = float(data['pace_limit'])
                        # Or derive from fastest slow segment
                        elif 'slow_segments' in data and data['slow_segments']:
                            # Find minimum pace in slow segments
                            paces = [seg.get('pace', 99) for seg in data['slow_segments'] 
                                    if isinstance(seg, dict)]
                            if paces:
                                pace_limit = min(paces)
                    
                    # Update the record with our best guess
                    cursor.execute('UPDATE runs SET pace_limit = ? WHERE id = ?', 
                                  (pace_limit, run_id))
                    updated_count += 1
                except Exception as e:
                    print(f"Error processing run {run_id}: {e}")
                    
            conn.commit()
            print(f"Updated {updated_count} runs with pace_limit data")
    except Exception as e:
        print(f"Migration error: {e}")

if __name__ == "__main__":
    force_pace_limits() 