# Smart Public Transport Advisor

**COMP1110 Computing and Data Science in Everyday Life**  
**Group G-02 — Topic B: Smart Public Transport Advisor**  
University of Hong Kong
Semester 2, 2025–2026

---

## Overview

This program models Hong Kong's public transport network as a graph of stops and segments, and helps users find journeys between any two stops. Each segment connects two stops and carries a duration (minutes) and cost (HKD). The program accepts an origin, a destination, and a preference mode — fastest, cheapest, or fewest transfers — and returns ranked candidate journeys with a full per-segment breakdown.

The implementation uses the **A\* pathfinding algorithm** guided by a geographic (haversine) heuristic for efficient search. Both a **text-based CLI** and an optional **GUI** (PyQt6 with an interactive Hong Kong map) are provided.

---

---

## Language and Requirements

**Language:** Python 3.8 or above

**Dependencies** (install once before running):

```
colorama      # coloured terminal output for the CLI
PyQt6         # required only for --gui mode
pyreadline3   # Windows readline support (optional)
```

Install all at once:

```bash
pip install -r requirements.txt
```
---

## How to Run

### CLI mode

```bash
python main.py
```

On startup the program automatically loads the full Hong Kong network from `data/mtr/` and `data/bus/`. If those files are missing or empty, it falls back to `data/Test/network.csv`. Warnings are printed for any data that could not be loaded; the program always continues.

### GUI mode

```bash
python main.py --gui
```

Opens a PyQt6 window. The network loads in the background; the A\* search also runs on a background thread so the map stays interactive. Use the form on the left to enter stops and preferences; results appear in the table on the right.

---

## File Structure

```
.
├── main.py              # CLI entry point: A* search, menus, input validation, journey display
├── files.py             # Data model (Segment, Journey, TransportNetwork) and all file loaders
├── requirements.txt     # Python dependencies
├── gui/
│   ├── __init__.py
│   ├── main_window.py   # PyQt6 main window; background A* thread so UI stays responsive
│   ├── hkmap.py         # Interactive HK map widget with stop overlay
│   ├── journey_form.py  # Origin / destination / preference input form
│   ├── results_table.py # Journey results display table
│   ├── network_map.py   # Network graph drawn over the map
│   └── widgets.py       # Shared UI helper widgets
└── data/
    ├── Hong_Kong_Dark_Map.png       # Background map image used by the GUI
    ├── mtr/
    │   ├── mtr_lines_and_stations.csv  # MTR line codes, station names, sequence numbers
    │   ├── mtr_lines_coords.csv        # Geographic coordinates for MTR line paths
    │   ├── mtr_lines_fares.csv         # Adult Octopus fares between every station pair
    │   └── mtr_station_coords.csv      # Latitude / longitude of each MTR station
    ├── bus/
    │   ├── ROUTE_BUS.xml   # Bus route definitions (journey time, full fare per route)
    │   ├── STOP_BUS.xml    # Bus stop coordinates (X/Y in WGS-84)
    │   ├── RSTOP_BUS.xml   # Stop sequences per route and direction
    │   └── FARE_BUS.xml    # Bus fare data
    └── Test/
        ├── network.csv         # Hand-crafted HK Island network — no header, simple format
        ├── network_small.csv   # Minimal 4-stop linear network for basic testing
        ├── test_small.csv      # 4-stop network in labelled-header format
        ├── map1.csv            # 35-segment Island + Kowloon network, labelled-header format
        ├── map2.csv            # 35-segment Kowloon / New Territories network, labelled-header
        ├── map3.csv            # 34-segment Tuen Ma Line network, labelled-header format
        ├── network_map1.csv    # Same coverage as map1.csv in simple (no-header) format
        ├── network_map2.csv    # Same coverage as map2.csv in simple format
        └── network_map3.csv    # Same coverage as map3.csv in simple format
```


## CLI Menu

```
============================================================
  Smart Public Transport Advisor
============================================================
  1. List all stops
  2. Query journeys
  3. Show network summary
  4. Load different network file
  5. Exit
============================================================
```

**Option 1 — List all stops**  
Displays every stop in the loaded network. Type a partial name to filter; press Enter to list all.

**Option 2 — Query journeys**  
Prompts for origin, destination, transport mode filter (optional), and preference. Returns the top ranked journeys with per-segment breakdowns (stop names, mode, duration, cost) and journey totals (total minutes, total HKD, number of legs).

