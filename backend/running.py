import xml.etree.ElementTree as ET
from datetime import datetime
from math import radians, sin, cos, sqrt, atan2
import traceback
import os
import glob
import json

# Function to calculate distance using Haversine formula
def haversine(lat1, lon1, lat2, lon2):    
    R = 3956  # Radius of Earth in miles   
    dlat = radians(lat2 - lat1)    
    dlon = radians(lon2 - lon1)    
    a = (sin(dlat / 2) ** 2 +         
         cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2)    
    c = 2 * atan2(sqrt(a), sqrt(1 - a))    
    return R * c

# Parse datetime from ISO format
def parse_time(time_str):
    return datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%SZ")

# Function to parse GPX data and calculate distance under specified pace
def analyze_run_file(file_path, pace_limit):
    try:
        print(f"Attempting to read file: {file_path}")
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        ns = {
            'gpx': 'http://www.topografix.com/GPX/1/1',
            'ns3': 'http://www.garmin.com/xmlschemas/TrackPointExtension/v1'
        }
        
        # Initialize variables
        total_distance_all = 0
        total_hr = 0
        total_hr_count = 0
        point_segments = []  # Store all point-to-point segments
        fast_segments = []
        
        # Extract trackpoints
        trkpt_list = root.findall('.//gpx:trkpt', ns)
        print(f"Found {len(trkpt_list)} trackpoints")
        
        prev_point = None
        
        # First pass: Calculate all point-to-point segments
        for trkpt in trkpt_list:
            lat = float(trkpt.get('lat'))
            lon = float(trkpt.get('lon'))
            time_elem = trkpt.find('.//gpx:time', ns)
            
            # Get heart rate
            hr = None
            for path in ['.//ns3:TrackPointExtension/ns3:hr', './/gpx:extensions//hr', './/extensions//hr', './/hr']:
                try:
                    hr_elem = trkpt.find(path, ns)
                    if hr_elem is not None:
                        hr = int(hr_elem.text)
                        total_hr += hr
                        total_hr_count += 1
                        break
                except:
                    continue
            
            if time_elem is not None:
                time = datetime.strptime(time_elem.text, '%Y-%m-%dT%H:%M:%SZ')
                
                current_point = {
                    'lat': lat,
                    'lon': lon,
                    'time': time,
                    'hr': hr
                }
                
                if prev_point:
                    # Calculate segment metrics
                    distance = haversine(prev_point['lat'], prev_point['lon'], lat, lon)
                    time_diff = (time - prev_point['time']).total_seconds() / 60  # minutes
                    total_distance_all += distance
                    
                    if time_diff > 0 and distance > 0:
                        pace = time_diff / distance  # minutes per mile
                        
                        # Store point-to-point segment
                        point_segments.append({
                            'start_time': prev_point['time'].isoformat(),
                            'end_time': time.isoformat(),
                            'start_point': prev_point,
                            'end_point': current_point,
                            'distance': distance,
                            'time_diff': time_diff,
                            'pace': pace,
                            'hr': prev_point['hr']
                        })
                
                prev_point = current_point
        
        # Second pass: Build fast segments from point segments
        current_segment = None
        
        for segment in point_segments:
            if segment['pace'] <= pace_limit:
                if current_segment is None:
                    # Start new segment
                    current_segment = {
                        'start_time': segment['start_time'],
                        'distance': segment['distance'],
                        'time_diff': segment['time_diff'],
                        'hr_values': [segment['hr']] if segment['hr'] is not None else []
                    }
                else:
                    # Continue segment
                    current_segment['distance'] += segment['distance']
                    current_segment['time_diff'] += segment['time_diff']
                    if segment['hr'] is not None:
                        current_segment['hr_values'].append(segment['hr'])
            
            elif current_segment is not None:
                # End segment
                current_segment['end_time'] = segment['start_time']  # End at start of slow segment
                
                # Calculate segment statistics
                segment_pace = current_segment['time_diff'] / current_segment['distance']
                segment_hr = (sum(current_segment['hr_values']) / 
                            len(current_segment['hr_values'])) if current_segment['hr_values'] else 0
                
                fast_segments.append({
                    'start_time': current_segment['start_time'],
                    'end_time': current_segment['end_time'],
                    'distance': current_segment['distance'],
                    'pace': segment_pace,
                    'avg_hr': segment_hr
                })
                
                current_segment = None
        
        # Handle last segment if still open
        if current_segment is not None:
            current_segment['end_time'] = point_segments[-1]['end_time']
            segment_pace = current_segment['time_diff'] / current_segment['distance']
            segment_hr = (sum(current_segment['hr_values']) / 
                        len(current_segment['hr_values'])) if current_segment['hr_values'] else 0
            
            fast_segments.append({
                'start_time': current_segment['start_time'],
                'end_time': current_segment['end_time'],
                'distance': current_segment['distance'],
                'pace': segment_pace,
                'avg_hr': segment_hr
            })
        
        # Calculate totals
        total_fast_distance = sum(segment['distance'] for segment in fast_segments)
        avg_hr_all = total_hr / total_hr_count if total_hr_count > 0 else 0
        avg_hr_fast = (sum(segment['avg_hr'] for segment in fast_segments) / 
                      len(fast_segments)) if fast_segments else 0
        
        return total_fast_distance, total_distance_all, fast_segments, avg_hr_all, avg_hr_fast
        
    except Exception as e:
        print(f"Error processing file: {str(e)}")
        traceback.print_exc()
        return 0, 0, [], 0, 0

