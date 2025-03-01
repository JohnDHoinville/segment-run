import xml.etree.ElementTree as ET
from datetime import datetime
from math import radians, sin, cos, sqrt, atan2, isnan
import traceback
import os
import glob
import json
from tzlocal import get_localzone
import pytz
import math

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
def analyze_run_file(file_path, pace_limit, user_age=None, resting_hr=None, weight=None, gender=None):
    try:
        print(f"\n=== Starting Run Analysis ===")
        print(f"File path: {file_path}")
        print(f"Pace limit: {pace_limit} min/mile")
        print(f"User metrics - Age: {user_age}, Resting HR: {resting_hr}")
        print(f"Additional metrics - Weight: {weight} (entered in lbs), Gender: {gender}")
        
        # Convert from lbs to kg
        weight_in_kg = weight * 0.453592
        
        # Verify file exists
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"GPX file not found at {file_path}")
        
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        print("Successfully parsed GPX file")
        
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
        
        if not trkpt_list:
            print("No trackpoints found in GPX file")
            raise Exception("No trackpoints found in GPX file")
        
        # Add this to track all heart rates
        all_heart_rates = []  # Track all heart rates for the entire run
        
        # First pass: Process all points and create basic segments
        prev_point = None
        for trkpt in trkpt_list:
            try:
                lat = float(trkpt.get('lat'))
                lon = float(trkpt.get('lon'))
                time_elem = trkpt.find('.//gpx:time', ns)
                
                # Get elevation
                ele_elem = trkpt.find('.//gpx:ele', ns)
                elevation = float(ele_elem.text) if ele_elem is not None else 0
                
                # Get heart rate
                hr = None
                for path in ['.//ns3:TrackPointExtension/ns3:hr', './/gpx:extensions//hr', './/extensions//hr', './/hr']:
                    try:
                        hr_elem = trkpt.find(path, ns)
                        if hr_elem is not None:
                            hr = int(hr_elem.text)
                            all_heart_rates.append(hr)
                            break
                    except:
                        continue
                
                if time_elem is not None:
                    utc_time = datetime.strptime(time_elem.text, '%Y-%m-%dT%H:%M:%SZ')
                    utc_time = pytz.utc.localize(utc_time)
                    time = utc_time.astimezone(local_tz)
                    
                    if prev_point:
                        distance = haversine(prev_point['lat'], prev_point['lon'], lat, lon)
                        time_diff = (time - prev_point['time']).total_seconds() / 60
                        total_distance_all += distance
                        
                        if time_diff > 0:
                            pace = time_diff / distance if distance > 0 else float('inf')
                            
                            point_segment = {
                                'lat': lat,
                                'lon': lon,
                                'elevation': elevation,
                                'time': time,
                                'hr': hr,
                                'distance': distance,
                                'pace': pace,
                                'is_fast': pace <= pace_limit if pace != float('inf') else False,
                                'prev_point': prev_point
                            }
                            point_segments.append(point_segment)
                    
                    prev_point = {
                        'lat': lat,
                        'lon': lon,
                        'time': time,
                        'hr': hr,
                        'elevation': elevation
                    }
                
            except Exception as e:
                print(f"Error processing point: {str(e)}")
                continue
        
        # Create continuous segments
        segments = []
        current_segment = None
        
        for i, point in enumerate(point_segments):
            if not current_segment:
                # Start new segment with proper coordinate format
                current_segment = {
                    'points': [point['prev_point']],
                    'is_fast': point['is_fast'],
                    'start_time': point['prev_point']['time'],
                    'distance': 0,
                    'total_hr': 0,
                    'hr_count': 0,
                    'coordinates': []  # Initialize empty coordinates array
                }
                # Add first coordinate
                current_segment['coordinates'].append([
                    float(point['prev_point']['lat']),
                    float(point['prev_point']['lon'])
                ])
            
            # Add current point to segment with proper coordinate format
            current_segment['points'].append(point)
            current_segment['coordinates'].append([
                float(point['lat']),
                float(point['lon'])
            ])
            current_segment['distance'] += point['distance']
            if point['hr']:
                current_segment['total_hr'] += point['hr']
                current_segment['hr_count'] += 1
            
            # Check if we need to end current segment
            next_point = point_segments[i + 1] if i < len(point_segments) - 1 else None
            if next_point and next_point['is_fast'] != current_segment['is_fast']:
                # Ensure the segment has valid coordinates
                if len(current_segment['coordinates']) >= 2:
                    segments.append(finalize_segment(current_segment))
                current_segment = None
        
        # Add final segment if it has enough points
        if current_segment and len(current_segment['coordinates']) >= 2:
            segments.append(finalize_segment(current_segment))
        
        # Split into fast and slow segments, ensuring each has valid coordinates
        fast_segments = [s for s in segments if s['is_fast'] and len(s['coordinates']) >= 2]
        slow_segments = [s for s in segments if not s['is_fast'] and len(s['coordinates']) >= 2]
        
        # Calculate totals
        total_fast_distance = sum(s['distance'] for s in fast_segments)
        total_slow_distance = sum(s['distance'] for s in slow_segments)
        
        # Calculate heart rate averages
        fast_hr_values = [s['avg_hr'] for s in fast_segments if s['avg_hr'] > 0]
        slow_hr_values = [s['avg_hr'] for s in slow_segments if s['avg_hr'] > 0]
        
        avg_hr_fast = sum(fast_hr_values) / len(fast_hr_values) if fast_hr_values else 0
        avg_hr_slow = sum(slow_hr_values) / len(slow_hr_values) if slow_hr_values else 0
        avg_hr_all = sum(all_heart_rates) / len(all_heart_rates) if all_heart_rates else 0
        
        # Debug output
        print(f"\nAnalysis complete:")
        print(f"Total distance: {total_distance_all:.2f} miles")
        print(f"Fast distance: {total_fast_distance:.2f} miles")
        print(f"Slow distance: {total_slow_distance:.2f} miles")
        print(f"Average HR (All): {avg_hr_all:.0f} bpm")
        print(f"Average HR (Fast): {avg_hr_fast:.0f} bpm")
        print(f"Average HR (Slow): {avg_hr_slow:.0f} bpm")
        
        # Format route data for mapping with proper coordinate format
        route_data = []
        for segment in segments:
            if segment and segment['coordinates'] and len(segment['coordinates']) >= 2:
                segment_data = {
                    'type': 'fast' if segment['is_fast'] else 'slow',
                    'coordinates': segment['coordinates'],
                    'pace': segment['pace'],
                    'distance': segment['distance'],
                    'start_time': segment['start_time'],
                    'end_time': segment['end_time']
                }
                route_data.append(segment_data)

        # Debug output for route data
        print("\nRoute Data Check:")
        print(f"Number of route segments: {len(route_data)}")
        for i, seg in enumerate(route_data):
            print(f"Segment {i}: {seg['type']}, {len(seg['coordinates'])} points")
            print(f"First coordinate: {seg['coordinates'][0]}")
            print(f"Last coordinate: {seg['coordinates'][-1]}")

        # Calculate training zones
        training_zones = calculate_training_zones(all_heart_rates, user_age, resting_hr)
        print("\nTraining Zones Result:")
        print(json.dumps(training_zones, indent=2))

        # Calculate additional metrics
        max_hr = max(all_heart_rates) if all_heart_rates else None
        duration_minutes = (point_segments[-1]['time'] - point_segments[0]['time']).total_seconds() / 60
        avg_hr = sum(all_heart_rates) / len(all_heart_rates) if all_heart_rates else None
        
        print("\nCalculating advanced metrics:")
        print(f"Max HR: {max_hr}")
        print(f"Duration: {duration_minutes} minutes")
        print(f"Average HR: {avg_hr}")
        
        # Calculate VO2 Max
        vo2max = estimate_vo2max(
            age=user_age,
            weight=weight_in_kg,
            gender=gender,
            time_minutes=duration_minutes,
            distance_km=total_distance_all * 1.60934,  # Convert miles to km
            max_hr=max_hr
        )
        print(f"Calculated VO2 Max: {vo2max}")
        
        # Calculate training load
        training_load = calculate_training_load(
            duration_minutes=duration_minutes,
            avg_hr=avg_hr,
            max_hr=max_hr,
            resting_hr=resting_hr
        )
        print(f"Calculated Training Load: {training_load}")
        
        # Calculate recovery time
        recovery_time = recommend_recovery_time(
            training_load=training_load,
            resting_hr=resting_hr,
            age=user_age
        )
        print(f"Calculated Recovery Time: {recovery_time}")
        
        # Predict race times
        race_predictions = predict_race_times(
            [s['pace'] for s in fast_segments if s['pace'] != float('inf')]
        )
        print(f"Calculated Race Predictions: {race_predictions}")

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
            'route_data': route_data,
            'elevation_data': elevation_data,
            'mile_splits': mile_splits,
            'training_zones': training_zones,
            'pace_recommendations': get_pace_recommendations([s['pace'] for s in fast_segments if s['pace'] != float('inf')]),
            'pace_limit': float(pace_limit),
            'vo2max': vo2max,
            'training_load': training_load,
            'recovery_time': recovery_time,
            'race_predictions': race_predictions,
            'max_hr': max_hr
        }
        
    except Exception as e:
        print(f"\nError in analyze_run_file:")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        traceback.print_exc()
        raise Exception(f"Failed to analyze run: {str(e)}")

