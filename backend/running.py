import xml.etree.ElementTree as ET
from datetime import datetime
from math import radians, sin, cos, sqrt, atan2, isnan
import traceback
import os
import glob
import json
from tzlocal import get_localzone
import pytz

# Add these constants at the top
TRAINING_ZONES = {
    'Zone 1': {
        'name': 'Recovery',
        'range': (0.30, 0.40),  # 30-40% of HRR
        'description': 'Very light intensity, active recovery, improves basic endurance',
        'color': '#7FB3D5'  # Light blue
    },
    'Zone 2': {
        'name': 'Aerobic',
        'range': (0.40, 0.60),  # 40-60% of HRR
        'description': 'Light aerobic, fat burning, builds endurance',
        'color': '#2ECC71'  # Green
    },
    'Zone 3': {
        'name': 'Tempo',
        'range': (0.60, 0.70),  # 60-70% of HRR
        'description': 'Moderate intensity, improves efficiency and aerobic capacity',
        'color': '#F4D03F'  # Yellow
    },
    'Zone 4': {
        'name': 'Threshold',
        'range': (0.70, 0.85),  # 70-85% of HRR
        'description': 'Hard intensity, increases lactate threshold and speed',
        'color': '#E67E22'  # Orange
    },
    'Zone 5': {
        'name': 'VO2 Max',
        'range': (0.85, 1.00),  # 85-100% of HRR
        'description': 'Maximum effort, improves speed and power',
        'color': '#E74C3C'  # Red
    }
}

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
    # Parse UTC time from GPX
    utc_time = datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%SZ")
    utc_time = pytz.utc.localize(utc_time)
    # Convert to local time
    local_tz = get_localzone()
    return utc_time.astimezone(local_tz)

