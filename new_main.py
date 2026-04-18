"""
Public Transport Management System (Input, Processing, Verification)

This module mirrors the terminal interaction style of main.py while focusing on:
1. CSV input and strict validation
2. Efficient Segment graph loading (no repeated stop objects)
3. Querying and listing all possible routes (no sorting/ranking)
"""

from __future__ import annotations

import csv
import os
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple
from models import TravelOption, Segment, Route, TransportGraph
from journey_planner import rank_routes, filter_by_mode, retry_mode_filter


REQUIRED_HEADERS = [
	"ID",
	"START",
	"STOP",
	"MODE OF TRANSPORT",
	"TIME",
	"PRICE (HKD)",
]


def parse_time_to_minutes(raw_time: str, row_number: int) -> int:
	"""Extract integer minutes from values like '10 mins' or '45 min'."""
	value = raw_time.strip()
	if not value:
		raise ValueError(f"Row {row_number}: TIME is empty.")

	match = re.search(r"(\d+)", value)
	if not match:
		raise ValueError(
			f"Row {row_number}: TIME '{raw_time}' is invalid. Expected a minute value such as '10 mins'."
		)

	minutes = int(match.group(1))
	if minutes <= 0:
		raise ValueError(f"Row {row_number}: TIME must be positive.")
	return minutes


def validate_headers(found_headers: List[str]) -> None:
	normalized = [header.strip() for header in found_headers]
	if normalized != REQUIRED_HEADERS:
		raise ValueError(
			"Header mismatch. Expected exactly: "
			+ ",".join(REQUIRED_HEADERS)
			+ f" | Found: {','.join(normalized)}"
		)


def load_map_csv(filename: str) -> Tuple[Optional[TransportGraph], List[str]]:
	"""Load and validate map CSV. Returns graph and list of messages."""
	messages: List[str] = []

	if not os.path.exists(filename):
		return None, [f"Error: File '{filename}' not found."]
	if os.path.getsize(filename) == 0:
		return None, [f"Error: File '{filename}' is empty."]

	graph = TransportGraph()

	try:
		with open(filename, "r", encoding="utf-8-sig", newline="") as csv_file:
			reader = csv.DictReader(csv_file)
			if reader.fieldnames is None:
				return None, ["Error: Missing CSV header row."]

			validate_headers(reader.fieldnames)

			for row_number, row in enumerate(reader, start=2):
				route_id = (row.get("ID") or "").strip()
				start = (row.get("START") or "").strip()
				stop = (row.get("STOP") or "").strip()
				mode = (row.get("MODE OF TRANSPORT") or "").strip()
				raw_time = (row.get("TIME") or "").strip()
				raw_price = (row.get("PRICE (HKD)") or "").strip()

				if not route_id:
					raise ValueError(f"Row {row_number}: ID is empty.")
				if not start:
					raise ValueError(f"Row {row_number}: START is empty.")
				if not stop:
					raise ValueError(f"Row {row_number}: STOP is empty.")
				if not mode:
					raise ValueError(f"Row {row_number}: MODE OF TRANSPORT is empty.")

				time_minutes = parse_time_to_minutes(raw_time, row_number)

				if not raw_price:
					raise ValueError(f"Row {row_number}: PRICE (HKD) is empty.")
				try:
					price_hkd = float(raw_price)
				except ValueError as exc:
					raise ValueError(
						f"Row {row_number}: PRICE (HKD) '{raw_price}' is invalid. Expected a number."
					) from exc

				if price_hkd < 0:
					raise ValueError(f"Row {row_number}: PRICE (HKD) cannot be negative.")

				graph.add_connection(
					route_id=route_id,
					start=start,
					stop=stop,
					mode_of_transport=mode,
					time_minutes=time_minutes,
					price_hkd=price_hkd,
				)

	except ValueError as exc:
		return None, [f"Error: {exc}"]
	except Exception as exc:
		return None, [f"Error: Could not read file '{filename}': {exc}"]

	if graph.route_count == 0:
		return None, ["Error: No route rows found in CSV."]

	messages.append(
		f"Loaded {graph.num_segments()} stops and {graph.route_count} route options from '{filename}'."
	)
	return graph, messages


def display_menu() -> None:
	"""Displays the main menu in the same style as main.py."""
	print("\n" + "=" * 50)
	print("  Smart Public Transport Advisor")
	print("=" * 50)
	print("  1. List all stops")
	print("  2. Query journeys")
	print("  3. Show network summary")
	print("  4. Load different network file")
	print("  5. Exit")
	print("=" * 50)


