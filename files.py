import os
import sys
import math
import xml.etree.ElementTree as ET
from typing import List, Dict, Tuple, Optional
import csv
from collections import deque

# =============================================================================
# Data Structures
# =============================================================================

class Segment:
    """Represents a transport segment (edge) between two stops.

    Attributes:
        from_stop: Origin stop name
        to_stop: Destination stop name
        duration: Travel time in minutes
        cost: Fare in HKD
    """

    def __init__(self, from_stop: str, to_stop: str, duration: int, cost: float, mode: str = 'Other'):
        self.from_stop = from_stop
        self.to_stop = to_stop
        self.duration = duration
        self.cost = cost
        self.mode_of_transport = mode

    def __repr__(self):
        return f"Segment({self.from_stop} -> {self.to_stop}, {self.duration}min, ${self.cost:.2f}, {self.mode_of_transport})"


class Journey:
    """Represents a complete journey through the network.

    Attributes:
        segments: List of Segment objects forming the journey
        total_duration: Total travel time in minutes
        total_cost: Total fare in HKD
    """

    def __init__(self, segments: List[Segment], fare_lookup: Dict[Tuple[str, str], float], origin: str, destination: str):
        self.segments = segments
        self.origin = origin
        self.destination = destination
        self.total_duration = sum(s.duration for s in segments)
        # Use direct fare if available, otherwise sum of segment costs
        direct_fare = fare_lookup.get((origin, destination))
        if direct_fare is not None:
            self.total_cost = direct_fare
        else:
            self.total_cost = sum(s.cost for s in segments)

    @property
    def num_segments(self) -> int:
        """Returns the number of segments in the journey."""
        return len(self.segments)

    def __repr__(self):
        return (f"Journey({self.num_segments} segments, "
                f"{self.total_duration}min, ${self.total_cost:.2f})")


class TransportNetwork:
    """Represents the transport network containing stops and segments.

    Attributes:
        stops: Dictionary of stop name -> list of outbound segments
        all_stops: Set of all stop names
        stop_coords: Dictionary of stop name -> (lat, lon) coordinates
    """

    def __init__(self):
        self.stops: Dict[str, List[Segment]] = {}
        self.all_stops: set = set()
        self.stop_coords: Dict[str, Tuple[float, float]] = {}  # stop_name -> (lat, lon)

    def add_segment(self, segment: Segment) -> None:
        """Adds a segment to the network.

        Args:
            segment: Segment object to add
        """
        # Add from stop and its outbound segment
        if segment.from_stop not in self.stops:
            self.stops[segment.from_stop] = []
        self.stops[segment.from_stop].append(segment)

        # Ensure both stops exist in all_stops
        self.all_stops.add(segment.from_stop)
        self.all_stops.add(segment.to_stop)

    def get_stops(self) -> List[str]:
        """Returns all stops sorted alphabetically."""
        return sorted(self.all_stops)

    def set_stop_coords(self, stop_name: str, lat: float, lon: float) -> None:
        """Sets the coordinates for a stop."""
        self.stop_coords[stop_name] = (lat, lon)

    def get_stop_coords(self, stop_name: str) -> Optional[Tuple[float, float]]:
        """Returns coordinates for a stop, or None if not available."""
        return self.stop_coords.get(stop_name)

    def get_outgoing_segments(self, stop: str) -> List[Segment]:
        """Returns all segments starting from the given stop."""
        return self.stops.get(stop, [])

    def get_num_segments(self) -> int:
        """Returns total number of segments in the network."""
        return sum(len(segments) for segments in self.stops.values())

    def get_average_stats(self) -> Tuple[float, float]:
        """Returns average duration and cost across all segments."""
        all_segments = []
        for segments in self.stops.values():
            all_segments.extend(segments)

        if not all_segments:
            return 0.0, 0.0

        avg_duration = sum(s.duration for s in all_segments) / len(all_segments)
        avg_cost = sum(s.cost for s in all_segments) / len(all_segments)

        return avg_duration, avg_cost

# =============================================================================
# File I/O Functions
# =============================================================================