# Function to parse GPX data and calculate distance under specified pace
def analyze_run_file(file_path, pace_limit, user_age=None, resting_hr=None):
    try:
        print(f"Attempting to read file: {file_path}")
        print(f"Parameters: pace_limit={pace_limit}, age={user_age}, resting_hr={resting_hr}")
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
        point_segments = []
        fast_segments = []
        slow_segments = []
        total_fast_distance = 0
        total_slow_distance = 0
        elevation_data = []
        
        # Mile split tracking
        current_mile = 0
        mile_splits = []
        accumulated_distance = 0
        mile_start_time = None
        mile_hr_values = []   # Separate list for mile splits
        
        # Get local timezone
        local_tz = get_localzone()
        
        # Extract trackpoints
        trkpt_list = root.findall('.//gpx:trkpt', ns)
        print(f"Found {len(trkpt_list)} trackpoints")
        
        prev_point = None
        
        # Add this to track all heart rates
        all_heart_rates = []  # Track all heart rates for the entire run
        
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
                        all_heart_rates.append(hr)  # Add to all heart rates
                        break
                except:
                    continue
            
            if time_elem is not None:
                # Convert UTC time to local time
                utc_time = datetime.strptime(time_elem.text, '%Y-%m-%dT%H:%M:%SZ')
                utc_time = pytz.utc.localize(utc_time)
                time = utc_time.astimezone(local_tz)
                
                current_point = {
                    'lat': lat,
                    'lon': lon,
                    'time': time,
                    'hr': hr
                }
                
                # Get elevation
                ele_elem = trkpt.find('.//gpx:ele', ns)
                elevation = float(ele_elem.text) if ele_elem is not None else 0
                elevation_data.append({
                    'time': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
                    'elevation': elevation * 3.28084  # Convert meters to feet
                })
                
                if prev_point:
                    distance = haversine(prev_point['lat'], prev_point['lon'], lat, lon)
                    time_diff = (time - prev_point['time']).total_seconds() / 60
                    total_distance_all += distance
                    accumulated_distance += distance
                    
                    if hr is not None:
                        mile_hr_values.append(hr)  # Use separate list for mile splits
                    
                    # Track mile splits
                    if mile_start_time is None:
                        mile_start_time = prev_point['time']
                    
                    while accumulated_distance >= (current_mile + 1):
                        # Calculate where exactly the mile was completed
                        mile_completion = current_mile + 1
                        distance_over = accumulated_distance - mile_completion
                        portion = distance_over / distance
                        mile_end_time = time - (time - prev_point['time']) * portion
                        
                        # Calculate actual time taken for this mile
                        split_time = (mile_end_time - mile_start_time).total_seconds()  # Get total seconds
                        split_minutes = split_time / 60.0  # Convert to minutes
                        
                        mile_splits.append({
                            'mile': current_mile + 1,
                            'split_time': split_minutes,  # Total time for this mile
                            'split_pace': split_minutes,  # Same as split time since it's one mile
                            'avg_hr': sum(mile_hr_values) / len(mile_hr_values) if mile_hr_values else 0
                        })
                        
                        # Start next mile from the mile marker
                        current_mile += 1
                        mile_start_time = mile_end_time  # Start next mile from where this one ended
                        mile_hr_values = []
                    
                    if time_diff > 0 and distance > 0:
                        pace = time_diff / distance  # minutes per mile
                        
                        # Store point-to-point segment with local time
                        point_segments.append({
                            'start_time': prev_point['time'].strftime('%Y-%m-%dT%H:%M:%S%z'),
                            'end_time': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
                            'start_point': {
                                'lat': prev_point['lat'],
                                'lon': prev_point['lon']
                            },
                            'end_point': {
                                'lat': lat,
                                'lon': lon
                            },
                            'distance': distance,
                            'time_diff': time_diff,
                            'pace': pace,
                            'hr': prev_point['hr']
                        })
                
                prev_point = current_point
        
        # Initialize segment lists
        current_fast_segment = None
        current_slow_segment = None

        # Handle first point
        if point_segments:
            if point_segments[0]['pace'] <= pace_limit:
                current_fast_segment = {
                    'start_time': point_segments[0]['start_time'],
                    'end_time': point_segments[0]['end_time'],
                    'distance': point_segments[0]['distance'],
                    'time_diff': point_segments[0]['time_diff'],
                    'hr_values': [point_segments[0]['hr']] if point_segments[0]['hr'] is not None else [],
                    'best_pace': point_segments[0]['pace'],
                    'points': [point_segments[0]['start_point']],
                    'pace': point_segments[0]['pace']
                }
                total_fast_distance += point_segments[0]['distance']
            else:
                current_slow_segment = {
                    'start_time': point_segments[0]['start_time'],
                    'end_time': point_segments[0]['end_time'],
                    'distance': point_segments[0]['distance'],
                    'time_diff': point_segments[0]['time_diff'],
                    'hr_values': [point_segments[0]['hr']] if point_segments[0]['hr'] is not None else [],
                    'best_pace': point_segments[0]['pace'],
                    'points': [point_segments[0]['start_point']],
                    'pace': point_segments[0]['pace']
                }
                total_slow_distance += point_segments[0]['distance']

        for i, segment in enumerate(point_segments[1:], 1):
            if segment['pace'] <= pace_limit:
                if current_fast_segment is None:
                    # End slow segment if exists
                    if current_slow_segment is not None:
                        # Add final point to slow segment
                        current_slow_segment['points'].append(segment['start_point'])
                        current_slow_segment['pace'] = current_slow_segment['time_diff'] / current_slow_segment['distance']
                        current_slow_segment['avg_hr'] = (sum(current_slow_segment['hr_values']) / 
                                                        len(current_slow_segment['hr_values'])) if current_slow_segment['hr_values'] else 0
                        slow_segments.append(current_slow_segment)
                        current_slow_segment = None

                    # Start new fast segment
                    current_fast_segment = {
                        'start_time': segment['start_time'],
                        'end_time': segment['end_time'],
                        'distance': segment['distance'],
                        'time_diff': segment['time_diff'],
                        'hr_values': [segment['hr']] if segment['hr'] is not None else [],
                        'best_pace': segment['pace'],
                        'points': [segment['start_point']],
                        'pace': segment['pace']
                    }
                    total_fast_distance += segment['distance']
                else:
                    # Continue fast segment
                    current_fast_segment['distance'] += segment['distance']
                    current_fast_segment['time_diff'] += segment['time_diff']
                    current_fast_segment['end_time'] = segment['end_time']
                    if segment['hr'] is not None:
                        current_fast_segment['hr_values'].append(segment['hr'])
                    current_fast_segment['best_pace'] = min(current_fast_segment['best_pace'], segment['pace'])
                    current_fast_segment['points'].append(segment['start_point'])
                    total_fast_distance += segment['distance']
            else:
                # Handle slow segment
                if current_slow_segment is None:
                    # End fast segment if exists
                    if current_fast_segment is not None:
                        current_fast_segment['points'].append(segment['start_point'])
                        current_fast_segment['pace'] = current_fast_segment['time_diff'] / current_fast_segment['distance']
                        current_fast_segment['avg_hr'] = (sum(current_fast_segment['hr_values']) / 
                                                        len(current_fast_segment['hr_values'])) if current_fast_segment['hr_values'] else 0
                        fast_segments.append(current_fast_segment)
                        current_fast_segment = None
                    
                    # Start new slow segment
                    current_slow_segment = {
                        'start_time': segment['start_time'],
                        'end_time': segment['end_time'],
                        'distance': segment['distance'],
                        'time_diff': segment['time_diff'],
                        'hr_values': [segment['hr']] if segment['hr'] is not None else [],
                        'best_pace': segment['pace'],
                        'points': [segment['start_point']]
                    }
                    total_slow_distance += segment['distance']
                else:
                    # Continue slow segment
                    current_slow_segment['distance'] += segment['distance']
                    current_slow_segment['time_diff'] += segment['time_diff']
                    current_slow_segment['end_time'] = segment['end_time']
                    if segment['hr'] is not None:
                        current_slow_segment['hr_values'].append(segment['hr'])
                    current_slow_segment['best_pace'] = min(current_slow_segment['best_pace'], segment['pace'])
                    current_slow_segment['points'].append(segment['start_point'])
                    total_slow_distance += segment['distance']
            
            # Add debug logging
            print(f"\nProcessing point {i}:")
            print(f"Current pace: {segment['pace']}")
            print(f"Fast segment active: {current_fast_segment is not None}")
            print(f"Slow segment active: {current_slow_segment is not None}")
            if current_fast_segment:
                print(f"Fast segment distance: {current_fast_segment['distance']}")
            if current_slow_segment:
                print(f"Slow segment distance: {current_slow_segment['distance']}")
        
        # Handle final segments
        if current_fast_segment is not None:
            current_fast_segment['points'].append(point_segments[-1]['end_point'])
            current_fast_segment['pace'] = current_fast_segment['time_diff'] / current_fast_segment['distance']
            current_fast_segment['avg_hr'] = (sum(current_fast_segment['hr_values']) / 
                                            len(current_fast_segment['hr_values'])) if current_fast_segment['hr_values'] else 0
            fast_segments.append(current_fast_segment)

        if current_slow_segment is not None:
            current_slow_segment['points'].append(point_segments[-1]['end_point'])
            current_slow_segment['pace'] = current_slow_segment['time_diff'] / current_slow_segment['distance']
            current_slow_segment['avg_hr'] = (sum(current_slow_segment['hr_values']) / 
                                            len(current_slow_segment['hr_values'])) if current_slow_segment['hr_values'] else 0
            slow_segments.append(current_slow_segment)
        
        # Calculate averages
        avg_hr_all = total_hr / total_hr_count if total_hr_count > 0 else 0
        avg_hr_fast = (sum(segment['avg_hr'] for segment in fast_segments) / 
                      len(fast_segments)) if fast_segments else 0
        avg_hr_slow = (sum(segment['avg_hr'] for segment in slow_segments) / 
                      len(slow_segments)) if slow_segments else 0
        
        # Calculate training zones if age and resting HR provided
        training_zones = calculate_training_zones(all_heart_rates, user_age, resting_hr) if user_age and resting_hr else None
        print("\nDebug - Training Zones:")
        print(f"Age: {user_age}")
        print(f"Resting HR: {resting_hr}")
        print(f"Number of heart rate points: {len(all_heart_rates)}")
        print(f"Training zones data: {training_zones}")
        
        # Get pace recommendations
        recent_paces = [segment['pace'] for segment in fast_segments]
        pace_recommendations = get_pace_recommendations(recent_paces)
        
        # Collect route data for mapping
        route_data = [{
            'lat': point['start_point']['lat'],
            'lon': point['start_point']['lon'],
            'elevation': elevation_data[i]['elevation'] if i < len(elevation_data) else 0,
            'time': point['start_time'],
            'hr': point['hr'],
            'pace': point['pace'],
            'distance': point['distance']
        } for i, point in enumerate(point_segments)]
        
        # Before returning results
        print("Debug - Route data:", route_data[:5])  # Show first 5 points
        print("\nDebug - Fast segments sample:")
        for segment in fast_segments[:2]:
            print(f"Start point: {segment['points'][0]}")
            print(f"End point: {segment['points'][-1]}")
            print(f"Distance: {segment['distance']}")
            print(f"Pace: {segment['pace']}")
            print("---")

        print("\nDebug - Slow segments sample:")
        for segment in slow_segments[:2]:
            print(f"Start point: {segment['points'][0]}")
            print(f"End point: {segment['points'][-1]}")
            print(f"Distance: {segment['distance']}")
            print(f"Pace: {segment['pace']}")
            print("---")
        
        # Debug segment creation
        print("\nDebug - Creating segments:")
        print(f"Number of point segments: {len(point_segments)}")
        print(f"First point segment: {point_segments[0]}")
        print(f"Last point segment: {point_segments[-1]}")
        
        # After creating segments
        print("\nDebug - Created segments:")
        print(f"Number of fast segments: {len(fast_segments)}")
        print(f"Number of slow segments: {len(slow_segments)}")
        if fast_segments:
            print(f"Sample fast segment: {fast_segments[0]}")
        if slow_segments:
            print(f"Sample slow segment: {slow_segments[0]}")
        
        # Return the results
        return {
            'total_distance': total_distance_all,
            'fast_distance': total_fast_distance,
            'slow_distance': total_slow_distance,
            'percentage_fast': (total_fast_distance/total_distance_all)*100 if total_distance_all > 0 else 0,
            'percentage_slow': (total_slow_distance/total_distance_all)*100 if total_distance_all > 0 else 0,
            'avg_hr_all': avg_hr_all,
            'avg_hr_fast': avg_hr_fast,
            'avg_hr_slow': avg_hr_slow,
            'fast_segments': fast_segments,
            'slow_segments': slow_segments,
            'elevation_data': elevation_data,
            'mile_splits': mile_splits,
            'route_data': point_segments,
            'pace_limit': float(pace_limit),
            'training_zones': training_zones,
            'pace_recommendations': pace_recommendations
        }
        
    except Exception as e:
        print(f"Error processing file: {str(e)}")
        traceback.print_exc()
        return 0, 0, 0, [], [], 0, 0, 0, [], [], None, None, []

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
    total_fast_distance, total_slow_distance, total_distance_all, 
    fast_segments, slow_segments, avg_hr_all, avg_hr_fast, avg_hr_slow,
    elevation_data, mile_splits, training_zones, pace_recommendations, route_data = results
    
    def format_time(iso_time_str):
        # Parse ISO format string and format for display
        try:
            dt = datetime.fromisoformat(iso_time_str)
            return dt.strftime('%I:%M:%S %p')  # Format as '11:23:45 AM'
        except:
            return iso_time_str
    
    # Format the results
    run_data = {
        "timestamp": timestamp,
        "gpx_file": os.path.basename(file_path),
        "pace_limit": pace_limit,
        "total_distance": round(total_distance_all, 2),
        "fast_distance": round(total_fast_distance, 2),
        "slow_distance": round(total_slow_distance, 2),
        "percentage_fast": round((total_fast_distance/total_distance_all)*100 if total_distance_all > 0 else 0, 1),
        "percentage_slow": round((total_slow_distance/total_distance_all)*100 if total_distance_all > 0 else 0, 1),
        "avg_hr_all": round(avg_hr_all, 0),
        "avg_hr_fast": round(avg_hr_fast, 0),
        "avg_hr_slow": round(avg_hr_slow, 0),
        "fast_segments": fast_segments,
        "slow_segments": slow_segments,
        "elevation_data": elevation_data,
        "mile_splits": mile_splits,
        "training_zones": training_zones,
        "pace_recommendations": pace_recommendations,
        "route_data": route_data
    }
    
    # Write to log file
    with open(log_file, "a") as f:
        f.write("\n" + "="*80 + "\n")
        f.write(f"Run Analysis - {timestamp}\n")
        f.write(f"File: {run_data['gpx_file']}\n")
        f.write(f"Pace Limit: {pace_limit} min/mile\n")
        f.write(f"Total Distance: {run_data['total_distance']} miles\n")
        f.write(f"Distance under {pace_limit} min/mile: {run_data['fast_distance']} miles ({run_data['percentage_fast']}%)\n")
        f.write(f"Distance over {pace_limit} min/mile: {run_data['slow_distance']} miles ({run_data['percentage_slow']}%)\n")
        f.write(f"Average Heart Rate (Overall): {run_data['avg_hr_all']} bpm\n")
        f.write(f"Average Heart Rate (Fast Segments): {run_data['avg_hr_fast']} bpm\n")
        f.write(f"Average Heart Rate (Slow Segments): {run_data['avg_hr_slow']} bpm\n")
        
        if fast_segments:
            f.write("\nFast Segments:\n")
            for i, segment in enumerate(fast_segments, 1):
                f.write(f"Segment {i}: {segment['distance']:.2f} miles at {segment['pace']:.1f} min/mile pace "
                       f"(Best: {segment['best_pace']:.1f}, Avg HR: {round(segment['avg_hr'])} bpm)\n")
                f.write(f"  Time: {format_time(segment['start_time'])} to {format_time(segment['end_time'])}\n")
        else:
            f.write("\nNo segments under target pace\n")
        
        if slow_segments:
            f.write("\nSlow Segments:\n")
            for i, segment in enumerate(slow_segments, 1):
                f.write(f"Segment {i}: {segment['distance']:.2f} miles at {segment['pace']:.1f} min/mile pace "
                       f"(Best: {segment['best_pace']:.1f}, Avg HR: {round(segment['avg_hr'])} bpm)\n")
                f.write(f"  Time: {format_time(segment['start_time'])} to {format_time(segment['end_time'])}\n")
        else:
            f.write("\nNo segments over target pace\n")
        
        f.write("\n")
    
    return run_data

