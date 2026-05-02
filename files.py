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

    def __init__(self, from_stop: str, to_stop: str, duration: int, cost: float, mode: str = 'Other', route_id: Optional[str] = None, route_name: Optional[str] = None, operator: Optional[str] = None):
        self.from_stop = from_stop
        self.to_stop = to_stop
        self.duration = duration
        self.cost = cost
        self.mode_of_transport = mode
        self.route_id = route_id
        self.route_name = route_name  # Bus number/name (e.g., "1", "102P")
        self.operator = operator      # Bus operator (e.g., "KMB", "CTB")

    def __repr__(self):
        return f"Segment({self.from_stop} -> {self.to_stop}, {self.duration}min, ${self.cost:.2f}, {self.mode_of_transport})"


class Journey:
    """Represents a complete journey through the network."""

    def __init__(self, segments: List[Segment], fare_lookup: Dict[Tuple[str, str], float], origin: str, destination: str):
        self.segments = segments
        self.origin = origin
        self.destination = destination
        
        # Group segments into legs (consecutive segments with same route_id and mode)
        legs = self._group_segments(segments)
        num_transfers = max(0, len(legs) - 1)
        buffer_time = num_transfers * 5  # 5 minutes per transfer
        
        self.total_duration = sum(s.duration for s in segments) + buffer_time
        
        direct_fare = fare_lookup.get((origin, destination))
        if direct_fare is not None:
            self.total_cost = direct_fare
        else:
            self.total_cost = self._calculate_cost_with_consolidation(segments)

    def _group_segments(self, segments):
        """Group consecutive segments that share the same route_id + mode into legs.

        Returns list of lists, where each inner list is one continuous leg.
        Segments with no route_id (e.g. Walk) are never merged.
        """
        if not segments:
            return []
        groups = []
        current = [segments[0]]
        for seg in segments[1:]:
            prev = current[-1]
            same_route = (
                seg.route_id is not None
                and seg.route_id == prev.route_id
                and seg.mode_of_transport == prev.mode_of_transport
            )
            if same_route:
                current.append(seg)
            else:
                groups.append(current)
                current = [seg]
        groups.append(current)
        return groups

    def _calculate_cost_with_consolidation(self, segments: List[Segment]) -> float:
        """Calculate cost, treating consecutive segments from the same route/line as one journey.
        
        Works for all transport modes: Bus, MTR, Light Rail, Airport Express, etc.
        If a transport has the same route_id for consecutive segments, charges once.
        """
        if not segments:
            return 0.0
        
        total_cost = 0.0
        i = 0
        
        while i < len(segments):
            current_segment = segments[i]
            
            # Check if this segment has a route_id (applies to all transport modes)
            if current_segment.route_id:
                # Add the fare for this route once
                total_cost += current_segment.cost
                route_id = current_segment.route_id
                mode = current_segment.mode_of_transport
                
                # Skip all consecutive segments from the same route and mode
                while i + 1 < len(segments) and segments[i + 1].route_id == route_id and segments[i + 1].mode_of_transport == mode:
                    i += 1
            else:
                # For segments without route_id, add the cost normally
                total_cost += current_segment.cost
            
            i += 1
        
        return total_cost

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
        self._alias_parent: Dict[str, str] = {}
        self._alias_groups: Dict[str, set] = {}

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

    def get_canonical_stop(self, stop_name: str) -> str:
        """Return the canonical representative for an equivalent stop group."""
        if stop_name not in self._alias_parent:
            return stop_name
        # Path compression
        root = stop_name
        while self._alias_parent.get(root, root) != root:
            root = self._alias_parent[root]
        while stop_name != root:
            parent = self._alias_parent[stop_name]
            self._alias_parent[stop_name] = root
            stop_name = parent
        return root

    def add_alias(self, stop_a: str, stop_b: str) -> None:
        """Declare stop_a and stop_b as equivalent nodes in the network."""
        root_a = self.get_canonical_stop(stop_a)
        root_b = self.get_canonical_stop(stop_b)
        if root_a == root_b:
            return

        if root_a not in self._alias_parent:
            self._alias_parent[root_a] = root_a
            self._alias_groups[root_a] = {root_a}
        if root_b not in self._alias_parent:
            self._alias_parent[root_b] = root_b
            self._alias_groups[root_b] = {root_b}

        # Union root_b into root_a
        self._alias_parent[root_b] = root_a
        group_b = self._alias_groups.pop(root_b, {root_b})
        self._alias_groups.setdefault(root_a, {root_a}).update(group_b)
        for member in group_b:
            self._alias_parent[member] = root_a

    def get_equivalent_stops(self, stop_name: str) -> List[str]:
        root = self.get_canonical_stop(stop_name)
        return list(self._alias_groups.get(root, {root}))

    def get_stop_coords(self, stop_name: str) -> Optional[Tuple[float, float]]:
        coords = self.stop_coords.get(stop_name)
        if coords is not None:
            return coords
        for equivalent in self.get_equivalent_stops(stop_name):
            coords = self.stop_coords.get(equivalent)
            if coords is not None:
                return coords
        return None

    def get_outgoing_segments(self, stop: str) -> List[Segment]:
        canonical = self.get_canonical_stop(stop)
        segments = list(self.stops.get(canonical, []))
        for equivalent in self.get_equivalent_stops(canonical):
            if equivalent != canonical:
                segments.extend(self.stops.get(equivalent, []))
        return segments

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


