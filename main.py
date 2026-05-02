import os
import sys
import math
import xml.etree.ElementTree as ET
from typing import List, Dict, Tuple, Optional
import csv
from collections import deque

def preference_to_optimization(preference: str) -> str:
    """Map a user preference to the A* optimization mode."""
    if preference in {'duration', 'cost', 'fewest'}:
        return preference
    return {
        'fastest': 'duration',
        'cheapest': 'cost',
        'fewest': 'fewest',
    }.get(preference, 'duration')

# =============================================================================
# Import data structures and load functions from files.py
# =============================================================================
from files import Segment, Journey, TransportNetwork, load_network, load_network_all, haversine_distance

# =============================================================================
# A* Pathfinding Algorithm
# =============================================================================

import heapq
from typing import Callable

class AStarNode:
    """Node for A* priority queue."""
    __slots__ = ['g_cost', 'f_cost', 'stop', 'path', 'last_segment']

    def __init__(self, g_cost: float, f_cost: float, stop: str, path: List[Segment], last_segment: Optional[Segment] = None):
        self.g_cost = g_cost
        self.f_cost = f_cost
        self.stop = stop
        self.path = path
        self.last_segment = last_segment

    def __lt__(self, other):
        return self.f_cost < other.f_cost


def estimate_cost(network: TransportNetwork, current_stop: str, destination: str,
                 optimization: str) -> float:
    """Heuristic function for A* - estimates minimum cost from current to destination.

    Args:
        network: The transport network
        current_stop: Current stop name
        destination: Destination stop name
        optimization: 'duration', 'cost', or 'fewest'

    Returns:
        Estimated minimum cost to reach destination
    """
    # Get coordinates
    curr_coords = network.get_stop_coords(current_stop)
    dest_coords = network.get_stop_coords(destination)

    if curr_coords and dest_coords:
        # Use haversine distance as heuristic
        lat1, lon1 = curr_coords
        lat2, lon2 = dest_coords
        straight_line_dist = haversine_distance(lat1, lon1, lat2, lon2)

        if optimization == 'duration':
            # Assume max speed ~50 km/h for transit = 833 m/min
            return straight_line_dist / 833
        elif optimization == 'cost':
            # Minimum possible cost is 0
            return 0
        else:  # fewest legs
            # Best case is always 1 more leg to reach the destination
            return 1

    # Fallback: if no coordinates, use very small heuristic
    if optimization == 'cost':
        return 0
    return 1  # Minimal heuristic for fewest/duration


def transfer_time_penalty(prev_segment: Optional[Segment], next_segment: Segment) -> float:
    """Return the transfer penalty (buffer time) between consecutive segments.

    A penalty is added when switching between different routes or transport modes.
    Same route_id + mode is considered a continuous ride with no penalty.
    If route_id is missing or route_name matches, treat it as continuous when mode is the same.
    """
    if prev_segment is None:
        return 0

    if next_segment.mode_of_transport != prev_segment.mode_of_transport:
        return 5

    if next_segment.route_id and prev_segment.route_id:
        if next_segment.route_id == prev_segment.route_id:
            return 0
    elif next_segment.route_name and prev_segment.route_name:
        if next_segment.route_name == prev_segment.route_name:
            return 0

    # If both segments are the same mode and share either route_id or route_name, no transfer penalty.
    if next_segment.route_id == prev_segment.route_id or (next_segment.route_name and prev_segment.route_name and next_segment.route_name == prev_segment.route_name):
        return 0

    return 5