def calculate_training_zones(hr_data, age, resting_hr):
    """Calculate time spent in each heart rate zone using Heart Rate Reserve method"""
    if not age or not hr_data or resting_hr is None:
        return None
        
    max_hr = 208 - (0.7 * age)  # Using Tanaka formula for max HR
    hrr = max_hr - resting_hr  # Heart Rate Reserve
    
    zones_data = {zone: {
        'name': info['name'],
        'count': 0,
        'time': 0,
        'description': info['description'],
        'color': info['color'],
        'range': (
            int(resting_hr + (info['range'][0] * hrr)),  # Lower bound using HRR
            int(resting_hr + (info['range'][1] * hrr))   # Upper bound using HRR
        )
    } for zone, info in TRAINING_ZONES.items()}
    
    # Count points in each zone
    for hr in hr_data:
        if hr:  # Skip None values
            for zone, data in zones_data.items():
                if data['range'][0] <= hr <= data['range'][1]:
                    data['count'] += 1
                    break
    
    total_points = len([hr for hr in hr_data if hr])  # Count only valid HR points
    
    # Calculate percentages and times
    for zone_data in zones_data.values():
        zone_data['percentage'] = (zone_data['count'] / total_points * 100) if total_points > 0 else 0
        zone_data['time'] = zone_data['count'] * 3  # Assuming 3-second intervals
    
    return zones_data