MTR_NEAREST_BUS_STOP: Dict[str, str] = {
    "Admiralty": "ADMIRALTY CENTRE",
    "Airport": "Airport (Terminal One)",
    "AsiaWorld-Expo": "Regal Airport Hotel - Cheong Tat Road",
    "Causeway Bay": "Causeway Bay - Hysan Place - Hennessy Road",
    "Central": "Pedder Street",
    "Chai Wan": "Chai Wan Station",
    "Che Kung Temple": "HILTON CENTRE",
    "Cheung Sha Wan": "UN CHAU ESTATE",
    "Choi Hung": "Tan Fung House Choi Hung Estate - Lung Cheung Road",
    "City One": "CITY ONE SHA TIN BUS TERMINUS",
    "Diamond Hill": "DIAMOND HILL STATION BUS TERMINUS",
    "Fanling": "Fanling Station - Exit A2 - Fanling Station Road",
    "Fo Tan": "FO TAN STATION",
    "Fortress Hill": "Fortress Hill Station - King's Road",
    "HKU": "Chiu Sheung School Hong Kong - Pok Fu Lam Road",
    "Hang Hau": "HANG HAU STATION",
    "Hau Wan": "YIU TUNG ESTATE - Yiu Tung Estate",
    "Heng Fa Chuen": "HKIVE (Chai Wan) - Shun Tai Road",
    "Heng On": "YAN ON ESTATE",
    "Hin Keng": "HIN HING HOUSE HIN KENG ESTATE",
    "Ho Man Tin": "FAT KWONG STREET",
    "Hong Kong": "IFC Mall - Man Cheung Street",
    "Hung Hom": "HUNG HOM STATION BUS TERMINUS",
    "Jordan": "BOWRING STREET - PRUDENTIAL CENTRE",
    "Kai Tak": "Kai Tak - Airside",
    "Kam Sheung Road": "KAM SHEUNG ROAD STATION CAR PARK",
    "Kennedy Town": "Kennedy Town Station - Forbes Street",
    "Kowloon Bay": "TELFORD GARDENS",
    "Kowloon City": "PRINCE EDWARD ROAD WEST - Junction Road",
    "Kowloon Tong": "FESTIVAL WALK",
    "Kwai Fong": "KWAI FONG STATION",
    "Kwai Hing": "KWAI HING STATION BUS TERMINUS",
    "Kwong Tong": "SHUN LEE FIRE STATION",
    "Kwun Tong": "TUNG YAN STREET - Hip Wo Street",
    "LOHAS Park": "LOHAS Park",
    "Lai Chi Kok": "CHEUNG SHA WAN BUS TERMINUS",
    "Lai King": "LAI KING STATION",
    "Lam Tin": "LAM TIN STATION (ALIGHTING STOP)",
    "Lei Tung": "Hong Kong True Light College - Lei Tung Estate Road",
    "Lo Wu": "LO WU STATION ROAD",
    "Lok Fu": "LOK HIM HOUSE",
    "Lok Ma Chau": "HA WAN TSUEN",
    "Long Ping": "Yuen Long Town Hall (LR Fung Nin Road Stop)",
    "Ma On Shan": "SUNSHINE CITY",
    "Mei Foo": "MEI FOO BUS TERMINUS",
    "Mong Kok": "MONG KOK STATION - ARGYLE CENTRE",
    "Mong Kok East": "MONG KOK EAST STATION - MOKO",
    "Ngau Tau Kok": "Ngau Tau Kok Station - Kwun Tong Road",
    "North Point": "SHU KUK STREET",
    "Ocean Park": "Ocean Park",
    "Pat Heung": "NGAU KENG",
    "Po Lam": "LEUNG KIT WAH PRIMARY SCHOOL",
    "Prince Edward": "MONGKOK POLICE STATION",
    "Quarry Bay": "North Point Government Primary School - King's Road",
    "Racecourse": "HILTON CENTRE",
    "Sai Ying Pun": "Centre Street - Queen's Road West",
    "Sha Tin": "SHA TIN CENTRAL",
    "Sha Tin Wai": "Lek Yuen Estate - Yuen Wo Road",
    "Sham Shui Po": "Pei Ho Street - Cheung Sha Wan Road",
    "Shau Kei Wan": "Perfect Mount Gardens - Tung Hei Road",
    "Shek Kong": "CHUN YIU",
    "Shek Mun": "SHATIN HOSPITAL",
    "Sheung Shui": "SHEUNG SHUI BBI - SHEUNG SHUI STATION",
    "Sheung Wan": "CLEVERLY STREET",
    "Siu Hong": "BRILLIANT GARDEN",
    "Siu Sai Wan": "Kailey Industrial Centre - Sheung On Street",
    "South Horizons": "South Horizons",
    "Sung Wong Toi": "Kai Tak Sports Park - Sung Wong Toi Road",
    "Tai Koo": "Kornhill Plaza - King's Road",
    "Tai Po Market": "TAI PO MARKET STATION BUS TERMINUS",
    "Tai Shui Hang": "HANG TAI ROAD",
    "Tai Wai": "TAI WAI BBI - CHIK WAN STREET",
    "Tai Wo": "TAI PO GOVERNMENT OFFICE BUILDING - Ting Kok Road",
    "Tai Wo Hau": "HO PUI VILLAGE KWOK SHUI ROAD",
    "Tin Hau": "Queen's College - Tung Lo Wan Road",
    "Tin Shui Wai": "Tin Shui Wai Police Station",
    "Tiu Keng Leng": "Tiu Keng Leng Station - King Ling Road",
    "To Kwa Wan": "Tin Kwong Road - Ma Tau Wai Road",
    "Tseung Kwan O": "Tseung Kwan O Station - Po Yap Road",
    "Tsim Sha Tsui": "TSIM SHA TSUI BBI - HAIPHONG ROAD",
    "Tsing Yi": "Tsing Yi Station (General Loading/Unloading Bay)",
    "Tsuen Wan": "MTR TSUEN WAN STATION",
    "Tuen Mun": "MTR Tuen Mun Station",
    "University": "UNIVERSITY STATION",
    "Wan Chai": "Fleming Road - Hennessy Road",
    "Whampoa": "WHAMPOA GARDEN BUS TERMINUS",
    "Wong Chuk Hang": "Wong Chuk Hang Station",
    "Wong Tai Sin": "WONG TAI SIN BBI - WONG TAI SIN TEMPLE",
    "Wu Kai Sha": "Wu Kai Sha Station - WU KAI SHA STATION",
    "Yau Ma Tei": "Man Ming Lane - Nathan Road",
    "Yau Tong": "Eastern Harbour Crossing Bus-Bus Interchange",
    "Yuen Long": "YOHO MALL I",
}