def generate_journeys_astar(network: TransportNetwork, fare_lookup: Dict[Tuple[str, str], float],
                            origin: str, destination: str, optimization: str = 'duration',
                            max_journeys: int = 20) -> List[Journey]:
    """Generates candidate journeys using A* algorithm.

    A* uses a heuristic to prioritize paths that are closer to the goal,
    making it more efficient than BFS for finding optimal paths.

    Args:
        network: The transport network
        fare_lookup: Dictionary of (from, to) -> fare
        origin: Starting stop name
        destination: Ending stop name
        optimization: 'duration', 'cost', or 'fewest' (what to minimize)
        max_journeys: Maximum number of journeys to return

    Returns:
        List of Journey objects found
    """
    origin = network.get_canonical_stop(origin) if hasattr(network, 'get_canonical_stop') else origin
    destination = network.get_canonical_stop(destination) if hasattr(network, 'get_canonical_stop') else destination

    if origin not in network.all_stops or destination not in network.all_stops:
        return []

    optimization = preference_to_optimization(optimization)

    journeys = []
    found_paths = set()

    # Priority queue for A*
    # heap: (f_cost, counter, AStarNode)
    counter = 0
    h_start = estimate_cost(network, origin, destination, optimization)

    if optimization == 'duration':
        g_start = 0
    elif optimization == 'cost':
        g_start = 0
    else:  # fewest
        g_start = 0

    initial_node = AStarNode(g_start, g_start + h_start, origin, [])
    heap = [(initial_node.f_cost, counter, initial_node)]

    # Track best g_cost for each stop + last-route state (visited with best cost)
    best_g_cost: Dict[Tuple[str, Optional[str], Optional[str]], float] = {
        (origin, None, None): 0
    }

    # Limit exploration
    exploration_count = 0
    MAX_EXPLORATION = 50000

    while heap and len(journeys) < max_journeys and exploration_count < MAX_EXPLORATION:
        exploration_count += 1
        _, _, current = heapq.heappop(heap)

        # If we reached destination
        if current.stop == destination and current.path:
            path_key = tuple(
                f"{s.from_stop}->{s.to_stop}|{s.mode_of_transport}|{s.route_id or ''}|{s.route_name or ''}"
                for s in current.path
            )
            if path_key not in found_paths:
                found_paths.add(path_key)
                journeys.append(Journey(current.path.copy(), fare_lookup, origin, destination))
                continue

        # Explore neighbors
        for segment in network.get_outgoing_segments(current.stop):
            next_stop = segment.to_stop
            next_canonical = network.get_canonical_stop(next_stop) if hasattr(network, 'get_canonical_stop') else next_stop

            # Calculate actual cost to reach next_stop
            if optimization == 'duration':
                penalty = transfer_time_penalty(current.last_segment, segment)
                g_cost = current.g_cost + segment.duration + penalty
            elif optimization == 'cost':
                if current.last_segment is not None and segment.route_id and current.last_segment.route_id == segment.route_id and current.last_segment.mode_of_transport == segment.mode_of_transport:
                    g_cost = current.g_cost
                else:
                    g_cost = current.g_cost + segment.cost
            else:  # fewest — count legs (transfers), not raw segments
                # Only increment when starting a new leg (route or mode changes)
                same_route = (
                    current.last_segment is not None
                    and segment.route_id is not None
                    and segment.route_id == current.last_segment.route_id
                    and segment.mode_of_transport == current.last_segment.mode_of_transport
                )
                g_cost = current.g_cost if same_route else current.g_cost + 1

            # Skip if we've found a better path to this stop+route state
            next_state = (next_canonical, segment.route_id, segment.mode_of_transport)
            if next_state in best_g_cost and best_g_cost[next_state] <= g_cost:
                continue

            # Check for cycles in current path using canonical stops
            if any((network.get_canonical_stop(s.to_stop) if hasattr(network, 'get_canonical_stop') else s.to_stop) == next_canonical for s in current.path):
                continue

            # Update best cost and add to heap
            best_g_cost[next_state] = g_cost
            h_estimate = estimate_cost(network, next_stop, destination, optimization)
            f_cost = g_cost + h_estimate

            new_path = current.path + [segment]
            new_node = AStarNode(g_cost, f_cost, next_canonical, new_path, segment)
            counter += 1
            heapq.heappush(heap, (f_cost, counter, new_node))

    return journeys

# =============================================================================
# Journey Generation (A* Algorithm)
# =============================================================================