def list_stops(graph: TransportGraph) -> None:
	"""Displays stops in the network with search/filter options."""
	stops = graph.get_stops()
	if not stops:
		print("\nNo stops in the network.")
		return

	print(f"\nTotal stops: {len(stops)}")
	query = input("Enter stop name to search (or 'all' to list all, 'summary' for stats): ").strip()

	if query.lower() == "summary":
		show_summary(graph)
		return

	if query.lower() == "all":
		print("\nAll stops:")
		print("-" * 30)
		for i, stop in enumerate(stops, 1):
			print(f"  {i}. {stop}")
		return

	filtered = [stop for stop in stops if query.lower() in stop.lower()]
	if not filtered:
		print(f"\nNo stops found containing '{query}'.")
		return

	print(f"\nStops containing '{query}' ({len(filtered)} found):")
	print("-" * 30)
	for i, stop in enumerate(filtered, 1):
		print(f"  {i}. {stop}")


def show_summary(graph: TransportGraph) -> None:
	"""Displays network summary statistics."""
	num_stops = graph.num_segments()
	num_routes = graph.route_count
	avg_time, avg_price = graph.average_stats()

	print("\n" + "-" * 40)
	print("         Network Summary")
	print("-" * 40)
	print(f"  Number of stops:    {num_stops}")
	print(f"  Number of segments: {num_routes}")
	if num_routes > 0:
		print(f"  Avg segment duration: {avg_time:.1f} minutes")
		print(f"  Avg segment cost:     ${avg_price:.2f}")
	print("-" * 40)


def normalize_stop_query(value: str) -> str:
	"""Normalize user stop input for case-insensitive exact-name matching."""
	# Keep punctuation/words so "Central" and "Central (Pier 5)" remain different.
	return " ".join(value.strip().split()).casefold()


def validate_stops(graph: TransportGraph, origin: str, destination: str) -> Tuple[bool, str, str, str]:
	"""Validates origin and destination stops (case insensitive)."""
	stops = graph.get_stops()
	stops_lookup = {normalize_stop_query(stop): stop for stop in stops}

	origin_norm = stops_lookup.get(normalize_stop_query(origin))
	if not origin_norm:
		return False, f"Error: Unknown stop '{origin}'", "", ""

	destination_norm = stops_lookup.get(normalize_stop_query(destination))
	if not destination_norm:
		return False, f"Error: Unknown stop '{destination}'", "", ""

	if origin_norm == destination_norm:
		return False, "Error: Origin and destination cannot be the same", "", ""

	return True, "", origin_norm, destination_norm


def generate_all_routes(
	graph: TransportGraph,
	origin: str,
	destination: str,
	max_depth: int = 6,
) -> List[Route]:
	"""Generate all possible routes using depth-limited DFS, no sorting."""
	routes: List[Route] = []

	start_segment = graph.get_segment(origin)
	end_segment = graph.get_segment(destination)

	if start_segment is None or end_segment is None:
		return routes

	def dfs(current: Segment, visited: Set[str], path: List[Tuple[Segment, TravelOption]]) -> None:
		if len(path) > max_depth:
			return

		if current.stop_name == destination and path:
			routes.append(Route(legs=list(path)))
			return

		for option in current.next_options:
			next_stop_name = option.next_segment.stop_name
			if next_stop_name in visited:
				continue

			path.append((current, option))
			visited.add(next_stop_name)
			dfs(option.next_segment, visited, path)
			visited.remove(next_stop_name)
			path.pop()

	dfs(start_segment, {origin}, [])
	return routes


def display_routes(routes: List[Route], origin: str, destination: str,
				   preference: str, allowed_modes: Optional[Set[str]]) -> None:
	if not routes:
		print(f"\nNo journeys found from {origin} to {destination}.")
		return

	preference_labels = {"fastest": "Fastest", "cheapest": "Cheapest", "fewest": "Fewest stops"}
	pref_label = preference_labels.get(preference, preference.capitalize())

	print(f"\n{'=' * 60}")
	print(f"  Journeys from '{origin}' to '{destination}'")
	print(f"  Ranked by: {pref_label}")
	if allowed_modes:
		print(f"  Mode filter: {', '.join(sorted(allowed_modes))} only")
	print(f"  Showing top {len(routes)} result(s)")
	print(f"{'=' * 60}")

	for i, route in enumerate(routes, 1):
		print(f"\n  Route {i}")
		print(f"  {'─' * 40}")
		print(f"  Time:   {route.total_time} mins")
		print(f"  Cost:   ${route.total_price:.2f} HKD")
		print(f"  Stops:  {len(route.legs)}")
		print(f"  Path:")
		for leg_index, (segment, option) in enumerate(route.legs, 1):
			print(f"    {leg_index}. {segment.stop_name} → {option.next_segment.stop_name}")
			print(f"       {option.mode_of_transport}  |  {option.time_minutes} mins  |  ${option.price_hkd:.2f}")

	print(f"\n{'=' * 60}")


