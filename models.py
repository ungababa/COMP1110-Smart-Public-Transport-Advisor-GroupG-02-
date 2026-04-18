from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    pass


@dataclass
class TravelOption:
	route_id: str
	mode_of_transport: str
	time_minutes: int
	price_hkd: float
	next_segment: "Segment"


class Segment:
	def __init__(self, stop_name: str):
		self.stop_name = stop_name
		self.next_options: List[TravelOption] = []

	def add_option(self, option: TravelOption) -> None:
		self.next_options.append(option)

	def __repr__(self) -> str:
		return f"Segment({self.stop_name}, {len(self.next_options)} options)"


@dataclass
class Route:
	legs: List[Tuple["Segment", TravelOption]]

	@property
	def total_time(self) -> int:
		return sum(option.time_minutes for _, option in self.legs)

	@property
	def total_price(self) -> float:
		return sum(option.price_hkd for _, option in self.legs)


class TransportGraph:
	"""Graph container that keeps one Segment object per stop name."""

	def __init__(self):
		self._segments_by_stop: Dict[str, Segment] = {}
		self.route_count = 0

	def get_or_create_segment(self, stop_name: str) -> Segment:
		segment = self._segments_by_stop.get(stop_name)
		if segment is None:
			segment = Segment(stop_name)
			self._segments_by_stop[stop_name] = segment
		return segment

	def add_connection(
		self,
		route_id: str,
		start: str,
		stop: str,
		mode_of_transport: str,
		time_minutes: int,
		price_hkd: float,
	) -> None:
		from_segment = self.get_or_create_segment(start)
		to_segment = self.get_or_create_segment(stop)

		option = TravelOption(
			route_id=route_id,
			mode_of_transport=mode_of_transport,
			time_minutes=time_minutes,
			price_hkd=price_hkd,
			next_segment=to_segment,
		)
		from_segment.add_option(option)
		self.route_count += 1

	def get_stops(self) -> List[str]:
		return sorted(self._segments_by_stop.keys())

	def get_segment(self, stop_name: str) -> Optional[Segment]:
		return self._segments_by_stop.get(stop_name)

	def has_stops(self) -> bool:
		return bool(self._segments_by_stop)

	def num_segments(self) -> int:
		return len(self._segments_by_stop)

	def average_stats(self) -> Tuple[float, float]:
		all_options: List[TravelOption] = []
		for segment in self._segments_by_stop.values():
			all_options.extend(segment.next_options)

		if not all_options:
			return 0.0, 0.0

		avg_time = sum(option.time_minutes for option in all_options) / len(all_options)
		avg_price = sum(option.price_hkd for option in all_options) / len(all_options)
		return avg_time, avg_price
	
	def get_all_modes(self) -> List[str]:
		"""Collect every unique transport mode that exists anywhere in the network."""
		modes: Set[str] = set()
		for segment in self._segments_by_stop.values():
			for option in segment.next_options:
				modes.add(option.mode_of_transport)
		return sorted(modes)