def finalize_segment(segment):
    """Helper function to calculate segment statistics"""
    points = segment['points']
    time_diff = (points[-1]['time'] - segment['start_time']).total_seconds() / 60
    
    # Ensure coordinates are valid
    if not segment['coordinates'] or len(segment['coordinates']) < 2:
        print(f"Warning: Invalid coordinates in segment")
        return None
    
    # Calculate pace
    pace = time_diff / segment['distance'] if segment['distance'] > 0 else float('inf')
    
    return {
        'is_fast': segment['is_fast'],
        'start_time': segment['start_time'],
        'end_time': points[-1]['time'],
        'distance': segment['distance'],
        'avg_hr': segment['total_hr'] / segment['hr_count'] if segment['hr_count'] > 0 else 0,
        'coordinates': segment['coordinates'],
        'time_diff': time_diff,
        'pace': pace,
        'elevation_points': [float(p.get('elevation', 0)) for p in points if isinstance(p, dict)],
        'start_point': segment['coordinates'][0],
        'end_point': segment['coordinates'][-1]
    }

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

def calculate_training_zones(heart_rates, user_age, resting_hr):
    print("\nCalculating training zones:")
    print(f"Heart rates: {len(heart_rates)} values")
    print(f"User age: {user_age}")
    print(f"Resting HR: {resting_hr}")
    
    if not heart_rates or not user_age or not resting_hr:
        print("Missing required data for training zones")
        return None
        
    # Calculate max HR using common formula
    max_hr = 220 - user_age
    heart_rate_reserve = max_hr - resting_hr
    
    print(f"Max HR: {max_hr}")
    print(f"Heart Rate Reserve: {heart_rate_reserve}")
    
    # Initialize zones with time spent
    zones = TRAINING_ZONES.copy()
    for zone in zones.values():
        zone['time_spent'] = 0
        zone['count'] = 0
        # Calculate actual heart rate ranges
        zone['hr_range'] = (
            int(resting_hr + (zone['range'][0] * heart_rate_reserve)),
            int(resting_hr + (zone['range'][1] * heart_rate_reserve))
        )
        print(f"Calculated HR range: {zone['hr_range']} for zone with HRR range {zone['range']}")
    
    # Count time spent in each zone
    for hr in heart_rates:
        hrr_percentage = (hr - resting_hr) / heart_rate_reserve
        
        for zone_name, zone_data in zones.items():
            if zone_data['range'][0] <= hrr_percentage <= zone_data['range'][1]:
                zone_data['time_spent'] += 1  # Assuming 1 second per data point
                zone_data['count'] += 1
                break
    
    # Convert seconds to minutes and calculate percentages
    total_time = sum(zone['time_spent'] for zone in zones.values())
    print(f"Total time: {total_time} seconds")
    
    for zone in zones.values():
        zone['time_spent'] = zone['time_spent'] / 60  # Convert to minutes
        zone['percentage'] = (zone['count'] / len(heart_rates) * 100) if heart_rates else 0
        zone.pop('count', None)  # Remove the count field
    
    print("Calculated zones:", zones)
    return zones

