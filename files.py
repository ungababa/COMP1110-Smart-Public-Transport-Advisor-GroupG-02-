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
    """Great-circle distance in metres between two lat/lon points. This is used to estimate segment durations when only stop coordinates are available. Used in the A* algorithm
    Source: https://en.wikipedia.org/wiki/Haversine_formula
    """
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
    """Load MTR lines, stations, fares, and coordinates."""
    network = TransportNetwork()
    fare_lookup = {}
    line_sequences = {}
    station_lines = {}

    try:
        with open('data/mtr/mtr_lines_and_stations.csv', 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                line = row.get('Line Code', '').strip()
                direction = row.get('Direction', '').strip()
                english = row.get('English Name', '').strip()
                sequence = row.get('Sequence', '').strip()
                if line and english and sequence and 'LMC' not in direction:
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
    except Exception:
        return network, {}, []

    try:
        with open('data/mtr/mtr_lines_fares.csv', 'r', encoding='utf-8-sig') as f:
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
    except Exception:
        pass

    try:
        with open('data/mtr/mtr_station_coords.csv', 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                station = row.get('Station', '').strip()
                lat_str = row.get('Latitude', '').strip()
                lon_str = row.get('Longitude', '').strip()
                if station and lat_str and lon_str:
                    try:
                        network.set_stop_coords(station, float(lat_str), float(lon_str))
                    except ValueError:
                        pass
    except Exception:
        pass

    TYPICAL_DURATION = 3
    ael_durations = {
        ('HongKong', 'Kowloon'): 5,
        ('Kowloon', 'Tsing Yi'): 7,
        ('Tsing Yi', 'Airport'): 12,
        ('Airport', 'AsiaWorld-Expo'): 3,
    }

    for (line, direction), stations in line_sequences.items():
        stations_sorted = sorted(stations, key=lambda x: x[0])
        for i in range(len(stations_sorted) - 1):
            from_station = stations_sorted[i][1]
            to_station = stations_sorted[i + 1][1]
            fare = fare_lookup.get((from_station, to_station), 5.0)
            duration = ael_durations.get((from_station, to_station), TYPICAL_DURATION) if line == 'AEL' else TYPICAL_DURATION
            
            network.add_segment(Segment(from_station, to_station, duration, fare, mode='MTR'))
            reverse_fare = fare_lookup.get((to_station, from_station), fare)
            reverse_duration = ael_durations.get((to_station, from_station), duration) if line == 'AEL' else TYPICAL_DURATION
            network.add_segment(Segment(to_station, from_station, reverse_duration, reverse_fare, mode='MTR'))

    return network, fare_lookup, []


def load_network(filename: str) -> Tuple[TransportNetwork, Dict[Tuple[str, str], float], List[str]]:
    """Load transport network from a simple CSV file."""
    network = TransportNetwork()
    
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception:
        return network, {}, []
    
    if not lines:
        return network, {}, []
    
    start_idx = 1 if lines[0].strip().lower().startswith('from_stop') else 0
    
    for line in lines[start_idx:]:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        try:
            parts = line.split(',')
            if len(parts) != 4:
                continue
            from_stop, to_stop, duration_str, cost_str = [p.strip() for p in parts]
            if not from_stop or not to_stop:
                continue
            duration = int(duration_str)
            cost = float(cost_str)
            if duration > 0 and cost >= 0:
                network.add_segment(Segment(from_stop, to_stop, duration, cost, mode='Other'))
        except (ValueError, IndexError):
            continue
    
    return network, {}, []





def load_network_from_bus() -> Tuple['TransportNetwork', Dict[Tuple[str, str], float], List[str]]:
    """Load bus network from XML files."""
    network = TransportNetwork()
    route_info = {}
    route_sequences = {}
    stop_names = {}
    stop_id_coords = {}
    stop_coords = {}

    try:
        tree = ET.parse('data/bus/ROUTE_BUS.xml')
        root = tree.getroot()
        for route in root.findall('ROUTE'):
            try:
                route_id = route.find('ROUTE_ID').text
                jt = route.find('JOURNEY_TIME')
                ff = route.find('FULL_FARE')
                route_info[route_id] = {
                    'journey_time': int(jt.text) if jt is not None and jt.text else None,
                    'full_fare': float(ff.text) if ff is not None and ff.text else 5.0
                }
            except (ValueError, AttributeError):
                pass
    except Exception:
        pass

    try:
        tree = ET.parse('data/bus/RSTOP_BUS.xml')
        root = tree.getroot()
        for rstop in root.findall('RSTOP'):
            try:
                route_id = rstop.find('ROUTE_ID').text
                route_seq = rstop.find('ROUTE_SEQ').text
                stop_seq = int(rstop.find('STOP_SEQ').text)
                stop_id = rstop.find('STOP_ID').text
                stop_name = rstop.find('STOP_NAMEE').text.strip()
                stop_names[stop_id] = stop_name
                key = (route_id, route_seq)
                if key not in route_sequences:
                    route_sequences[key] = []
                route_sequences[key].append((stop_seq, stop_name, stop_id))
            except (ValueError, AttributeError):
                pass
    except Exception:
        pass

    try:
        tree = ET.parse('data/bus/STOP_BUS.xml')
        root = tree.getroot()
        for stop in root.findall('STOP'):
            try:
                stop_id = stop.find('STOP_ID').text
                x_elem = stop.find('X')
                y_elem = stop.find('Y')
                if x_elem is not None and y_elem is not None and x_elem.text and y_elem.text:
                    lat = float(x_elem.text)
                    lon = float(y_elem.text)
                    stop_id_coords[stop_id] = (lat, lon)
                    name = stop_names.get(stop_id)
                    if name:
                        stop_coords[name] = (lat, lon)
            except (ValueError, AttributeError):
                pass
    except Exception:
        pass

    FALLBACK_DURATION = 3

    for (route_id, route_seq), stops in route_sequences.items():
        stops_sorted = sorted(stops, key=lambda x: x[0])
        info = route_info.get(route_id, {})
        fare = info.get('full_fare', 5.0)
        total_journey_time = info.get('journey_time')
        
        total_route_distance = 0.0
        segment_distances = []

        for i in range(len(stops_sorted) - 1):
            sid1 = stops_sorted[i][2]
            sid2 = stops_sorted[i + 1][2]
            c1 = stop_id_coords.get(sid1)
            c2 = stop_id_coords.get(sid2)
            dist = haversine_distance(c1[0], c1[1], c2[0], c2[1]) if c1 and c2 else None
            segment_distances.append(dist)
            if dist is not None:
                total_route_distance += dist

        for i in range(len(stops_sorted) - 1):
            from_station = stops_sorted[i][1]
            to_station = stops_sorted[i + 1][1]
            dist = segment_distances[i]

            if dist and total_route_distance > 0 and total_journey_time and total_journey_time > 0:
                duration = max(1, round(dist * total_journey_time / total_route_distance))
            else:
                duration = FALLBACK_DURATION

            network.add_segment(Segment(from_station, to_station, duration, fare, mode='Bus'))
            network.add_segment(Segment(to_station, from_station, duration, fare, mode='Bus'))

    for stop_name, (lat, lon) in stop_coords.items():
        network.set_stop_coords(stop_name, lat, lon)

    return network, {}, []


def load_network_all() -> Tuple[TransportNetwork, Dict[Tuple[str, str], float], List[str]]:
    """Load complete transport network from all available sources."""
    network = TransportNetwork()
    fare_lookup = {}

    loaders = [
        load_network_from_mtr,
        load_network_from_bus,
    ]

    for loader in loaders:
        try:
            sub_network, sub_fare_lookup, _ = loader()
            for stop, segments in sub_network.stops.items():
                for segment in segments:
                    network.add_segment(segment)
            fare_lookup.update(sub_fare_lookup)
            for stop_name, coords in sub_network.stop_coords.items():
                if stop_name not in network.stop_coords:
                    network.set_stop_coords(stop_name, coords[0], coords[1])
        except Exception:
            pass

    return network, fare_lookup, []