def list_gpx_files(directory="~/Downloads"):
    # Expand the ~ to full home directory path
    directory = os.path.expanduser(directory)
    
    # Get all .gpx files in the directory
    gpx_files = glob.glob(os.path.join(directory, "*.gpx"))
    
    if not gpx_files:
        print(f"No GPX files found in {directory}")
        return None
        
    # Print the list of files
    print("\nAvailable GPX files:")
    for i, file_path in enumerate(gpx_files, 1):
        print(f"{i}. {os.path.basename(file_path)}")
    
    # Let user select a file
    while True:
        try:
            choice = int(input("\nEnter the number of the file you want to analyze (0 to quit): "))
            if choice == 0:
                return None
            if 1 <= choice <= len(gpx_files):
                return gpx_files[choice - 1]
            print("Please enter a valid number from the list.")
        except ValueError:
            print("Please enter a valid number.")

def save_run_results(file_path, pace_limit, results):
    log_file = "running_log.txt"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    total_distance, total_distance_all, fast_segments, avg_hr_all, avg_hr_fast = results
    
    # Format the results
    run_data = {
        "timestamp": timestamp,
        "gpx_file": os.path.basename(file_path),
        "pace_limit": pace_limit,
        "total_distance": round(total_distance_all, 2),
        "fast_distance": round(total_distance, 2),
        "percentage_fast": round((total_distance/total_distance_all)*100 if total_distance_all > 0 else 0, 1),
        "avg_hr_all": round(avg_hr_all, 0),
        "avg_hr_fast": round(avg_hr_fast, 0),
        "fast_segments": fast_segments  # No need to transform, already in correct format
    }
    
    # Write to log file
    with open(log_file, "a") as f:
        f.write("\n" + "="*80 + "\n")
        f.write(f"Run Analysis - {timestamp}\n")
        f.write(f"File: {run_data['gpx_file']}\n")
        f.write(f"Pace Limit: {pace_limit} min/mile\n")
        f.write(f"Total Distance: {run_data['total_distance']} miles\n")
        f.write(f"Average Heart Rate (Overall): {run_data['avg_hr_all']} bpm\n")
        f.write(f"Distance under {pace_limit} min/mile: {run_data['fast_distance']} miles ({run_data['percentage_fast']}%)\n")
        f.write(f"Average Heart Rate (Fast Segments): {run_data['avg_hr_fast']} bpm\n")
        
        if fast_segments:
            f.write("\nFast Segments:\n")
            for i, segment in enumerate(fast_segments, 1):
                f.write(f"Segment {i}: {segment['distance']:.2f} miles at {segment['pace']:.1f} min/mile pace "
                       f"(Avg HR: {round(segment['avg_hr'])} bpm)\n")
                f.write(f"  Time: {segment['start_time']} to {segment['end_time']}\n")
        else:
            f.write("\nNo segments under target pace\n")
        
        f.write("\n")
    
    return run_data

def main():
    # List and select GPX file
    file_path = list_gpx_files()
    
    if not file_path:
        print("No file selected. Exiting...")
        return
        
    # Get pace limit from user
    while True:
        try:
            pace_limit = float(input("Enter the pace limit (minutes per mile): "))
            if pace_limit > 0:
                break
            else:
                print("Please enter a positive number.")
        except ValueError:
            print("Please enter a valid number.")
    
    result = analyze_run_file(file_path, pace_limit)
    
    # Save results to log file
    run_data = save_run_results(file_path, pace_limit, result)
    
    # Display results
    total_distance, total_distance_all, fast_segments, avg_hr_all, avg_hr_fast = result
    
    print(f"\nAnalyzing file: {file_path}")
    print(f"Total run distance: {total_distance_all:.2f} miles")
    print(f"Average Heart Rate (Overall): {round(avg_hr_all)} bpm")
    if total_distance_all > 0:
        percentage = (total_distance/total_distance_all)*100
        print(f"Distance under {pace_limit} minute pace: {total_distance:.2f} miles ({percentage:.1f}%)")
        print(f"Average Heart Rate (Fast Segments): {round(avg_hr_fast)} bpm")
        
        if fast_segments:
            print("\nFast segment breakdown:")
            for i, segment in enumerate(fast_segments, 1):
                print(f"Segment {i}: {segment['distance']:.2f} miles at {segment['pace']:.1f} min/mile pace "
                      f"(Avg HR: {round(segment['avg_hr'])} bpm)")
                print(f"  Time: {segment['start_time']} to {segment['end_time']}")
        else:
            print("\nNo segments found under the target pace.")
            
    print(f"\nResults have been saved to {os.path.abspath('running_log.txt')}")

if __name__ == "__main__":
    main()