def generate_journeys(network: TransportNetwork, fare_lookup: Dict[Tuple[str, str], float], origin: str, destination: str,
                      max_depth: int = 30, max_journeys: int = 20, optimization: str = 'duration') -> List[Journey]:
    """Generates candidate journeys using A* algorithm.

    Uses A* with geographic heuristic for efficient pathfinding.
    Supports optimization by duration, cost, or fewest segments.

    Args:
        network: The transport network
        fare_lookup: Dictionary of (from, to) -> fare
        origin: Starting stop name
        destination: Ending stop name
        max_depth: Maximum number of segments in a journey (default: 30)
        max_journeys: Maximum number of journeys to return (default: 20)
        optimization: 'duration', 'cost', or 'fewest' (what to minimize)

    Returns:
        List of Journey objects found (up to max_journeys)
    """
    if origin not in network.all_stops or destination not in network.all_stops:
        return []

    # Use A* algorithm
    return generate_journeys_astar(network, fare_lookup, origin, destination,
                                   optimization=optimization, max_journeys=max_journeys)


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
        return sorted(journeys, key=lambda j: (j.total_duration, j.total_cost, j.num_legs))
    elif preference == 'cheapest':
        return sorted(journeys, key=lambda j: (j.total_cost, j.total_duration, j.num_legs))
    elif preference == 'fewest':
        # Sort by number of legs (transfers), not raw segment count.
        # A 6-stop non-stop ride (1 leg) should rank above a 2-stop journey
        # that requires a mode/route change (2 legs).
        return sorted(journeys, key=lambda j: (j.num_legs, j.total_duration, j.total_cost))
    else:
        return journeys


def get_transport_preferences(network: TransportNetwork) -> Optional[set]:
    """Prompt user to select transport medium(s).

    Returns a set of selected mode strings, or None for Any/skip.
    """
    # Collect available modes from the network
    modes = set()
    for segments in network.stops.values():
        for s in segments:
            modes.add(s.mode_of_transport)

    if not modes:
        print("\nNo transport modes detected in the current network.")
        return None

    modes_list = sorted(modes)
    print("\nSelect transport medium preference (multi-select allowed):")
    for i, m in enumerate(modes_list, 1):
        print(f"  {i}. {m}")
    any_index = len(modes_list) + 1
    print(f"  {any_index}. Any / No preference")
    print("Enter choices as numbers separated by commas (e.g. 1,3). Press Enter for Any.")

    while True:
        print("Enter choice(s): ", end="", flush=True)
        sys.stdout.flush()
        choice = input().strip()
        if choice == "":
            return None

        # Parse comma-separated choices and ranges
        parts = [p.strip() for p in choice.split(',') if p.strip()]
        indices = set()
        valid = True
        for part in parts:
            if '-' in part:
                try:
                    a, b = part.split('-')
                    a_i = int(a)
                    b_i = int(b)
                    if a_i <= 0 or b_i <= 0 or a_i > b_i:
                        valid = False
                        break
                    for v in range(a_i, b_i + 1):
                        indices.add(v)
                except Exception:
                    valid = False
                    break
            else:
                try:
                    v = int(part)
                    indices.add(v)
                except Exception:
                    valid = False
                    break

        if not valid:
            print("Invalid input. Use numbers like '1' or '1,3' or ranges '1-3'.")
            continue

        # If user selected Any
        if any_index in indices:
            return None

        # Validate indices and map to modes
        selected = set()
        out_of_range = False
        for idx in indices:
            if 1 <= idx <= len(modes_list):
                selected.add(modes_list[idx - 1])
            else:
                out_of_range = True
                break

        if out_of_range or not selected:
            print("Invalid selection. Please choose from the listed numbers.")
            continue

        return selected


