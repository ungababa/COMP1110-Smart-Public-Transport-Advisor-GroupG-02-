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
    """Represents a transport segment (edge) between two stops."""

    def __init__(self, from_stop: str, to_stop: str, duration: int, cost: float, mode: str = 'Other'):
        self.from_stop = from_stop
        self.to_stop = to_stop
        self.duration = duration
        self.cost = cost
        self.mode_of_transport = mode

    def __repr__(self):
        return f"Segment({self.from_stop} -> {self.to_stop}, {self.duration}min, ${self.cost:.2f}, {self.mode_of_transport})"


class Journey:
    """Represents a complete journey through the network."""

    def __init__(self, segments: List[Segment], fare_lookup: Dict[Tuple[str, str], float], origin: str, destination: str):
        self.segments = segments
        self.origin = origin
        self.destination = destination
        self.total_duration = sum(s.duration for s in segments)
        direct_fare = fare_lookup.get((origin, destination))
        if direct_fare is not None:
            self.total_cost = direct_fare
        else:
            self.total_cost = sum(s.cost for s in segments)

    @property
    def num_segments(self) -> int:
        return len(self.segments)

    def __repr__(self):
        return (f"Journey({self.num_segments} segments, "
                f"{self.total_duration}min, ${self.total_cost:.2f})")


class TransportNetwork:
    """Represents the transport network containing stops and segments."""

    def __init__(self):
        self.stops: Dict[str, List[Segment]] = {}
        self.all_stops: set = set()
        self.stop_coords: Dict[str, Tuple[float, float]] = {}

    def add_segment(self, segment: Segment) -> None:
        if segment.from_stop not in self.stops:
            self.stops[segment.from_stop] = []
        self.stops[segment.from_stop].append(segment)
        self.all_stops.add(segment.from_stop)
        self.all_stops.add(segment.to_stop)

    def get_stops(self) -> List[str]:
        return sorted(self.all_stops)

    def set_stop_coords(self, stop_name: str, lat: float, lon: float) -> None:
        self.stop_coords[stop_name] = (lat, lon)

    def get_stop_coords(self, stop_name: str) -> Optional[Tuple[float, float]]:
        return self.stop_coords.get(stop_name)

    def get_outgoing_segments(self, stop: str) -> List[Segment]:
        return self.stops.get(stop, [])

    def get_num_segments(self) -> int:
        return sum(len(segments) for segments in self.stops.values())

    def get_average_stats(self) -> Tuple[float, float]:
        all_segments = []
        for segments in self.stops.values():
            all_segments.extend(segments)
        if not all_segments:
            return 0.0, 0.0
        avg_duration = sum(s.duration for s in all_segments) / len(all_segments)
        avg_cost = sum(s.cost for s in all_segments) / len(all_segments)
        return avg_duration, avg_cost


