"""
Smart Public Transport Advisor
==============================

A text-based Python program that models a small transport network,
accepts user preferences, generates candidate journeys, and ranks them.

Author: COMP1110 Group Project
Version: 1.0
"""

import os
import sys
from typing import List, Dict, Tuple, Optional


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

    def __init__(self, from_stop: str, to_stop: str, duration: int, cost: float):
        self.from_stop = from_stop
        self.to_stop = to_stop
        self.duration = duration
        self.cost = cost

    def __repr__(self):
        return f"Segment({self.from_stop} -> {self.to_stop}, {self.duration}min, ${self.cost:.2f})"


class Journey:
    """Represents a complete journey through the network.

    Attributes:
        segments: List of Segment objects forming the journey
        total_duration: Total travel time in minutes
        total_cost: Total fare in HKD
    """

    def __init__(self, segments: List[Segment]):
        self.segments = segments
        self.total_duration = sum(s.duration for s in segments)
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
    """

    def __init__(self):
        self.stops: Dict[str, List[Segment]] = {}
        self.all_stops: set = set()

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

def load_network_from_mtr() -> Tuple[TransportNetwork, List[str]]:
    """Loads transport network from official MTR data files.

    Reads from:
    - mtr_lines_and_stations.csv: Station info and sequences
    - mtr_lines_fares.csv: Fare data between stations

    Returns:
        Tuple of (TransportNetwork object, list of warning/error messages)
    """
    import csv

    network = TransportNetwork()
    warnings = []

    # Files to try loading
    stations_file = 'mtr_lines_and_stations.csv'
    fares_file = 'mtr_lines_fares.csv'

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
        return load_network('network.csv'), [f"Warning: Could not read {stations_file}: {str(e)}"]

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

    # Typical duration between adjacent stations (in minutes)
    # Most MTR journeys are 2-4 minutes between stations
    TYPICAL_DURATION = 3

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

            # Add forward segment
            segment = Segment(from_station, to_station, TYPICAL_DURATION, fare)
            network.add_segment(segment)
            segments_added += 1

            # Add reverse segment (bidirectional)
            reverse_fare = fare_lookup.get((to_station, from_station), fare)
            reverse_segment = Segment(to_station, from_station, TYPICAL_DURATION, reverse_fare)
            network.add_segment(reverse_segment)
            segments_added += 1

    # Add interchange connections (stations that appear in multiple lines)
    # These are key interchange stations where passengers can change lines
    # We already have them from the line sequences, but let's ensure connectivity

    if segments_added == 0:
        return load_network('network.csv'), ["Warning: No segments created from MTR data, using network.csv"]

    warnings.append(f"Loaded {len(network.all_stops)} stops and {segments_added} segments from MTR data")

    return network, warnings


def load_network(filename: str) -> Tuple[TransportNetwork, List[str]]:
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
    network = TransportNetwork()
    warnings = []

    if not os.path.exists(filename):
        return network, [f"Error: File '{filename}' not found."]

    if os.path.getsize(filename) == 0:
        return network, [f"Error: File '{filename}' is empty."]

    try:
        with open(filename, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        return network, [f"Error: Could not read file: {str(e)}"]

    if not lines:
        return network, [f"Error: File '{filename}' is empty."]

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
        segment = Segment(from_stop, to_stop, duration, cost)
        network.add_segment(segment)
        valid_count += 1

    if valid_count == 0:
        warnings.append(f"Error: No valid segments found in file.")

    return network, warnings


# =============================================================================
# Journey Generation (Depth-Limited DFS)
# =============================================================================

def generate_journeys(network: TransportNetwork, origin: str, destination: str,
                      max_depth: int = 15, max_journeys: int = 20) -> List[Journey]:
    """Generates candidate journeys using BFS to find shortest paths first.

    Uses BFS to find the minimum number of segments, then uses limited DFS
    to explore alternative routes up to max_depth.

    Args:
        network: The transport network
        origin: Starting stop name
        destination: Ending stop name
        max_depth: Maximum number of segments in a journey (default: 15)
        max_journeys: Maximum number of journeys to return (default: 20)

    Returns:
        List of Journey objects found (up to max_journeys)
    """
    from collections import deque

    if origin not in network.all_stops or destination not in network.all_stops:
        return []

    # BFS to find minimum segments needed
    # BFS state: (current_stop, path_as_list_of_segments)
    queue = deque()
    queue.append((origin, []))

    # Track best path length found for each stop
    best_length = {origin: 0}

    journeys = []
    found_paths = set()

    # Limit exploration
    exploration_count = 0
    MAX_EXPLORATION = 50000

    while queue and len(journeys) < max_journeys and exploration_count < MAX_EXPLORATION:
        exploration_count += 1
        current, path = queue.popleft()

        path_len = len(path)

        # If we reached destination
        if current == destination and path:
            path_key = tuple(s.from_stop + '->' + s.to_stop for s in path)
            if path_key not in found_paths:
                found_paths.add(path_key)
                journeys.append(Journey(path.copy()))
                continue

        # If max depth reached, skip
        if path_len >= max_depth:
            continue

        # Explore neighbors
        for segment in network.get_outgoing_segments(current):
            next_stop = segment.to_stop
            new_path_len = path_len + 1

            # Skip if we've found a better path to this stop
            if next_stop in best_length and best_length[next_stop] <= new_path_len:
                continue

            # Check for cycles in current path
            if any(s.to_stop == next_stop for s in path):
                continue

            # Update best length and add to queue
            best_length[next_stop] = new_path_len
            new_path = path + [segment]
            queue.append((next_stop, new_path))

    return journeys


# =============================================================================
# Ranking Functions
# =============================================================================

def rank_journeys(journeys: List[Journey], preference: str) -> List[Journey]:
    """Ranks journeys according to user preference.

    Args:
        journeys: List of Journey objects
        preference: 'fastest', 'cheapest', or 'fewest'

    Returns:
        Sorted list of journeys
    """
    if preference == 'fastest':
        return sorted(journeys, key=lambda j: (j.total_duration, j.total_cost, j.num_segments))
    elif preference == 'cheapest':
        return sorted(journeys, key=lambda j: (j.total_cost, j.total_duration, j.num_segments))
    elif preference == 'fewest':
        return sorted(journeys, key=lambda j: (j.num_segments, j.total_duration, j.total_cost))
    else:
        return journeys


# =============================================================================
# Display Functions
# =============================================================================

def display_menu() -> None:
    """Displays the main menu."""
    print("\n" + "=" * 50)
    print("  Smart Public Transport Advisor")
    print("=" * 50)
    print("  1. List all stops")
    print("  2. Query journeys")
    print("  3. Show network summary")
    print("  4. Load different network file")
    print("  5. Exit")
    print("=" * 50)


def list_stops(network: TransportNetwork) -> None:
    """Displays all stops in the network."""
    stops = network.get_stops()
    if not stops:
        print("\nNo stops in the network.")
        return

    print(f"\nTotal stops: {len(stops)}")
    print("-" * 30)
    for i, stop in enumerate(stops, 1):
        print(f"  {i}. {stop}")


def show_summary(network: TransportNetwork) -> None:
    """Displays network summary statistics."""
    num_stops = len(network.all_stops)
    num_segments = network.get_num_segments()
    avg_duration, avg_cost = network.get_average_stats()

    print("\n" + "-" * 40)
    print("         Network Summary")
    print("-" * 40)
    print(f"  Number of stops:    {num_stops}")
    print(f"  Number of segments: {num_segments}")
    if num_segments > 0:
        print(f"  Avg segment duration: {avg_duration:.1f} minutes")
        print(f"  Avg segment cost:     ${avg_cost:.2f}")
    print("-" * 40)


def display_journeys(journeys: List[Journey], origin: str, destination: str,
                     preference: str, top_n: int = 5) -> None:
    """Displays the top journeys with full breakdown.

    Args:
        journeys: List of ranked Journey objects
        origin: Origin stop name
        destination: Destination stop name
        preference: User's preference mode
        top_n: Number of top journeys to display
    """
    if not journeys:
        print(f"\nNo journeys found from {origin} to {destination}.")
        return

    # Rank and take top N
    ranked = rank_journeys(journeys, preference)[:top_n]

    print(f"\n{'=' * 60}")
    print(f"  Journeys from '{origin}' to '{destination}'")
    print(f"  Preference: {preference}")
    print(f"  Found {len(journeys)} journey(s), showing top {len(ranked)}")
    print(f"{'=' * 60}")

    for i, journey in enumerate(ranked, 1):
        print(f"\n--- Journey {i} ---")
        print(f"  Duration: {journey.total_duration} minutes")
        print(f"  Cost:     ${journey.total_cost:.2f} HKD")
        print(f"  Segments: {journey.num_segments}")
        print("  Route:")

        for j, segment in enumerate(journey.segments, 1):
            print(f"    {j}. {segment.from_stop} -> {segment.to_stop} "
                  f"({segment.duration}min, ${segment.cost:.2f})")

        print()


# =============================================================================
# Input Validation Functions
# =============================================================================

def get_valid_stops(network: TransportNetwork) -> List[str]:
    """Returns list of valid stop names."""
    return network.get_stops()


def validate_stops(network: TransportNetwork, origin: str, destination: str) -> Tuple[bool, str]:
    """Validates origin and destination stops.

    Returns:
        Tuple of (is_valid, error_message)
    """
    stops = network.get_stops()

    if origin not in stops:
        return False, f"Error: Unknown stop '{origin}'"

    if destination not in stops:
        return False, f"Error: Unknown stop '{destination}'"

    if origin == destination:
        return False, "Error: Origin and destination cannot be the same"

    return True, ""


def get_preference() -> str:
    """Prompts user for preference mode and returns valid preference.

    Returns:
        Valid preference string: 'fastest', 'cheapest', or 'fewest'
    """
    while True:
        print("\nSelect preference:")
        print("  1. Fastest (shortest total time)")
        print("  2. Cheapest (lowest total cost)")
        print("  3. Fewest segments (simplest route)")
        choice = input("Enter choice (1-3): ").strip()

        if choice == '1':
            return 'fastest'
        elif choice == '2':
            return 'cheapest'
        elif choice == '3':
            return 'fewest'
        else:
            print("Invalid choice. Please enter 1, 2, or 3.")


# =============================================================================
# Main Program Functions
# =============================================================================

def query_journeys(network: TransportNetwork) -> None:
    """Handles the journey query workflow."""
    if not network.all_stops:
        print("\nError: No network loaded. Please load a network first.")
        return

    # Get origin
    print("\nAvailable stops:")
    stops = network.get_stops()
    for stop in stops:
        print(f"  - {stop}")

    while True:
        origin = input("\nEnter origin stop: ").strip()
        if origin:
            break
        print("Please enter a stop name.")

    # Get destination
    while True:
        destination = input("Enter destination stop: ").strip()
        if destination:
            break
        print("Please enter a stop name.")

    # Validate stops
    is_valid, error_msg = validate_stops(network, origin, destination)
    if not is_valid:
        print(f"\n{error_msg}")
        return

    # Get preference
    preference = get_preference()

    # Generate and display journeys
    journeys = generate_journeys(network, origin, destination)
    display_journeys(journeys, origin, destination, preference)


def load_network_interactive() -> Tuple[Optional[TransportNetwork], List[str]]:
    """Prompts user for network file path and loads it."""
    filename = input("\nEnter network file path: ").strip()

    if not filename:
        print("Error: No filename provided.")
        return None, ["Error: No filename provided."]

    return load_network(filename)


# =============================================================================
# Case Study Runner
# =============================================================================

def run_case_study(network: TransportNetwork, origin: str, destination: str,
                   preference: str) -> None:
    """Runs a case study with given parameters.

    Args:
        network: The transport network
        origin: Origin stop name
        destination: Destination stop name
        preference: Preference mode
    """
    print(f"\n{'#' * 60}")
    print(f"# Case Study: {origin} -> {destination}")
    print(f"# Preference: {preference}")
    print(f"{'#' * 60}")

    is_valid, error_msg = validate_stops(network, origin, destination)
    if not is_valid:
        print(f"\n{error_msg}")
        return

    journeys = generate_journeys(network, origin, destination)
    display_journeys(journeys, origin, destination, preference, top_n=5)


def run_batch_cases(network: TransportNetwork, cases: List[Tuple[str, str, str]]) -> None:
    """Runs multiple case studies in batch mode.

    Args:
        network: The transport network
        cases: List of (origin, destination, preference) tuples
    """
    for origin, dest, pref in cases:
        run_case_study(network, origin, dest, pref)
        print()


# =============================================================================
# Main Entry Point
# =============================================================================

def main():
    """Main function - entry point of the program."""
    # Try to load from MTR data first, fall back to network.csv
    print("Loading network from MTR data...")
    network, warnings = load_network_from_mtr()

    if not network.all_stops:
        print("Loading default network from 'network.csv'...")
        network, warnings = load_network("network.csv")

    for warning in warnings:
        print(warning)

    if not network.all_stops:
        print("\nWarning: No network could be loaded.")
        print("You can load a different network using option 4.")

    # Main menu loop
    while True:
        display_menu()
        choice = input("\nEnter choice (1-5): ").strip()

        if choice == '1':
            list_stops(network)

        elif choice == '2':
            query_journeys(network)

        elif choice == '3':
            show_summary(network)

        elif choice == '4':
            new_network, new_warnings = load_network_interactive()
            for warning in new_warnings:
                print(warning)
            if new_network and new_network.all_stops:
                network = new_network
                print("\nNetwork loaded successfully!")

        elif choice == '5':
            print("\nThank you for using Smart Public Transport Advisor!")
            print("Goodbye!")
            break

        else:
            print("\nInvalid choice. Please enter a number 1-5.")


# Alternative main for batch case study testing
def main_batch_test():
    """Alternative main for testing with predefined case studies."""
    # Try MTR data first, fall back to network.csv
    print("Loading network from MTR data...")
    network, warnings = load_network_from_mtr()

    if not network.all_stops:
        print(f"Loading network from 'network.csv'...")
        network, warnings = load_network("network.csv")

    for warning in warnings:
        print(warning)

    if not network.all_stops:
        print("Error: Could not load network. Exiting.")
        return

    # Define case studies - use real MTR station names
    # Note: Some long-distance routes (like Tuen Mun to Kowloon) require many segments
    cases = [
        # Case 1: Budget commuter - wants cheapest route
        ("Central", "Sha Tin", "cheapest"),
        # Case 2: Last-minute student - wants fastest route
        ("Kowloon Tong", "Causeway Bay", "fastest"),
        # Case 3: Transfer-averse user - wants fewest segments
        # Use a closer destination that's reachable within 15 segments
        ("Tuen Mun", "Tsuen Wan", "fewest"),
        # Case 4: Another fastest route test
        ("Prince Edward", "Ocean Park", "fastest"),
    ]

    print("\n" + "=" * 60)
    print("Running Case Studies")
    print("=" * 60)

    run_batch_cases(network, cases)


if __name__ == "__main__":
    # Check if running in batch test mode
    if len(sys.argv) > 1 and sys.argv[1] == "--batch":
        main_batch_test()
    else:
        main()