def get_pace_recommendations(recent_paces, target_race_distance=None):
    """Generate pace recommendations based on recent performance"""
    if not recent_paces:
        return None
        
    avg_pace = sum(recent_paces) / len(recent_paces)
    best_pace = min(recent_paces)
    
    recommendations = {
        'Easy': avg_pace * 1.3,  # 30% slower than average
        'Recovery': avg_pace * 1.4,  # 40% slower than average
        'Long Run': avg_pace * 1.2,  # 20% slower than average
        'Tempo': best_pace * 1.1,  # 10% slower than best
        'Interval': best_pace * 0.95,  # 5% faster than best
    }
    
    return recommendations

def calculate_pace_zones(recent_runs):
    """Calculate recommended pace zones based on recent performance"""
    if not recent_runs:
        return None

    # Get average and best paces from recent runs
    paces = []
    for run in recent_runs:
        # Use the data field from the dictionary
        run_data = json.loads(run['data']) if isinstance(run['data'], str) else run['data']
        fast_segments = run_data.get('fast_segments', [])
        if fast_segments:
            paces.extend([segment['pace'] for segment in fast_segments])

    if not paces:
        return None

    avg_pace = sum(paces) / len(paces)
    best_pace = min(paces)

    return {
        'Recovery': {
            'range': (avg_pace * 1.4, avg_pace * 1.5),
            'description': 'Very easy running, for recovery days'
        },
        'Easy': {
            'range': (avg_pace * 1.2, avg_pace * 1.3),
            'description': 'Comfortable pace for building endurance'
        },
        'Long Run': {
            'range': (avg_pace * 1.1, avg_pace * 1.2),
            'description': 'Slightly faster than easy pace'
        },
        'Tempo': {
            'range': (best_pace * 1.05, best_pace * 1.1),
            'description': 'Comfortably hard, sustainable for 20-40 minutes'
        },
        'Interval': {
            'range': (best_pace * 0.9, best_pace * 0.95),
            'description': 'Fast pace for short intervals'
        }
    }