def get_pace_recommendations(recent_paces):
    """Calculate pace zones based on recent performance"""
    # Filter out any invalid paces
    valid_paces = [p for p in recent_paces if p != float('inf') and p > 0]
    
    if not valid_paces:
        return None

    avg_pace = sum(valid_paces) / len(valid_paces)
    best_pace = min(valid_paces)

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

def estimate_vo2max(age, weight, gender, time_minutes, distance_km, max_hr):
    """Estimate VO2 Max using heart rate and pace data"""
    if not all([age, weight, time_minutes, distance_km, max_hr]):
        print("VO2 Max calculation missing required data:", {
            'age': age, 'weight': weight, 'time': time_minutes,
            'distance': distance_km, 'max_hr': max_hr
        })
        return None
        
    speed_kmh = distance_km / (time_minutes / 60)
    print(f"VO2 Max calculation - Speed: {speed_kmh} km/h")
    # Use a standard formula: Modified Uth-Sörensen-Overgaard formula
    resting_hr = 60  # Fallback if not available
    vo2max = 15.3 * (max_hr / resting_hr)
    
    # Convert speed to min per km pace for adjustment
    pace_km = (time_minutes / distance_km)
    
    # Adjust based on speed - faster runners have higher VO2max
    if pace_km < 4.5:  # Faster than 4:30 min/km
        vo2max *= 1.15
    elif pace_km < 5.5:  # Faster than 5:30 min/km
        vo2max *= 1.05
    
    return round(vo2max, 1)