def get_nearest_bus_stop_for_mtr_station(station: str) -> Optional[str]:
    """Return the nearest bus stop for a given MTR station."""
    return MTR_NEAREST_BUS_STOP.get(station)


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
        route_id = f"{line}_{direction}"  # Create unique route identifier
        for i in range(len(stations_sorted) - 1):
            from_station = stations_sorted[i][1]
            to_station = stations_sorted[i + 1][1]
            fare = fare_lookup.get((from_station, to_station), 5.0)
            if line == 'AEL':
                duration = ael_durations.get((from_station, to_station),
                           ael_durations.get((to_station, from_station), TYPICAL_DURATION))
            else:
                duration = TYPICAL_DURATION
            network.add_segment(Segment(from_station, to_station, duration, fare, mode='MTR', route_id=route_id))
            segments_added += 1
            reverse_fare = fare_lookup.get((to_station, from_station), fare)
            reverse_duration = ael_durations.get((to_station, from_station),
                               ael_durations.get((from_station, to_station), duration))
            network.add_segment(Segment(to_station, from_station, reverse_duration, reverse_fare, mode='MTR', route_id=route_id))
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
        route_id = f"{line}_{direction}"  # Create unique route identifier
        for i in range(len(stops_sorted) - 1):
            from_id = stops_sorted[i][1]
            to_id = stops_sorted[i + 1][1]
            from_station = id_to_name[from_id]
            to_station = id_to_name[to_id]
            fare = fare_lookup.get((from_station, to_station), 5.0)
            network.add_segment(Segment(from_station, to_station, TYPICAL_DURATION, fare, mode='Light Rail', route_id=route_id))
            segments_added += 1
            reverse_fare = fare_lookup.get((to_station, from_station), fare)
            network.add_segment(Segment(to_station, from_station, TYPICAL_DURATION, reverse_fare, mode='Light Rail', route_id=route_id))
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
            rn = route.find('ROUTE_NAMEE')
            cc = route.find('COMPANY_CODE')
            route_info[route_id] = {
                'journey_time': int(jt.text) if jt is not None and jt.text else None,
                'full_fare': float(ff.text) if ff is not None and ff.text else 5.0,
                'route_name': rn.text if rn is not None and rn.text else 'Unknown',
                'operator': cc.text if cc is not None and cc.text else 'Unknown'
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

            route_name = info.get('route_name', 'Unknown')
            operator = info.get('operator', 'Unknown')

            segment = Segment(from_station, to_station, duration, fare, mode='Bus', route_id=route_id, route_name=route_name, operator=operator)
            network.add_segment(segment)
            segments_added += 1

            reverse_segment = Segment(to_station, from_station, duration, fare, mode='Bus', route_id=route_id, route_name=route_name, operator=operator)
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
                network.add_segment(Segment(from_station, to_station, duration, fare, mode='Airport Express', route_id='Airport Express', route_name='Airport Express', operator='Airport Express'))
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

    # Treat mapped MTR stations and their nearest bus stops as equivalent nodes
    for mtr_station, bus_stop in MTR_NEAREST_BUS_STOP.items():
        if mtr_station in network.all_stops and bus_stop in network.all_stops:
            network.add_alias(mtr_station, bus_stop)

    all_warnings.append(f"Total network: {len(network.all_stops)} stops, {network.get_num_segments()} segments")
    return network, fare_lookup, all_warnings