def analyze_elevation_impact(point_segments):
    """Analyze how elevation affects pace"""
    elevation_pace_data = []
    for i in range(len(point_segments) - 1):
        current = point_segments[i]
        next_point = point_segments[i + 1]
        
        # Get elevation from start_point and end_point
        current_elevation = float(current.get('elevation', 0))
        next_elevation = float(next_point.get('elevation', 0))
        
        elevation_change = next_elevation - current_elevation
        pace = float(current.get('pace', 0))
        
        if not isnan(pace) and not isnan(elevation_change):
            elevation_pace_data.append({
                'elevation_change': elevation_change,
                'pace': pace,
                'distance': float(current.get('distance', 0))
            })
    
    return elevation_pace_data

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
    total_fast_distance, total_slow_distance, total_distance_all, 
    fast_segments, slow_segments, avg_hr_all, avg_hr_fast, avg_hr_slow,
    elevation_data, mile_splits, training_zones, pace_recommendations, route_data = result
    
    print(f"\nAnalyzing file: {file_path}")
    print(f"Total run distance: {total_distance_all:.2f} miles")
    print(f"Distance under {pace_limit} minute pace: {total_fast_distance:.2f} miles ({round((total_fast_distance/total_distance_all)*100, 1)}%)")
    print(f"Distance over {pace_limit} minute pace: {total_slow_distance:.2f} miles ({round((total_slow_distance/total_distance_all)*100, 1)}%)")
    print(f"Average Heart Rate (Overall): {round(avg_hr_all)} bpm")
    if total_distance_all > 0:
        print(f"Average Heart Rate (Fast Segments): {round(avg_hr_fast)} bpm")
        print(f"Average Heart Rate (Slow Segments): {round(avg_hr_slow)} bpm")
        
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