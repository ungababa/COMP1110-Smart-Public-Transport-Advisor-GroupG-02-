import os
import sys
import math
import xml.etree.ElementTree as ET
import csv
import heapq
from files import Segment, Journey, TransportNetwork, load_network, load_network_all
from collections import deque
from typing import Callable
from typing import List, Dict, Tuple, Optional

# Require colorama for CLI colours
from colorama import init as _colorama_init, Fore, Style
_colorama_init(autoreset=True)

def _c(text: str, color: str = '') -> str:
    """Wrap text with colour codes."""
    return f"{color}{text}{Style.RESET_ALL}"


def _rgb(r: int, g: int, b: int) -> str:
    """Return a 24-bit ANSI foreground colour escape sequence."""
    return f"\033[38;2;{r};{g};{b}m"


HEADING_COLOUR = _rgb(173, 216, 230)
BREAK_COLOUR = _rgb(187, 213, 218)
RESULT_COLOUR = _rgb(154, 216, 114)
PROMPT_COLOUR = Fore.WHITE


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
        else:  # fewest
            # Assume at least 1 segment per ~500m or so
            return max(1, straight_line_dist / 500)

    # Fallback: if no coordinates, use very small heuristic
    if optimization == 'cost':
        return 0
    return 1  # Minimal heuristic for fewest/duration


# =============================================================================
# Import data structures and load functions from files.py
# =============================================================================

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

    # Track best g_cost for each stop (visited with best cost)
    best_g_cost: Dict[str, float] = {origin: 0}

    # Limit exploration
    exploration_count = 0
    MAX_EXPLORATION = 50000

    while heap and len(journeys) < max_journeys and exploration_count < MAX_EXPLORATION:
        exploration_count += 1
        _, _, current = heapq.heappop(heap)

        # If we reached destination
        if current.stop == destination and current.path:
            path_key = tuple(s.from_stop + '->' + s.to_stop for s in current.path)
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
                g_cost = current.g_cost + segment.duration
            elif optimization == 'cost':
                if current.last_segment is not None and segment.route_id and current.last_segment.route_id == segment.route_id and current.last_segment.mode_of_transport == segment.mode_of_transport:
                    g_cost = current.g_cost
                else:
                    g_cost = current.g_cost + segment.cost
            else:  # fewest
                g_cost = current.g_cost + 1

            # Skip if we've found a better path to this stop
            if next_canonical in best_g_cost and best_g_cost[next_canonical] <= g_cost:
                continue

            # Check for cycles in current path using canonical stops
            if any((network.get_canonical_stop(s.to_stop) if hasattr(network, 'get_canonical_stop') else s.to_stop) == next_canonical for s in current.path):
                continue

            # Update best cost and add to heap
            best_g_cost[next_canonical] = g_cost
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
        return sorted(journeys, key=lambda j: (j.total_duration, j.total_cost, j.num_segments))
    elif preference == 'cheapest':
        return sorted(journeys, key=lambda j: (j.total_cost, j.total_duration, j.num_segments))
    elif preference == 'fewest':
        return sorted(journeys, key=lambda j: (j.num_segments, j.total_duration, j.total_cost))
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
        print("\n" + _c("No transport modes detected in the current network.", RESULT_COLOUR))
        return None

    modes_list = sorted(modes)
    print("\n" + _c("Select transport medium preference (multi-select allowed):", HEADING_COLOUR + Style.BRIGHT))
    for i, m in enumerate(modes_list, 1):
        print(_c(f"  {i}.", Fore.YELLOW), _c(m, Fore.WHITE))
    any_index = len(modes_list) + 1
    print(_c(f"  {any_index}.", Fore.YELLOW), _c("Any / No preference", Fore.WHITE))
    print(_c("Enter choices as numbers separated by commas (e.g. 1,3). Press Enter for Any.", PROMPT_COLOUR), end=" ")

    while True:
        print(end="", flush=True)
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
            print(_c("Invalid input. Use numbers like '1' or '1,3' or ranges '1-3'.", RESULT_COLOUR))
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
            print(_c("Invalid selection. Please choose from the listed numbers.", RESULT_COLOUR))
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
    sep = _c("=" * 60, BREAK_COLOUR)
    title = _c("  Smart Public Transport Advisor", HEADING_COLOUR + Style.BRIGHT)
    print("\n" + sep)
    print(title)
    print(sep)
    print(_c("  1.", Fore.YELLOW), _c("List all stops", Style.NORMAL))
    print(_c("  2.", Fore.YELLOW), _c("Query journeys", Style.NORMAL))
    print(_c("  3.", Fore.YELLOW), _c("Show network summary", Style.NORMAL))
    print(_c("  4.", Fore.YELLOW), _c("Load different network file", Style.NORMAL))
    print(_c("  5.", Fore.YELLOW), _c("Exit", Style.NORMAL))
    print(sep)


