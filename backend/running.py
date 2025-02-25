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
        print(f"File parsed successfully. Root tag: {root.tag}")
        
        # Define all possible namespaces
        ns = {
            'gpx': 'http://www.topografix.com/GPX/1/1',
            'ns3': 'http://www.garmin.com/xmlschemas/TrackPointExtension/v1'
        }
        
        # Initialize all variables
        trackpoints = []
        total_distance = 0
        total_distance_all = 0
        total_hr = 0
        total_hr_count = 0
        fast_hr = 0
        fast_hr_count = 0
        prev_lat = None
        prev_lon = None
        prev_time = None
        
        # Initialize fast segments tracking
        fast_segments = []
        current_segment_distance = 0
        current_segment_start_time = None
        current_segment_hr = 0
        current_segment_hr_count = 0
        
        # Extract trackpoints with time and coordinates
        trkpt_list = root.findall('.//gpx:trkpt', ns)
        print(f"Found {len(trkpt_list)} trackpoints")
        
        for trkpt in trkpt_list:
            lat = float(trkpt.get('lat'))
            lon = float(trkpt.get('lon'))
            time_elem = trkpt.find('.//gpx:time', ns)
            
            # Try different common paths for heart rate data
            hr_elem = None
            hr_paths = [
                './/ns3:TrackPointExtension/ns3:hr',
                './/gpx:extensions//hr',
                './/extensions//hr',
                './/hr'
            ]
            
            for path in hr_paths:
                try:
                    hr_elem = trkpt.find(path, ns)
                    if hr_elem is not None:
                        break
                except:
                    continue
            
            print(f"Point - Lat: {lat}, Lon: {lon}")  # Debug
            
            # Process heart rate if available
            if hr_elem is not None:
                try:
                    hr = int(hr_elem.text)
                    total_hr += hr
                    total_hr_count += 1
                except (ValueError, TypeError):
                    pass  # Skip if heart rate value is invalid
            
            if time_elem is not None:
                time_str = time_elem.text
                time = datetime.strptime(time_str, '%Y-%m-%dT%H:%M:%SZ')
                print(f"Time: {time}")  # Debug
                
                if prev_lat is not None and prev_lon is not None and prev_time is not None:
                    # Calculate distance between points - fixed haversine call
                    distance = haversine(prev_lat, prev_lon, lat, lon)
                    print(f"Distance between points: {distance} miles")  # Debug
                    
                    # Calculate time difference
                    time_diff = (time - prev_time).total_seconds() / 60  # Convert to minutes
                    
                    if time_diff > 0:  # Avoid division by zero
                        pace = time_diff / distance if distance > 0 else float('inf')
                        print(f"Pace: {pace} min/mile")  # Debug
                        
                        total_distance_all += distance
                        if pace <= pace_limit:
                            total_distance += distance
                            if hr_elem is not None:
                                fast_hr += hr
                                fast_hr_count += 1
                            
                            # Track fast segment
                            if current_segment_start_time is None:
                                current_segment_start_time = prev_time
                            current_segment_distance += distance
                            if hr_elem is not None:
                                current_segment_hr += hr
                                current_segment_hr_count += 1
                        else:
                            # End current fast segment if exists
                            if current_segment_distance > 0:
                                segment_duration = (prev_time - current_segment_start_time).total_seconds() / 60
                                segment_pace = segment_duration / current_segment_distance
                                segment_avg_hr = current_segment_hr / current_segment_hr_count if current_segment_hr_count > 0 else 0
                                fast_segments.append((current_segment_distance, segment_pace, segment_avg_hr))
                                current_segment_distance = 0
                                current_segment_start_time = None
                                current_segment_hr = 0
                                current_segment_hr_count = 0
            
            prev_lat = lat
            prev_lon = lon
            if time_elem is not None:
                prev_time = time
            
            # Break after a few points during debugging
            if len(trackpoints) < 5:  # Only process first 5 points for debugging
                trackpoints.append((lat, lon, time if time_elem is not None else None))
        
        # Add final fast segment if exists
        if current_segment_distance > 0:
            segment_duration = (prev_time - current_segment_start_time).total_seconds() / 60
            segment_pace = segment_duration / current_segment_distance
            segment_avg_hr = current_segment_hr / current_segment_hr_count if current_segment_hr_count > 0 else 0
            fast_segments.append((current_segment_distance, segment_pace, segment_avg_hr))
        
        # Calculate averages
        avg_hr_all = total_hr / total_hr_count if total_hr_count > 0 else 0
        avg_hr_fast = fast_hr / fast_hr_count if fast_hr_count > 0 else 0
        
        print(f"Final total_distance: {total_distance}")  # Debug
        print(f"Final total_distance_all: {total_distance_all}")  # Debug
        
        return total_distance, total_distance_all, fast_segments, avg_hr_all, avg_hr_fast
        
    except Exception as e:
        print(f"Error processing file: {str(e)}")
        traceback.print_exc()  # This will print the full error traceback
        return 0, 0, [], 0, 0  # Return empty list for fast_segments on error

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
        "fast_segments": [
            {
                "distance": round(dist, 2),
                "pace": round(pace, 1),
                "avg_hr": round(hr, 0)
            }
            for dist, pace, hr in fast_segments
        ]
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
            for i, segment in enumerate(run_data['fast_segments'], 1):
                f.write(f"Segment {i}: {segment['distance']} miles at {segment['pace']} min/mile pace (Avg HR: {segment['avg_hr']} bpm)\n")
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
    
    # Display results as before
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
            for i, (dist, pace, hr) in enumerate(fast_segments, 1):
                print(f"Segment {i}: {dist:.2f} miles at {pace:.1f} min/mile pace (Avg HR: {round(hr)} bpm)")
        else:
            print("\nNo segments found under the target pace.")
            
    print(f"\nResults have been saved to {os.path.abspath('running_log.txt')}")

if __name__ == "__main__":
    main()