**Option 3 — Show network summary**  
Prints total stops, total segments, average segment duration, and average segment cost.

**Option 4 — Load different network file**  
Enter a path to any CSV file in the format described below. The new network replaces the current one without restarting.

**Option 5 — Exit**

---

## Journey Query Workflow (Option 2)

1. **Enter origin stop** — partial name matching is supported; the program narrows to the unique match or lists candidates.
2. **Enter destination stop** — same matching logic.
3. **Select transport mode** (optional) — choose from modes in the loaded network (e.g. MTR, Bus, Tram) by number. Enter a single mode for a strict filter (every segment must match); enter multiple comma-separated numbers for a permissive filter (at least one segment must match). Press Enter to skip filtering.
4. **Select preference:**
   - `1` Fastest — minimise total travel time (includes 5-minute transfer penalty between different routes or modes)
   - `2` Cheapest — minimise total fare (MTR fares use the origin→destination lookup; bus fares use the full-route fare)
   - `3` Fewest transfers — minimise the number of legs (consecutive segments on the same route count as one leg)

The program runs A\* for the chosen optimisation, deduplicates paths, ranks them, and displays the top routes.

---

## Network File Format

Custom networks can be loaded via Option 4. Two CSV formats are accepted.

### Simple format (no header row)

```
Central,Admiralty,4,4.00
Admiralty,Wan Chai,3,4.00
```

Columns in order: `from_stop, to_stop, duration_minutes, cost_hkd`

- `duration_minutes` must be a positive integer.
- `cost_hkd` must be a non-negative decimal.

### Labelled format (with header row)

Detected automatically when the first row starts with `from_stop` (case-insensitive). Example:

```
ID,START,STOP,MODE OF TRANSPORT,TIME,PRICE (HKD)
1,Central,Admiralty,MTR (Island Line),4 mins,4.00
```

Columns are read by position: ID, from\_stop, to\_stop, mode, duration, cost.

### Rules for both formats

- Lines beginning with `#` and blank lines are skipped.
- Rows with fewer than 4 fields, non-numeric duration, or negative cost are skipped individually — the rest of the file still loads.
- A missing file or empty file produces an empty network with a printed warning; the program does not crash.

---

---

## Key Design Decisions

**A\* with haversine heuristic.** The program uses A\* with straight-line geographic distance as an admissible heuristic rather than exhaustive BFS. Speed assumption for the duration heuristic is ~50 km/h (833 m/min). For cost optimisation the heuristic is 0 (admissible lower bound). For fewest-legs it is 1.

**Transfer time penalty.** Switching between different routes or modes adds 5 minutes to the duration estimate per transfer. Consecutive segments sharing the same `route_id` and mode type are treated as a single continuous ride with no penalty.

**Fare consolidation.** For MTR and Airport Express, the fare for a multi-stop leg is looked up from `mtr_lines_fares.csv` using the leg's actual origin and destination, not the sum of hop-by-hop costs. Bus fares use the full-route fare from the XML data. Modes other than MTR/AEL always fall back to the per-segment stored cost.

**Stop aliasing.** MTR station names and nearby bus stop names differ between data sources. A union-find structure (`add_alias` / `get_canonical_stop` in `TransportNetwork`) resolves these into canonical names so A\* can plan routes that cross modes at interchange stops.

**Transport mode filter policy.** Single-mode selection = strict (every segment must be that mode). Multi-mode selection = permissive (at least one segment must match). This lets users say "MTR only" or "any route that includes bus".

---

## Limitations

- Journey optimality is not mathematically guaranteed. The A\* heuristic may miss a better route that involves backtracking away from the destination.
- The bus network is built from static XML files. Live schedule changes, service suspensions, and new routes are not reflected.
- The program does not model timetables or departure times; all durations are constant travel-time estimates with no waiting for the next service.
- Walking segments between nearby stops are not inserted automatically; they must be present in the loaded network file.
- The GUI requires PyQt6, which may need a separate installation step on some systems.

---

## GitHub Repository

https://github.com/ungababa/COMP1110-Smart-Public-Transport-Advisor-GroupG-02-

---

*COMP1110 Group G-02 — Semester 2, 2025–2026*
