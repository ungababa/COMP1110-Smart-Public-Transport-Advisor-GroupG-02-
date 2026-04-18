# sorting and filtering logic for routes — no printing or input in here

from __future__ import annotations
from typing import List, Optional, Set, Tuple
from models import Route, TransportGraph


def rank_routes(routes: List[Route], preference: str) -> List[Route]:
    # sort by what the user picked, tiebreak is always: price then fewest legs
    if preference == "fastest":
        key = lambda r: (r.total_time, r.total_price, len(r.legs))
    elif preference == "cheapest":
        key = lambda r: (r.total_price, r.total_time, len(r.legs))
    elif preference == "fewest":
        key = lambda r: (len(r.legs), r.total_time, r.total_price)
    else:
        return routes[:5]  # shouldn't happen, but don't crash

    return sorted(routes, key=key)[:5]


def filter_by_mode(routes: List[Route], allowed_modes: Set[str]) -> List[Route]:
    # every leg in the route must use one of the selected modes, no exceptions

    def all_legs_allowed(route: Route) -> bool:
        for _, option in route.legs:
            if option.mode_of_transport not in allowed_modes:
                return False
        return True

    return [route for route in routes if all_legs_allowed(route)]


def retry_mode_filter(
    routes: List[Route], graph: TransportGraph
) -> Tuple[List[Route], Optional[Set[str]]]:
    # keep asking until the filter actually returns something (or they skip it)
    from new_main import ask_mode_filter  # imported here to avoid circular import

    while True:
        allowed_modes = ask_mode_filter(graph)

        if allowed_modes is None:
            return routes, None  # user skipped, give back everything

        filtered = filter_by_mode(routes, allowed_modes)

        if filtered:
            return filtered, allowed_modes

        mode_list = ", ".join(sorted(allowed_modes))
        print(f"\n  No routes found using only: {mode_list}")
        print("  Please try a different combination.")