# updated query flow — now collects preference + mode filter before showing results
def query_journeys(graph: TransportGraph) -> None:
	"""Handles the journey query workflow."""
	if not graph.has_stops():
		print("\nError: No network loaded. Please load a network first.")
		return

	print("\nTip: Use option 1 to search/list stops if needed.")
	stops_lookup = {normalize_stop_query(stop): stop for stop in graph.get_stops()}

	while True:
		origin_input = input("\nEnter origin stop: ").strip()
		if not origin_input:
			print("Please enter a stop name.")
			continue

		origin = stops_lookup.get(normalize_stop_query(origin_input))
		if origin is None:
			print(f"Error: Unknown stop '{origin_input}'")
			continue
		break

	while True:
		destination_input = input("Enter destination stop: ").strip()
		if not destination_input:
			print("Please enter a stop name.")
			continue
		destination = stops_lookup.get(normalize_stop_query(destination_input))
		if destination is None:
			print(f"Error: Unknown stop '{destination_input}'")
			continue
		break

	is_valid, error_msg, origin, destination = validate_stops(graph, origin, destination)
	if not is_valid:
		print(f"\n{error_msg}")
		return

	preference = ask_preference()

	print("\n  Searching for routes...")
	all_routes = generate_all_routes(graph, origin, destination)

	if not all_routes:
		print(f"\n  No journeys found from '{origin}' to '{destination}'.")
		return

	print(f"  Found {len(all_routes)} possible route(s).")

	filtered_routes, allowed_modes = retry_mode_filter(all_routes, graph)
	ranked = rank_routes(filtered_routes, preference)
	display_routes(ranked, origin, destination, preference, allowed_modes)


# asks the user how they want results sorted before we run anything
def ask_preference() -> str:
	print("\n  How would you like to rank journeys?")
	print("    1. Fastest   (shortest total time)")
	print("    2. Cheapest  (lowest total price)")
	print("    3. Fewest    (least number of stops)")
	valid_choices = {
		"1": "fastest", "2": "cheapest", "3": "fewest",
		"fastest": "fastest", "cheapest": "cheapest", "fewest": "fewest",
	}
	while True:
		raw = input("\n  Your choice (1/2/3): ").strip().lower()
		preference = valid_choices.get(raw)
		if preference:
			return preference
		print("  Please enter 1, 2, or 3.")

# lets the user narrow down results to specific transport modes, or skip entirely
def ask_mode_filter(graph: TransportGraph) -> Optional[Set[str]]:
	all_modes = graph.get_all_modes()
	print("\n  Filter by transport mode? (optional)")
	print("  Press Enter to skip and show all modes.")
	print()
	for i, mode in enumerate(all_modes, 1):
		print(f"    {i}. {mode}")
	raw = input("\n  Enter number(s) separated by commas, or press Enter to skip: ").strip()
	if not raw:
		return None
	selected_modes: Set[str] = set()
	for part in raw.split(","):
		part = part.strip()
		if not part:
			continue
		if part.isdigit():
			index = int(part) - 1
			if 0 <= index < len(all_modes):
				selected_modes.add(all_modes[index])
			else:
				print(f"  Warning: '{part}' is out of range, skipping.")
		else:
			print(f"  Warning: '{part}' is not a valid number, skipping.")
	if not selected_modes:
		print("  No valid selections — showing all modes.")
		return None
	return selected_modes


def load_network_interactive() -> Tuple[Optional[TransportGraph], List[str]]:
	"""Prompt user for a CSV file and keep asking until valid or cancelled."""
	filename = input("\nEnter network file path: ").strip()

	if not filename:
		print("Error: No filename provided.")
		return None, ["Error: No filename provided."]

	while True:
		graph, messages = load_map_csv(filename)
		if graph is not None:
			return graph, messages

		for message in messages:
			print(message)

		print("Please fix the above error in the CSV file.")
		retry = input("Press Enter to retry loading the same file, or type 'cancel' to stop: ").strip().lower()
		if retry == "cancel":
			return None, ["Load cancelled by user."]


def main() -> None:
	"""Main function - defaults to data/map1.csv and starts terminal menu."""
	default_map = os.path.join("data", "map1.csv")

	print("Loading default network from 'data/map1.csv'...")
	graph, messages = load_map_csv(default_map)

	if messages:
		for message in messages:
			print(message)

	if graph is None:
		print("\nWarning: Default map failed to load.")
		print("Use option 4 to load a different network file.")
		graph = TransportGraph()

	while True:
		display_menu()
		choice = input("\nEnter choice (1-5): ").strip()

		if choice == "1":
			list_stops(graph)
		elif choice == "2":
			query_journeys(graph)
		elif choice == "3":
			show_summary(graph)
		elif choice == "4":
			new_graph, new_messages = load_network_interactive()
			for message in new_messages:
				print(message)
			if new_graph is not None and new_graph.has_stops():
				graph = new_graph
				print("\nNetwork loaded successfully!")
		elif choice == "5":
			print("\nThank you for using Smart Public Transport Advisor!")
			print("Goodbye!")
			break
		else:
			print("\nInvalid choice. Please enter a number 1-5.")


if __name__ == "__main__":
	main()