def load_network_from_mtr() -> Tuple[TransportNetwork, Dict[Tuple[str, str], float], List[str]]:
    """Loads transport network from official MTR data files.

    Reads from:
    - mtr/mtr_lines_and_stations.csv: Station info and sequences
    - mtr/mtr_lines_fares.csv: Fare data between stations

    Returns:
        Tuple of (TransportNetwork object, fare_lookup dict, list of warning/error messages)
    """
    # csv imported at module level

    network = TransportNetwork()
    warnings = []

    # Files to try loading
    stations_file = 'data/mtr/mtr_lines_and_stations.csv'
    fares_file = 'data/mtr/mtr_lines_fares.csv'

    # Check if files exist
    if not os.path.exists(stations_file):
        return load_network('network.csv'), ["Warning: MTR data not found, falling back to network.csv"]

    # Build station sequences from lines data
    # Key: (line_code, direction), Value: list of (sequence, station_name)
    line_sequences = {}
    # Track which lines each station belongs to
    station_lines = {}  # station_name -> set of line codes

    try:
        with open(stations_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                line = row.get('Line Code', '').strip()
                direction = row.get('Direction', '').strip()
                english = row.get('English Name', '').strip()
                sequence = row.get('Sequence', '').strip()

                # Skip empty or special rows
                if not line or not english or not sequence:
                    continue

                # Skip LMC ( Lok Ma Chau) branch as it's covered by main EAL
                if 'LMC' in direction:
                    continue

                # Track station -> lines
                if english not in station_lines:
                    station_lines[english] = set()
                station_lines[english].add(line)

                key = (line, direction)
                if key not in line_sequences:
                    line_sequences[key] = []
                try:
                    line_sequences[key].append((int(float(sequence)), english))
                except ValueError:
                    pass
    except Exception as e:
        return load_network('data/network.csv'), [f"Warning: Could not read {stations_file}: {str(e)}"]

    # Build fare lookup from fares file
    # Key: (source, dest), Value: standard fare
    fare_lookup = {}
    try:
        with open(fares_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                src = row.get('SRC_STATION_NAME', '').strip()
                dest = row.get('DEST_STATION_NAME', '').strip()
                std_fare = row.get('OCT_STD_FARE', '').strip()

                if src and dest and std_fare:
                    try:
                        fare_lookup[(src, dest)] = float(std_fare)
                    except ValueError:
                        pass
    except Exception as e:
        warnings.append(f"Warning: Could not read fares file: {str(e)}")

    # Also load airport express fares
    airport_fares_file = 'data/airport_express_fares.csv'
    try:
        with open(airport_fares_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                src = row.get('ST_FROM', '').strip()
                dest = row.get('ST_TO', '').strip()
                fare = row.get('SINGLE_ADT_FARE', '').strip()

                if src and dest and fare:
                    try:
                        fare_lookup[(src, dest)] = float(fare)
                    except ValueError:
                        pass
    except Exception as e:
        warnings.append(f"Warning: Could not read airport fares: {str(e)}")

    # Load MTR station coordinates
    coords_file = 'data/mtr/mtr_station_coords.csv'
    loaded_coords = 0
    try:
        with open(coords_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                station = row.get('Station', '').strip()
                lat_str = row.get('Latitude', '').strip()
                lon_str = row.get('Longitude', '').strip()

                if station and lat_str and lon_str:
                    try:
                        lat = float(lat_str)
                        lon = float(lon_str)
                        network.set_stop_coords(station, lat, lon)
                        loaded_coords += 1
                    except ValueError:
                        pass
    except Exception as e:
        warnings.append(f"Warning: Could not read MTR coords: {str(e)}")

    # Typical duration between adjacent stations (in minutes)
    # Most MTR journeys are 2-4 minutes between stations
    TYPICAL_DURATION = 3

    # Special durations for Airport Express Line (AEL)
    ael_durations = {
        ('HongKong', 'Kowloon'): 5,
        ('Kowloon', 'Tsing Yi'): 7,
        ('Tsing Yi', 'Airport'): 12,
        ('Airport', 'AsiaWorld-Expo'): 3,
    }

    # Build segments from line sequences
    segments_added = 0

    for (line, direction), stations in line_sequences.items():
        # Sort by sequence
        stations_sorted = sorted(stations, key=lambda x: x[0])

        # Create segments between consecutive stations
        for i in range(len(stations_sorted) - 1):
            from_station = stations_sorted[i][1]
            to_station = stations_sorted[i + 1][1]

            # Get fare, default to 5.0 if not found
            fare = fare_lookup.get((from_station, to_station), 5.0)

            # Get duration
            if line == 'AEL':
                duration = ael_durations.get((from_station, to_station), ael_durations.get((to_station, from_station), TYPICAL_DURATION))
            else:
                duration = TYPICAL_DURATION

            # Add forward segment
            segment = Segment(from_station, to_station, duration, fare, mode='MTR')
            network.add_segment(segment)
            segments_added += 1

            # Add reverse segment (bidirectional)
            reverse_fare = fare_lookup.get((to_station, from_station), fare)
            reverse_duration = ael_durations.get((to_station, from_station), ael_durations.get((from_station, to_station), duration))
            reverse_segment = Segment(to_station, from_station, reverse_duration, reverse_fare, mode='MTR')
            network.add_segment(reverse_segment)
            segments_added += 1

    # Add interchange connections (stations that appear in multiple lines)
    # These are key interchange stations where passengers can change lines
    # We already have them from the line sequences, but let's ensure connectivity

    if segments_added == 0:
        fallback_network, fallback_warnings = load_network('data/network.csv')
        return fallback_network, {}, ["Warning: No segments created from MTR data, using data/network.csv"] + fallback_warnings + fallback_warnings

    warnings.append(f"Loaded {len(network.all_stops)} stops, {segments_added} segments, {loaded_coords} coordinates from MTR data")

    return network, fare_lookup, warnings


def load_network(filename: str) -> Tuple['TransportNetwork', Dict[Tuple[str, str], float], List[str]]:
    """Loads transport network from a CSV-format file.

    File format:
        from_stop,to_stop,duration,cost
        Central,Admiralty,15,10.5
        ...

    Args:
        filename: Path to the network file

    Returns:
        Tuple of (TransportNetwork object, list of warning/error messages)
    """
    from main import Segment, TransportNetwork
    
    network = TransportNetwork()
    warnings = []

    if not os.path.exists(filename):
        return network, {}, [f"Error: File '{filename}' not found."]

    if os.path.getsize(filename) == 0:
        return network, {}, [f"Error: File '{filename}' is empty."]

    try:
        with open(filename, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        return network, {}, [f"Error: Could not read file: {str(e)}"]

    if not lines:
        return network, {}, [f"Error: File '{filename}' is empty."]

    # Skip header if present
    start_idx = 0
    if lines[0].strip().lower().startswith('from_stop'):
        start_idx = 1

    valid_count = 0
    for line_num, line in enumerate(lines[start_idx:], start=start_idx + 1):
        line = line.strip()

        # Skip empty lines and comments
        if not line or line.startswith('#'):
            continue

        # Parse CSV line
        parts = [p.strip() for p in line.split(',')]

        if len(parts) != 4:
            warnings.append(f"Warning: Line {line_num}: Expected 4 fields, got {len(parts)}. Skipping.")
            continue

        from_stop, to_stop, duration_str, cost_str = parts

        # Validate stop names
        if not from_stop or not to_stop:
            warnings.append(f"Warning: Line {line_num}: Empty stop name. Skipping.")
            continue

        # Validate duration
        try:
            duration = int(duration_str)
            if duration <= 0:
                warnings.append(f"Warning: Line {line_num}: Duration must be positive. Skipping.")
                continue
        except ValueError:
            warnings.append(f"Warning: Line {line_num}: Invalid duration '{duration_str}'. Skipping.")
            continue

        # Validate cost
        try:
            cost = float(cost_str)
            if cost < 0:
                warnings.append(f"Warning: Line {line_num}: Cost cannot be negative. Skipping.")
                continue
        except ValueError:
            warnings.append(f"Warning: Line {line_num}: Invalid cost '{cost_str}'. Skipping.")
            continue

        # Add segment to network
        segment = Segment(from_stop, to_stop, duration, cost, mode='Other')
        network.add_segment(segment)
        valid_count += 1

    if valid_count == 0:
        warnings.append(f"Error: No valid segments found in file.")

    return network, {}, warnings


def load_network_from_light_rail() -> Tuple['TransportNetwork', Dict[Tuple[str, str], float], List[str]]:
    """Loads light rail network from CSV files.

    Reads from:
    - mtr/light_rail_routes_and_stops.csv: Route and stop sequences
    - mtr/light_rail_fares.csv: Fare data between stops

    Returns:
        Tuple of (TransportNetwork object, fare_lookup dict, list of warning/error messages)
    """
    from main import Segment, TransportNetwork
    
    # csv imported at module level

    network = TransportNetwork()
    warnings = []

    routes_file = 'data/mtr/light_rail_routes_and_stops.csv'
    fares_file = 'data/mtr/light_rail_fares.csv'

    if not os.path.exists(routes_file):
        return network, [f"Warning: {routes_file} not found"]

    # Build ID to name mapping
    id_to_name = {}
    line_sequences = {}

    try:
        with open(routes_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                line = row.get('Line Code', '').strip()
                direction = row.get('Direction', '').strip()
                stop_id = row.get('Stop ID', '').strip()
                english = row.get('English Name', '').strip()
                sequence = row.get('Sequence', '').strip()

                if not line or not english or not sequence or not stop_id:
                    continue

                id_to_name[stop_id] = english

                key = (line, direction)
                if key not in line_sequences:
                    line_sequences[key] = []
                try:
                    line_sequences[key].append((int(float(sequence)), stop_id))
                except ValueError:
                    pass
    except Exception as e:
        return network, [f"Warning: Could not read {routes_file}: {str(e)}"]

    # Build fare lookup
    fare_lookup = {}
    try:
        with open(fares_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                from_id = row.get('from_station_id', '').strip()
                to_id = row.get('to_station_id', '').strip()
                fare = row.get('fare_single_adult', '').strip()

                if from_id and to_id and fare:
                    try:
                        from_name = id_to_name.get(from_id)
                        to_name = id_to_name.get(to_id)
                        if from_name and to_name:
                            fare_lookup[(from_name, to_name)] = float(fare)
                    except ValueError:
                        pass
    except Exception as e:
        warnings.append(f"Warning: Could not read fares file: {str(e)}")

    # Typical duration for light rail (3-5 minutes between stops)
    TYPICAL_DURATION = 4

    segments_added = 0
    for (line, direction), stops in line_sequences.items():
        stops_sorted = sorted(stops, key=lambda x: x[0])
        for i in range(len(stops_sorted) - 1):
            from_id = stops_sorted[i][1]
            to_id = stops_sorted[i + 1][1]
            from_station = id_to_name[from_id]
            to_station = id_to_name[to_id]

            fare = fare_lookup.get((from_station, to_station), 5.0)

            # Add forward
            segment = Segment(from_station, to_station, TYPICAL_DURATION, fare, mode='Light Rail')
            network.add_segment(segment)
            segments_added += 1

            # Add reverse
            reverse_fare = fare_lookup.get((to_station, from_station), fare)
            reverse_segment = Segment(to_station, from_station, TYPICAL_DURATION, reverse_fare, mode='Light Rail')
            network.add_segment(reverse_segment)
            segments_added += 1

    warnings.append(f"Loaded light rail: {len(network.all_stops)} stops, {segments_added} segments")
    return network, fare_lookup, warnings


def load_network_from_bus() -> Tuple['TransportNetwork', Dict[Tuple[str, str], float], List[str]]:
    """Loads bus network from CSV files.

    Reads from:
    - mtr_bus_routes.csv: Route information
    - mtr_bus_stops.csv: Stop sequences per route
    - mtr_bus_fares.csv: Fare data per route

    Returns:
        Tuple of (TransportNetwork object, list of warning/error messages)
    """
    from main import Segment, TransportNetwork
    
    # csv imported at module level

    network = TransportNetwork()
    warnings = []

    routes_file = 'data/bus/ROUTE_BUS.xml'
    stops_file = 'data/bus/RSTOP_BUS.xml'
    coords_file = 'data/bus/STOP_BUS.xml'
    fares_file = 'data/bus/FARE_BUS.xml'

    if not os.path.exists(stops_file):
        return network, [f"Warning: {stops_file} not found"]

    # Load route information
    route_info = {}  # route_id -> journey_time
    try:
        tree = ET.parse(routes_file)
        root = tree.getroot()
        for route in root.findall('ROUTE'):
            route_id = route.find('ROUTE_ID').text
            journey_time = route.find('JOURNEY_TIME')
            if journey_time is not None and journey_time.text:
                route_info[route_id] = int(journey_time.text)
    except Exception as e:
        warnings.append(f"Warning: Could not read {routes_file}: {str(e)}")

    # Load stop sequences and names
    route_sequences = {}  # route_id -> list of (seq, stop_name, stop_id)
    stop_names = {}  # stop_id -> stop_name
    try:
        tree = ET.parse(stops_file)
        root = tree.getroot()
        for rstop in root.findall('RSTOP'):
            route_id = rstop.find('ROUTE_ID').text
            stop_seq = int(rstop.find('STOP_SEQ').text)
            stop_id = rstop.find('STOP_ID').text
            stop_name = rstop.find('STOP_NAMEE').text  # English name
            
            if route_id not in route_sequences:
                route_sequences[route_id] = []
            route_sequences[route_id].append((stop_seq, stop_name, stop_id))
            stop_names[stop_id] = stop_name
    except Exception as e:
        warnings.append(f"Warning: Could not read {stops_file}: {str(e)}")

    # Load stop coordinates
    stop_coords = {}  # stop_name -> (x, y)
    try:
        tree = ET.parse(coords_file)
        root = tree.getroot()
        for stop in root.findall('STOP'):
            stop_id = stop.find('STOP_ID').text
            x_elem = stop.find('X')
            y_elem = stop.find('Y')
            if x_elem is not None and y_elem is not None and x_elem.text and y_elem.text:
                x = float(x_elem.text)
                y = float(y_elem.text)
                stop_name = stop_names.get(stop_id)
                if stop_name:
                    stop_coords[stop_name] = (x, y)
    except Exception as e:
        warnings.append(f"Warning: Could not read {coords_file}: {str(e)}")

    # Typical duration for bus (5-10 minutes between stops)
    TYPICAL_DURATION = 7

    segments_added = 0
    for route_id, stops in route_sequences.items():
        stops_sorted = sorted(stops, key=lambda x: x[0])
        fare = 5.0  # Default fare since FARE_BUS.xml is too large

        for i in range(len(stops_sorted) - 1):
            from_station = stops_sorted[i][1]
            to_station = stops_sorted[i + 1][1]

            # For bus, use fixed fare per segment (simplified)
            segment = Segment(from_station, to_station, TYPICAL_DURATION, fare, mode='Bus')
            network.add_segment(segment)
            segments_added += 1

            # Add reverse (bidirectional)
            reverse_segment = Segment(to_station, from_station, TYPICAL_DURATION, fare, mode='Bus')
            network.add_segment(reverse_segment)
            segments_added += 1

    # Add walking segments between close bus stops (limited)
    walking_segments = 0
    max_walking_per_stop = 5  # Limit walking connections per stop
    walking_per_stop = {}
    for stop1, (x1, y1) in stop_coords.items():
        walking_per_stop[stop1] = 0

    for stop1, (x1, y1) in stop_coords.items():
        if walking_per_stop.get(stop1, 0) >= max_walking_per_stop:
            continue
        # Sort stops by distance and take closest
        distances = []
        for stop2, (x2, y2) in stop_coords.items():
            if stop1 != stop2:
                dist = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
                distances.append((dist, stop2, x2, y2))
        distances.sort()
        for dist, stop2, x2, y2 in distances[:max_walking_per_stop]:
            if dist < 300:  # within 300 units
                duration = max(1, int(dist / 84))
                network.add_segment(Segment(stop1, stop2, duration, 0.0, mode='Walk'))
                network.add_segment(Segment(stop2, stop1, duration, 0.0, mode='Walk'))
                walking_segments += 2
                walking_per_stop[stop1] = walking_per_stop.get(stop1, 0) + 1
                walking_per_stop[stop2] = walking_per_stop.get(stop2, 0) + 1

    # Add walking transfers between MTR/light rail stations and bus stops with similar names
    transfer_segments = 0
    major_stations = {'Central', 'Admiralty', 'Tsim Sha Tsui', 'Mong Kok', 'Prince Edward', 'Yau Ma Tei', 'Jordan', 'Sham Shui Po', 'Cheung Sha Wan', 'Lai Chi Kok', 'Mei Foo', 'Tsuen Wan', 'Kwai Fong', 'Kwai Hing', 'Tai Wo Hau'}
    for mtr_stop in network.all_stops:
        if mtr_stop in stop_coords:
            continue
        if mtr_stop not in major_stations:
            continue
        added = 0
        for bus_stop in stop_coords:
            if added >= 3:  # Limit to 3 transfers per station
                break
            if mtr_stop.lower() in bus_stop.lower():
                network.add_segment(Segment(mtr_stop, bus_stop, 5, 0.0, mode='Walk'))
                network.add_segment(Segment(bus_stop, mtr_stop, 5, 0.0, mode='Walk'))
                transfer_segments += 2
                added += 1

    # Store stop coordinates in the network
    for stop_name, (x, y) in stop_coords.items():
        network.set_stop_coords(stop_name, x, y)

    warnings.append(f"Loaded bus: {len([s for s in network.all_stops if s in stop_coords])} bus stops, {segments_added} bus segments, {walking_segments} walking segments, {transfer_segments} transfer segments")
    return network, {}, warnings


def load_network_from_airport_express() -> Tuple['TransportNetwork', List[str]]:
    """Loads airport express network from CSV file.

    Reads from:
    - airport_express_fares.csv: Direct fares between stations

    Returns:
        Tuple of (TransportNetwork object, list of warning/error messages)
    """
    from main import Segment, TransportNetwork
    
    # csv imported at module level

    network = TransportNetwork()
    warnings = []

    fares_file = 'airport_express_fares.csv'

    if not os.path.exists(fares_file):
        return network, [f"Warning: {fares_file} not found"]

    fare_lookup = {}
    stations = set()

    try:
        with open(fares_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                from_station = row.get('ST_FROM', '').strip()
                to_station = row.get('ST_TO', '').strip()
                fare = row.get('SINGLE_ADT_FARE', '').strip()

                if from_station and to_station and fare:
                    stations.add(from_station)
                    stations.add(to_station)
                    try:
                        fare_lookup[(from_station, to_station)] = float(fare)
                    except ValueError:
                        pass
    except Exception as e:
        return network, [f"Warning: Could not read {fares_file}: {str(e)}"]

    # Airport express stations: HongKong, Kowloon, Tsing Yi, Airport, AsiaWorld-Expo
    # Create segments between all pairs with fares
    # Typical duration: HongKong-Airport ~24 min, Kowloon-Airport ~20 min, etc.
    # But to make it competitive, use realistic fast times
    duration_lookup = {
        ('HongKong', 'Kowloon'): 5,
        ('HongKong', 'Tsing Yi'): 12,
        ('HongKong', 'Airport'): 24,
        ('HongKong', 'AsiaWorld-Expo'): 24,
        ('Kowloon', 'Tsing Yi'): 7,
        ('Kowloon', 'Airport'): 20,
        ('Kowloon', 'AsiaWorld-Expo'): 20,
        ('Tsing Yi', 'Airport'): 12,
        ('Tsing Yi', 'AsiaWorld-Expo'): 12,
        ('Airport', 'AsiaWorld-Expo'): 3,
    }

    segments_added = 0
    for from_station in stations:
        for to_station in stations:
            if from_station != to_station:
                fare = fare_lookup.get((from_station, to_station), 100.0)  # Default high fare
                duration = duration_lookup.get((from_station, to_station), duration_lookup.get((to_station, from_station), 10))
                segment = Segment(from_station, to_station, duration, fare, mode='Airport Express')
                network.add_segment(segment)
                segments_added += 1

    warnings.append(f"Loaded airport express: {len(network.all_stops)} stops, {segments_added} segments")
    return network, warnings


def load_network_all() -> Tuple['TransportNetwork', Dict[Tuple[str, str], float], List[str]]:
    """Loads complete transport network from all available data sources.

    Combines MTR, light rail, bus, and airport express networks.

    Returns:
        Tuple of (TransportNetwork object, fare_lookup dict, list of warning/error messages)
    """
    from main import TransportNetwork
    
    network = TransportNetwork()
    fare_lookup = {}
    all_warnings = []

    # Load each network and merge
    loaders = [
        ('mtr', load_network_from_mtr),
        ('light_rail', load_network_from_light_rail),
        ('bus', load_network_from_bus),
    ]

    for name, loader in loaders:
        try:
            sub_network, sub_fare_lookup, warnings = loader()
            all_warnings.extend(warnings)
            # Merge networks
            for stop, segments in sub_network.stops.items():
                for segment in segments:
                    network.add_segment(segment)
            # Merge fare lookups
            fare_lookup.update(sub_fare_lookup)
            # Merge coordinates
            for stop_name, coords in sub_network.stop_coords.items():
                if stop_name not in network.stop_coords:
                    network.set_stop_coords(stop_name, coords[0], coords[1])
        except Exception as e:
            all_warnings.append(f"Error loading {name}: {str(e)}")

    total_stops = len(network.all_stops)
    total_segments = network.get_num_segments()

    all_warnings.append(f"Total network: {total_stops} stops, {total_segments} segments")

    return network, fare_lookup, all_warnings