def calculate_training_load(duration_minutes, avg_hr, max_hr, resting_hr):
    """Calculate Training Load using Banister TRIMP"""
    if not all([duration_minutes, avg_hr, max_hr, resting_hr]):
        print("Training Load calculation missing required data:", {
            'duration': duration_minutes, 'avg_hr': avg_hr,
            'max_hr': max_hr, 'resting_hr': resting_hr
        })
        return None
        
    hrr_ratio = (avg_hr - resting_hr) / (max_hr - resting_hr)
    intensity = 0.64 * math.exp(1.92 * hrr_ratio)
    return duration_minutes * avg_hr * intensity

def recommend_recovery_time(training_load, resting_hr, age):
    """Recommend recovery time based on training load and personal metrics"""
    if not all([training_load, resting_hr, age]):
        return None
        
    base_recovery = training_load * 0.2  # Hours
    age_factor = 1 + max(0, (age - 30) * 0.02)
    hr_factor = 1 + max(0, (resting_hr - 60) * 0.01)
    return base_recovery * age_factor * hr_factor

def predict_race_times(recent_paces, distances=[5, 10, 21.1, 42.2]):
    """Predict race times using Riegel formula"""
    if not recent_paces:
        return None
        
    best_pace = min(recent_paces)
    base_time = best_pace * 5  # Use 5k as base
    
    predictions = {}
    for distance in distances:
        # Riegel formula: T2 = T1 * (D2/D1)^1.06
        predicted_time = base_time * (distance/5) ** 1.06
        predictions[f"{distance}k"] = predicted_time
        
    return predictions

def calculate_vo2max(avg_hr, max_hr, avg_pace, user_age, gender):
    """Calculate estimated VO2max using heart rate and pace data"""
    if not avg_hr or not avg_pace or not user_age:
        return None
    
    # Use Firstbeat formula (simplified version)
    # VO2max = 15.3 × HRmax/HRrest
    hrr = max_hr / avg_hr  # Heart rate ratio
    pace_factor = 60 / avg_pace  # Convert pace to speed factor
    
    # Adjust for age and gender
    age_factor = 1 - (user_age - 20) * 0.01 if user_age > 20 else 1
    gender_factor = 1.0 if gender == 1 else 0.85  # Male=1, Female=0
    
    vo2max = 15.3 * hrr * pace_factor * age_factor * gender_factor
    return round(vo2max, 1) if vo2max > 20 else None  # Only return reasonable values

def calculate_training_load(duration_minutes, avg_hr, resting_hr, max_hr=None):
    """Calculate training load using TRIMP (Training Impulse)"""
    if not duration_minutes or not avg_hr or not resting_hr:
        return None
    
    if not max_hr:
        max_hr = 220  # Default max HR if not provided
    
    # Calculate heart rate reserve (HRR) percentage
    hrr_percent = (avg_hr - resting_hr) / (max_hr - resting_hr)
    
    # Use Banister TRIMP formula
    gender_factor = 1.92  # Male factor (use 1.67 for female)
    trimp = duration_minutes * hrr_percent * 0.64 * math.exp(gender_factor * hrr_percent)
    
    return round(trimp) if trimp > 0 else None

def calculate_recovery_time(training_load, fitness_level=None):
    """Estimate recovery time based on training load"""
    if not training_load:
        return None
    
    # Basic formula: higher training load = longer recovery
    if not fitness_level:
        fitness_level = 1.0  # Default average fitness
        
    # Higher fitness = faster recovery
    base_recovery = training_load * 0.2  # Each TRIMP unit = 0.2 hours recovery
    adjusted_recovery = base_recovery / fitness_level
    
    return round(adjusted_recovery * 10) / 10  # Round to 1 decimal place

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