def filter_journeys_by_transport(journeys: List[Journey], preferred_modes: Optional[set]) -> List[Journey]:
    """Filter journeys according to preferred transport modes.

    Behaviour:
    - If preferred_modes is None or empty: return journeys unchanged.
    - If a single mode selected: strict policy (all segments must be in the mode set).
    - If multiple modes selected: permissive policy (at least one segment matches).
    """
    if not preferred_modes:
        return journeys

    if len(preferred_modes) == 1:
        # Strict: all segments must be in preferred_modes
        return [j for j in journeys if all(s.mode_of_transport in preferred_modes for s in j.segments)]
    else:
        # Permissive: at least one segment matches
        return [j for j in journeys if any(s.mode_of_transport in preferred_modes for s in j.segments)]


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
    """Displays stops in the network with search/filter options."""
    stops = network.get_stops()
    if not stops:
        print("\nNo stops in the network.")
        return

    print(f"\nTotal stops: {len(stops)}")
    print("Enter stop name to search (or 'all' to list all, 'summary' for stats): ", end="", flush=True)
    sys.stdout.flush()
    query = input().strip()

    if query.lower() == 'summary':
        show_summary(network)
        return
    elif query.lower() == 'all':
        print("\nAll stops:")
        print("-" * 30)
        for i, stop in enumerate(stops, 1):
            print(f"  {i}. {stop}")
    else:
        # Filter stops containing the query (case insensitive)
        filtered = [stop for stop in stops if query.lower() in stop.lower()]
        if not filtered:
            print(f"\nNo stops found containing '{query}'.")
        else:
            print(f"\nStops containing '{query}' ({len(filtered)} found):")
            print("-" * 30)
            for i, stop in enumerate(filtered, 1):
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
        print(f"\n{_c('--- Journey', HEADING_COLOUR)} {_c(str(i), HEADING_COLOUR)} {_c('---', HEADING_COLOUR)}")
        print(f"  {_c('Duration:', Fore.YELLOW)} {_c(str(journey.total_duration) + ' minutes', RESULT_COLOUR)}")
        print(f"  {_c('Cost:', Fore.YELLOW)} {_c(f'${journey.total_cost:.2f} HKD', RESULT_COLOUR)}")
        print(f"  {_c('Legs:', Fore.YELLOW)} {_c(str(journey.num_legs), RESULT_COLOUR)}")
        print(f"  {_c('Route:', HEADING_COLOUR)}")

        for j, segment in enumerate(journey.segments, 1):
            bus_info = ""
            if segment.mode_of_transport == 'Bus' and segment.route_name:
                bus_info = f" {_c('[Bus', HEADING_COLOUR)} {segment.route_name} {segment.operator} {_c(']', HEADING_COLOUR)}"
            print(_c(f"    {j}.", Fore.YELLOW),
                  _c(f"{segment.from_stop} -> {segment.to_stop} "
                     f"({segment.duration}min, ${segment.cost:.2f}) "
                     f"[{segment.mode_of_transport}]", RESULT_COLOUR) + bus_info)

        print()


# =============================================================================
# Input Validation Functions
# =============================================================================

def get_valid_stops(network: TransportNetwork) -> List[str]:
    """Returns list of valid stop names."""
    return network.get_stops()


def validate_stops(network: TransportNetwork, origin: str, destination: str) -> Tuple[bool, str, str, str]:
    """Validates origin and destination stops (case insensitive).

    Returns:
        Tuple of (is_valid, error_message, normalized_origin, normalized_destination)
    """
    stops = network.get_stops()
    stops_lower = {stop.lower(): stop for stop in stops}

    origin_norm = stops_lower.get(origin.lower())
    if not origin_norm:
        return False, f"Error: Unknown stop '{origin}'", "", ""

    dest_norm = stops_lower.get(destination.lower())
    if not dest_norm:
        return False, f"Error: Unknown stop '{destination}'", "", ""

    if origin_norm == dest_norm:
        return False, "Error: Origin and destination cannot be the same", "", ""

    return True, "", origin_norm, dest_norm


def prompt_stop_input(prompt_msg: str, network: TransportNetwork) -> str:
    """Prompt for stop input with validation."""
    stops = sorted(network.all_stops, key=str.lower)

    while True:
        print(_c(prompt_msg, PROMPT_COLOUR), end="", flush=True)
        sys.stdout.flush()
        user_input = input().strip()

        if not user_input:
            print("Please enter a stop name.")
            continue

        normalized = " ".join(user_input.lower().split())

        exact = next((s for s in stops if s.lower() == normalized), None)
        if exact:
            return exact

        words = normalized.split()
        if words:
            matches = [s for s in stops if all(w in s.lower() for w in words)]
            if matches:
                if len(matches) == 1:
                    print(f"  -> {matches[0]}")
                    return matches[0]
                print(f"  Matches: {', '.join(matches[:8])}")
                continue

        print(f"Error: No stop found matching '{user_input}'")