# =============================================================================
# Helper
# =============================================================================

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in metres between two lat/lon points."""
    R = 6371000
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
         * math.sin(dlon / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# =============================================================================
# File I/O Functions
# =============================================================================

def load_network_from_mtr() -> Tuple[TransportNetwork, Dict[Tuple[str, str], float], List[str]]:
    network = TransportNetwork()
    warnings = []

    stations_file = 'data/mtr/mtr_lines_and_stations.csv'
    fares_file = 'data/mtr/mtr_lines_fares.csv'

    if not os.path.exists(stations_file):
        return load_network('data/network.csv')[0], {}, ["Warning: MTR data not found, falling back to network.csv"]

    line_sequences = {}
    station_lines = {}

    try:
        with open(stations_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                line = row.get('Line Code', '').strip()
                direction = row.get('Direction', '').strip()
                english = row.get('English Name', '').strip()
                sequence = row.get('Sequence', '').strip()
                if not line or not english or not sequence:
                    continue
                if 'LMC' in direction:
                    continue
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
        return load_network('data/network.csv')[0], {}, [f"Warning: Could not read {stations_file}: {str(e)}"]

    fare_lookup = {}
    try:
        with open(fares_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                src = row.get('SRC_STATION_NAME', '').strip()
                dest = row.get('DEST_STATION_NAME', '').strip()
                std_fare = row.get('OCT_ADT_FARE', '').strip()
                if src and dest and std_fare:
                    try:
                        fare_lookup[(src, dest)] = float(std_fare)
                    except ValueError:
                        pass
    except Exception as e:
        warnings.append(f"Warning: Could not read fares file: {str(e)}")

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
    ael_durations = {
        ('HongKong', 'Kowloon'): 5,
        ('Kowloon', 'Tsing Yi'): 7,
        ('Tsing Yi', 'Airport'): 12,
        ('Airport', 'AsiaWorld-Expo'): 3,
    }

    segments_added = 0
    for (line, direction), stations in line_sequences.items():
        stations_sorted = sorted(stations, key=lambda x: x[0])
        for i in range(len(stations_sorted) - 1):
            from_station = stations_sorted[i][1]
            to_station = stations_sorted[i + 1][1]
            fare = fare_lookup.get((from_station, to_station), 5.0)
            if line == 'AEL':
                duration = ael_durations.get((from_station, to_station),
                           ael_durations.get((to_station, from_station), TYPICAL_DURATION))
            else:
                duration = TYPICAL_DURATION
            network.add_segment(Segment(from_station, to_station, duration, fare, mode='MTR'))
            segments_added += 1
            reverse_fare = fare_lookup.get((to_station, from_station), fare)
            reverse_duration = ael_durations.get((to_station, from_station),
                               ael_durations.get((from_station, to_station), duration))
            network.add_segment(Segment(to_station, from_station, reverse_duration, reverse_fare, mode='MTR'))
            segments_added += 1

    if segments_added == 0:
        net, _, fw = load_network('data/network.csv')
        return net, {}, ["Warning: No segments created from MTR data, using data/network.csv"] + fw

    warnings.append(f"Loaded {len(network.all_stops)} stops and {segments_added} segments from MTR data")

    return network, fare_lookup, warnings


def load_network(filename: str) -> Tuple[TransportNetwork, Dict[Tuple[str, str], float], List[str]]:
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

    start_idx = 1 if lines[0].strip().lower().startswith('from_stop') else 0
    valid_count = 0

    for line_num, line in enumerate(lines[start_idx:], start=start_idx + 1):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        parts = [p.strip() for p in line.split(',')]
        if len(parts) != 4:
            warnings.append(f"Warning: Line {line_num}: Expected 4 fields, got {len(parts)}. Skipping.")
            continue
        from_stop, to_stop, duration_str, cost_str = parts
        if not from_stop or not to_stop:
            warnings.append(f"Warning: Line {line_num}: Empty stop name. Skipping.")
            continue
        try:
            duration = int(duration_str)
            if duration <= 0:
                warnings.append(f"Warning: Line {line_num}: Duration must be positive. Skipping.")
                continue
        except ValueError:
            warnings.append(f"Warning: Line {line_num}: Invalid duration '{duration_str}'. Skipping.")
            continue
        try:
            cost = float(cost_str)
            if cost < 0:
                warnings.append(f"Warning: Line {line_num}: Cost cannot be negative. Skipping.")
                continue
        except ValueError:
            warnings.append(f"Warning: Line {line_num}: Invalid cost '{cost_str}'. Skipping.")
            continue
        network.add_segment(Segment(from_stop, to_stop, duration, cost, mode='Other'))
        valid_count += 1

    if valid_count == 0:
        warnings.append("Error: No valid segments found in file.")

    return network, {}, warnings


def load_network_from_light_rail() -> Tuple[TransportNetwork, Dict[Tuple[str, str], float], List[str]]:
    network = TransportNetwork()
    warnings = []

    routes_file = 'data/mtr/light_rail_routes_and_stops.csv'
    fares_file = 'data/mtr/light_rail_fares.csv'

    if not os.path.exists(routes_file):
        return network, {}, [f"Warning: {routes_file} not found"]

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
        return network, {}, [f"Warning: Could not read {routes_file}: {str(e)}"]

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
            network.add_segment(Segment(from_station, to_station, TYPICAL_DURATION, fare, mode='Light Rail'))
            segments_added += 1
            reverse_fare = fare_lookup.get((to_station, from_station), fare)
            network.add_segment(Segment(to_station, from_station, TYPICAL_DURATION, reverse_fare, mode='Light Rail'))
            segments_added += 1

    warnings.append(f"Loaded light rail: {len(network.all_stops)} stops, {segments_added} segments")
    return network, fare_lookup, warnings


def load_network_from_bus() -> Tuple['TransportNetwork', Dict[Tuple[str, str], float], List[str]]:
    network = TransportNetwork()
    warnings = []

    routes_file = 'data/bus/ROUTE_BUS.xml'
    stops_file = 'data/bus/RSTOP_BUS.xml'
    coords_file = 'data/bus/STOP_BUS.xml'

    if not os.path.exists(stops_file):
        return network, {}, [f"Warning: {stops_file} not found"]

    # Load route info: journey_time and full_fare keyed by route_id
    route_info = {}
    try:
        tree = ET.parse(routes_file)
        root = tree.getroot()
        for route in root.findall('ROUTE'):
            route_id = route.find('ROUTE_ID').text
            jt = route.find('JOURNEY_TIME')
            ff = route.find('FULL_FARE')
            route_info[route_id] = {
                'journey_time': int(jt.text) if jt is not None and jt.text else None,
                'full_fare': float(ff.text) if ff is not None and ff.text else 5.0
            }
    except Exception as e:
        warnings.append(f"Warning: Could not read {routes_file}: {str(e)}")

    # Load stop sequences grouped by (route_id, route_seq/direction)
    # CRITICAL: must group by ROUTE_SEQ too, otherwise both directions
    # get mixed into one sequence, doubling total distance and breaking durations
    route_sequences = {}  # (route_id, route_seq) -> list of (stop_seq, stop_name, stop_id)
    stop_names = {}       # stop_id -> stop_name
    try:
        tree = ET.parse(stops_file)
        root = tree.getroot()
        for rstop in root.findall('RSTOP'):
            route_id = rstop.find('ROUTE_ID').text
            route_seq = rstop.find('ROUTE_SEQ').text   # direction (1 or 2)
            stop_seq = int(rstop.find('STOP_SEQ').text)
            stop_id = rstop.find('STOP_ID').text
            stop_name = rstop.find('STOP_NAMEE').text.strip()
            stop_names[stop_id] = stop_name
            key = (route_id, route_seq)
            if key not in route_sequences:
                route_sequences[key] = []
            route_sequences[key].append((stop_seq, stop_name, stop_id))
    except Exception as e:
        warnings.append(f"Warning: Could not read {stops_file}: {str(e)}")

    # Load stop coordinates keyed by stop_id (NOT name — multiple stops share names)
    stop_id_coords = {}  # stop_id -> (lat, lon)
    stop_coords = {}     # stop_name -> (lat, lon) for network.set_stop_coords
    try:
        tree = ET.parse(coords_file)
        root = tree.getroot()
        for stop in root.findall('STOP'):
            stop_id = stop.find('STOP_ID').text
            x_elem = stop.find('X')
            y_elem = stop.find('Y')
            if x_elem is not None and y_elem is not None and x_elem.text and y_elem.text:
                lat = float(x_elem.text)  # X = latitude
                lon = float(y_elem.text)  # Y = longitude
                stop_id_coords[stop_id] = (lat, lon)
                name = stop_names.get(stop_id)
                if name:
                    stop_coords[name] = (lat, lon)
    except Exception as e:
        warnings.append(f"Warning: Could not read {coords_file}: {str(e)}")

    FALLBACK_DURATION = 3  # only used when coords are genuinely missing

    segments_added = 0

    for (route_id, route_seq), stops in route_sequences.items():
        stops_sorted = sorted(stops, key=lambda x: x[0])
        info = route_info.get(route_id, {})
        fare = info.get('full_fare', 5.0)
        total_journey_time = info.get('journey_time', None)

        # Pass 1: compute segment distances using stop_id coords (haversine)
        total_route_distance = 0.0
        segment_distances = []

        for i in range(len(stops_sorted) - 1):
            sid1 = stops_sorted[i][2]
            sid2 = stops_sorted[i + 1][2]
            c1 = stop_id_coords.get(sid1)
            c2 = stop_id_coords.get(sid2)

            if c1 and c2:
                dist = haversine_distance(c1[0], c1[1], c2[0], c2[1])
            else:
                dist = None

            segment_distances.append(dist)
            if dist is not None:
                total_route_distance += dist

        # Pass 2: build segments with duration proportional to distance
        for i in range(len(stops_sorted) - 1):
            from_station = stops_sorted[i][1]
            to_station = stops_sorted[i + 1][1]
            dist = segment_distances[i]

            if (dist is not None and
                    total_route_distance > 0 and
                    total_journey_time is not None and
                    total_journey_time > 0):
                duration = max(1, round(dist * total_journey_time / total_route_distance))
            else:
                duration = FALLBACK_DURATION

            segment = Segment(from_station, to_station, duration, fare, mode='Bus')
            network.add_segment(segment)
            segments_added += 1

            reverse_segment = Segment(to_station, from_station, duration, fare, mode='Bus')
            network.add_segment(reverse_segment)
            segments_added += 1

    # Store coords in network for A* heuristic
    for stop_name, (lat, lon) in stop_coords.items():
        network.set_stop_coords(stop_name, lat, lon)

    warnings.append(
        f"Loaded bus: {len(stop_coords)} bus stops, {segments_added} bus segments"
    )
    return network, {}, warnings


def load_network_from_airport_express() -> Tuple[TransportNetwork, Dict[Tuple[str, str], float], List[str]]:
    network = TransportNetwork()
    warnings = []

    fares_file = 'data/airport_express_fares.csv'
    if not os.path.exists(fares_file):
        return network, {}, [f"Warning: {fares_file} not found"]

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
        return network, {}, [f"Warning: Could not read {fares_file}: {str(e)}"]

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
                fare = fare_lookup.get((from_station, to_station), 100.0)
                duration = duration_lookup.get((from_station, to_station),
                           duration_lookup.get((to_station, from_station), 10))
                network.add_segment(Segment(from_station, to_station, duration, fare, mode='Airport Express'))
                segments_added += 1

    warnings.append(f"Loaded airport express: {len(network.all_stops)} stops, {segments_added} segments")
    return network, fare_lookup, warnings


def load_network_all() -> Tuple[TransportNetwork, Dict[Tuple[str, str], float], List[str]]:
    """Loads complete transport network from all available data sources."""
    network = TransportNetwork()
    fare_lookup = {}
    all_warnings = []

    loaders = [
        ('mtr', load_network_from_mtr),
        ('light_rail', load_network_from_light_rail),
        ('bus', load_network_from_bus),
    ]

    for name, loader in loaders:
        try:
            sub_network, sub_fare_lookup, warnings = loader()
            all_warnings.extend(warnings)
            for stop, segments in sub_network.stops.items():
                for segment in segments:
                    network.add_segment(segment)
            fare_lookup.update(sub_fare_lookup)
            # Merge coordinates for A* heuristic
            for stop_name, coords in sub_network.stop_coords.items():
                if stop_name not in network.stop_coords:
                    network.set_stop_coords(stop_name, coords[0], coords[1])
        except Exception as e:
            all_warnings.append(f"Error loading {name}: {str(e)}")

    all_warnings.append(f"Total network: {len(network.all_stops)} stops, {network.get_num_segments()} segments")
    return network, fare_lookup, all_warnings