def list_stops(network: TransportNetwork) -> None:
    """Displays stops in the network with search/filter options."""
    stops = network.get_stops()
    if not stops:
        print("\n" + _c("No stops in the network.", RESULT_COLOUR))
        return

    print(_c(f"\nTotal stops: {len(stops)}", HEADING_COLOUR))
    print(_c("Press ENTER to list all stop or TYPE stop name to search: ", PROMPT_COLOUR), end="", flush=True)
    sys.stdout.flush()
    query = input().strip()

    if (query == ""):
        print(_c("\nAll stops:", HEADING_COLOUR))
        print(_c("-" * 30, BREAK_COLOUR))
        for i, stop in enumerate(stops, 1):
            print(_c(f"  {i}.", Fore.YELLOW), _c(stop, RESULT_COLOUR))
    else:
        # Filter stops containing the query (case insensitive)
        filtered = [stop for stop in stops if query.lower() in stop.lower()]
        if not filtered:
            print(_c(f"\nNo stops found containing '{query}'.", RESULT_COLOUR))
        else:
            print(_c(f"\nStops containing '{query}' ({len(filtered)} found):", HEADING_COLOUR))
            print(_c("-" * 30, BREAK_COLOUR))
            for i, stop in enumerate(filtered, 1):
                print(_c(f"  {i}.", Fore.YELLOW), _c(stop, RESULT_COLOUR))


def show_summary(network: TransportNetwork) -> None:
    """Displays network summary statistics."""
    num_stops = len(network.all_stops)
    num_segments = network.get_num_segments()
    avg_duration, avg_cost = network.get_average_stats()

    print("\n" + _c("-" * 40, BREAK_COLOUR))
    print(_c("         Network Summary", HEADING_COLOUR))
    print(_c("-" * 40, BREAK_COLOUR))
    print(_c(f"  Number of stops:    {num_stops}", RESULT_COLOUR))
    print(_c(f"  Number of segments: {num_segments}", RESULT_COLOUR))
    if num_segments > 0:
        print(_c(f"  Avg segment duration: {avg_duration:.1f} minutes", RESULT_COLOUR))
        print(_c(f"  Avg segment cost:     ${avg_cost:.2f}", RESULT_COLOUR))
    print(_c("-" * 40, BREAK_COLOUR))


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

    header = _c('=' * 64, BREAK_COLOUR)
    title = _c(f"  Journeys from '{origin}' to '{destination}'", HEADING_COLOUR + Style.BRIGHT)
    sub = _c(f"  Preference: {preference} | Found {len(journeys)} journey(s), showing top {len(ranked)}", RESULT_COLOUR)
    print(f"\n{header}")
    print(title)
    print(sub)
    print(header)

    for i, journey in enumerate(ranked, 1):
        print(f"\n{_c('--- Journey', HEADING_COLOUR)} {_c(str(i), HEADING_COLOUR)} {_c('---', HEADING_COLOUR)}")
        print(f"  {_c('Duration:', Fore.YELLOW)} {_c(str(journey.total_duration) + ' minutes', RESULT_COLOUR)}")
        print(f"  {_c('Cost:', Fore.YELLOW)} {_c(f'${journey.total_cost:.2f} HKD', RESULT_COLOUR)}")
        print(f"  {_c('Segments:', Fore.YELLOW)} {_c(str(journey.num_segments), RESULT_COLOUR)}")
        print(f"  {_c('Route:', HEADING_COLOUR)}")

        for j, segment in enumerate(journey.segments, 1):
            bus_info = ""
            if segment.mode_of_transport == 'Bus' and segment.route_name:
                bus_info = f" {_c('[Bus', HEADING_COLOUR)} {segment.route_name} {segment.operator} {_c(']', HEADING_COLOUR)}"
            seg_line = f"    {j}. {segment.from_stop} -> {segment.to_stop} ({segment.duration}min, ${segment.cost:.2f}) [{segment.mode_of_transport}]"
            print(_c(f"    {j}.", Fore.YELLOW), _c(f"{segment.from_stop} -> {segment.to_stop} ({segment.duration}min, ${segment.cost:.2f}) [{segment.mode_of_transport}]", RESULT_COLOUR) + bus_info)

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
        # Print prompt explicitly with flush to avoid buffering
        print(_c(prompt_msg, PROMPT_COLOUR), end="", flush=True)
        sys.stdout.flush()  # Force output to terminal
        user_input = input().strip()
        
        if not user_input:
            print(_c("Please enter a stop name.", RESULT_COLOUR))
            continue

        normalized = " ".join(user_input.lower().split())

        # Exact match
        exact = next((s for s in stops if s.lower() == normalized), None)
        if exact:
            return exact

        # Partial word match (all words must be in stop name)
        words = normalized.split()
        if words:
            matches = [s for s in stops if all(w in s.lower() for w in words)]
            if matches:
                if len(matches) == 1:
                    print(_c(f"  -> {matches[0]}", RESULT_COLOUR))
                    return matches[0]
                print(_c(f"  Matches: {', '.join(matches[:8])}", RESULT_COLOUR))
                continue

        print(_c(f"Error: No stop found matching '{user_input}'", RESULT_COLOUR))