def get_preference() -> str:
    """Prompts user for preference mode and returns valid preference."""
    while True:
        print("\n" + _c("Select preference:", HEADING_COLOUR + Style.BRIGHT))
        print(_c("  1.", Fore.YELLOW), _c("Fastest (shortest total time)", Fore.WHITE))
        print(_c("  2.", Fore.YELLOW), _c("Cheapest (lowest total cost)", Fore.WHITE))
        print(_c("  3.", Fore.YELLOW), _c("Fewest transfers (simplest route)", Fore.WHITE))
        print(_c("Enter choice (1-3): ", PROMPT_COLOUR), end="", flush=True)
        sys.stdout.flush()
        choice = input().strip()

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

def query_journeys(network: TransportNetwork, fare_lookup: Dict[Tuple[str, str], float]) -> None:
    """Handles the journey query workflow."""
    if not network.all_stops:
        print("\nError: No network loaded. Please load a network first.")
        return

    print(_c("\nTip: Start typing a stop name, see suggestions below.", HEADING_COLOUR))
    origin = prompt_stop_input("\nEnter origin stop: ", network)
    destination = prompt_stop_input("Enter destination stop: ", network)

    is_valid, error_msg, origin, destination = validate_stops(network, origin, destination)
    if not is_valid:
        print(f"\n{error_msg}")
        return

    transport_pref = get_transport_preferences(network)
    preference = get_preference()
    optimization = preference_to_optimization(preference)

    journeys = generate_journeys(network, fare_lookup, origin, destination,
                                 optimization=optimization)
    journeys = filter_journeys_by_transport(journeys, transport_pref)
    display_journeys(journeys, origin, destination, preference)


def load_network_interactive() -> Tuple[Optional[TransportNetwork], Dict[Tuple[str, str], float], List[str]]:
    """Prompts user for network file path and loads it."""
    print("\nEnter network file path: ", end="", flush=True)
    sys.stdout.flush()
    filename = input().strip()

    if not filename:
        print("Error: No filename provided.")
        return None, {}, ["Error: No filename provided."]

    network, fare_lookup, warnings = load_network(filename)
    return network, fare_lookup, warnings


# =============================================================================
# Main Entry Point
# =============================================================================

def main():
    """Main function - entry point of the program."""
    print(_c("Loading complete transport network...", HEADING_COLOUR))
    network, fare_lookup, warnings = load_network_all()

    if not network.all_stops:
        print("Loading default network from 'data/network.csv'...")
        network, fare_lookup, warnings = load_network("data/network.csv")

    for warning in warnings:
        print(warning)

    if not network.all_stops:
        print("\nWarning: No network could be loaded.")
        print("You can load a different network using option 4.")

    while True:
        display_menu()
        print("\nEnter choice (1-5): ", end="", flush=True)
        sys.stdout.flush()
        choice = input().strip()

        if choice == '1':
            list_stops(network)
        elif choice == '2':
            query_journeys(network, fare_lookup)
        elif choice == '3':
            show_summary(network)
        elif choice == '4':
            new_network, new_fare_lookup, new_warnings = load_network_interactive()
            for warning in new_warnings:
                print(warning)
            if new_network and new_network.all_stops:
                network = new_network
                fare_lookup = new_fare_lookup
                print("\nNetwork loaded successfully!")
        elif choice == '5':
            print("\nThank you for using Smart Public Transport Advisor!")
            print("Goodbye!")
            break
        else:
            print("\nInvalid choice. Please enter a number 1-5.")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--gui":
        from gui.main_window import run_gui

        print("Loading transport network for GUI...")
        network, fare_lookup, warnings = load_network_all()

        if not network.all_stops:
            print("Loading default network from 'data/network.csv'...")
            network, fare_lookup, warnings = load_network("data/network.csv")

        for warning in warnings:
            print(warning)

        if not network.all_stops:
            print("Error: No network could be loaded.")
            sys.exit(1)

        print(f"Loaded: {len(network.all_stops)} stops")
        print("Starting GUI...")
        run_gui(network, fare_lookup)
    else:
        main()