def _matches_all_words(text: str, stops: List[str]) -> List[str]:
    """Return stops where ALL words in text are found in the stop name."""
    text_lower = text.lower()
    words = text_lower.split()
    if not words:
        return []

    matches = []
    for stop in stops:
        stop_lower = stop.lower()
        if all(word in stop_lower for word in words):
            matches.append(stop)
    return matches


def get_preference() -> str:
    """Prompts user for preference mode and returns valid preference.

    Returns:
        Valid preference string: 'fastest', 'cheapest', or 'fewest'
    """
    while True:
        print("\n" + _c("Select preference:", HEADING_COLOUR + Style.BRIGHT))
        print(_c("  1.", Fore.YELLOW), _c("Fastest (shortest total time)", Fore.WHITE))
        print(_c("  2.", Fore.YELLOW), _c("Cheapest (lowest total cost)", Fore.WHITE))
        print(_c("  3.", Fore.YELLOW), _c("Fewest segments (simplest route)", Fore.WHITE))
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
            print(_c("Invalid choice. Please enter 1, 2, or 3.", RESULT_COLOUR))


# =============================================================================
# Main Program Functions
# =============================================================================

def query_journeys(network: TransportNetwork, fare_lookup: Dict[Tuple[str, str], float]) -> None:
    """Handles the journey query workflow."""
    if not network.all_stops:
        print("\nError: No network loaded. Please load a network first.")
        return

    # Get origin and destination with autocomplete
    print(_c("\nTip: Start typing a stop name, see suggestions below.", HEADING_COLOUR))
    origin = prompt_stop_input("\nEnter origin stop: ", network)
    destination = prompt_stop_input("Enter destination stop: ", network)

    # Validate stops
    is_valid, error_msg, origin, destination = validate_stops(network, origin, destination)
    if not is_valid:
        print(_c(f"\n{error_msg}", RESULT_COLOUR))
        return

    # Get transport medium preference (multi-select)
    transport_pref = get_transport_preferences(network)

    # Get preference
    preference = get_preference()

    # Map preference to optimization parameter
    optimization = preference_to_optimization(preference)

    # Generate journeys using A* with optimization
    journeys = generate_journeys(network, fare_lookup, origin, destination,
                               optimization=optimization)

    # Apply transport-mode filter (if any)
    journeys = filter_journeys_by_transport(journeys, transport_pref)

    # Display results
    display_journeys(journeys, origin, destination, preference)


def load_network_interactive() -> Tuple[Optional[TransportNetwork], Dict[Tuple[str, str], float], List[str]]:
    """Prompts user for network file path and loads it."""
    print(_c("\nEnter network file path: ", PROMPT_COLOUR), end="", flush=True)
    sys.stdout.flush()
    filename = input().strip()

    if not filename:
        print(_c("Error: No filename provided.", RESULT_COLOUR))
        return None, {}, ["Error: No filename provided."]

    network, fare_lookup, warnings = load_network(filename)
    return network, fare_lookup, warnings

# =============================================================================
# Main Entry Point
# =============================================================================

def main():
    """Main function - entry point of the program."""
    # Try to load from all transport data
    print(_c("Loading complete transport network...", HEADING_COLOUR))
    network, fare_lookup, warnings = load_network_all()

    if not network.all_stops:
        print(_c("Loading default network from 'data/network.csv'...", HEADING_COLOUR))
        network, fare_lookup, warnings = load_network("data/network.csv")

    for warning in warnings:
        print(_c(warning, RESULT_COLOUR))

    if not network.all_stops:
        print(_c("\nWarning: No network could be loaded.", RESULT_COLOUR))
        print(_c("You can load a different network using option 4.", RESULT_COLOUR))

    # Main menu loop
    while True:
        display_menu()
        print(_c("\nEnter choice (1-5): ", PROMPT_COLOUR), end="", flush=True)
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
            print(_c("\nThank you for using Smart Public Transport Advisor!", HEADING_COLOUR))
            print(_c("Goodbye!", RESULT_COLOUR))
            break

        else:
            print(_c("\nInvalid choice. Please enter a number 1-5.", RESULT_COLOUR))

if __name__ == "__main__":
    # Check if running in GUI mode
    if len(sys.argv) > 1 and sys.argv[1] == "--gui":
        from gui.main_window import run_gui

        print(_c("Loading transport network for GUI...", HEADING_COLOUR))
        network, fare_lookup, warnings = load_network_all()

        if not network.all_stops:
            print(_c("Loading default network from 'data/network.csv'...", HEADING_COLOUR))
            network, fare_lookup, warnings = load_network("data/network.csv")

        for warning in warnings:
            print(_c(warning, RESULT_COLOUR))

        if not network.all_stops:
            print(_c("Error: No network could be loaded.", RESULT_COLOUR))
            sys.exit(1)

        print(_c(f"Loaded: {len(network.all_stops)} stops", RESULT_COLOUR))
        print(_c("Starting GUI...", HEADING_COLOUR))
        run_gui(network, fare_lookup)
    else:
        main()