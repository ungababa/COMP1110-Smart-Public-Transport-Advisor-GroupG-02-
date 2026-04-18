# Smart Public Transport Advisor

A text-based Python program that models a public transport network, generates candidate journeys between stops, and ranks them based on user preferences.

## Table of Contents
- [Overview](#overview)
- [Requirements](#requirements)
- [Quick Start](#quick-start)
- [Data Source](#data-source)
- [Menu Options](#menu-options)
- [Journey Generation Method](#journey-generation-method)
- [Case Studies](#case-studies)
- [Running Case Studies](#running-case-studies)
- [Error Handling](#error-handling)

## Overview

This program simulates a public transport network with:
- **Stops**: Transport stations (nodes) - 96 MTR stations
- **Segments**: Routes between stops (edges) with duration and cost

Users can query journeys between any two stops, and the program will find all valid routes within a depth limit, then rank them according to their preference (fastest, cheapest, or fewest segments).

## Requirements

- Python 3.6+ (no external libraries required)
- Standard library only (os, sys, typing)
- Data files: `mtr_lines_and_stations.csv` and `mtr_lines_fares.csv`

## Quick Start

1. Ensure all CSV files are in the same directory as `transport_advisor.py`
2. Run the program:
   ```bash
   python transport_advisor.py
   ```
3. Follow the menu prompts to explore the network

For batch testing with case studies:
```bash
python transport_advisor.py --batch
```

## Data Source

The program loads network data from official MTR data files:
- `mtr_lines_and_stations.csv` - Station information and sequences
- `mtr_lines_fares.csv` - Fare data between stations

The network includes:
- **96 stops** (MTR stations)
- **440+ segments** (bidirectional connections)
- Real fares from MTR official data
- Typical duration: 3 minutes per segment
```

- `from_stop`: Name of the origin stop
- `to_stop`: Name of the destination stop
- `duration`: Travel time in minutes (positive integer)
- `cost`: Fare in HKD (positive number)

### Example

```csv
Central,Admiralty,15,10.5
Central,Mong Kok,8,8.5
Mong Kok,Yau Ma Tei,5,5.5
```

### Sample Network (network.csv)

The provided sample network includes:
- **24 stops** covering various Hong Kong MTR stations
- **47+ segments** including multiple lines and interchange connections
- Realistic travel times and fares

## Menu Options

### 1. List all stops
Displays all available stops in alphabetical order.

### 2. Query journeys
Prompts for:
1. **Origin stop** - Starting location
2. **Destination stop** - Ending location
3. **Preference** - Choose from:
   - Fastest (shortest total time)
   - Cheapest (lowest total cost)
   - Fewest segments (simplest route)

Then displays the top 5 ranked journeys with full breakdown.

### 3. Show network summary
Displays:
- Total number of stops
- Total number of segments
- Average segment duration
- Average segment cost

### 4. Load different network file
Allows loading an alternative network file (CSV format).

### 5. Exit
Exits the program.

## Journey Generation Method

### Algorithm: Depth-Limited Depth-First Search (DFS)

The program uses **depth-limited DFS** to generate candidate journeys:

1. **Starting point**: Begin at the origin stop
2. **Exploration**: Recursively follow each outgoing segment
3. **Depth limit**: Maximum of 6 segments per journey (prevents excessively long routes)
4. **Cycle prevention**: Don't revisit stops already in the current path
5. **Termination**: When destination is reached or depth limit is hit

### Why This Method?

- **Simple**: Easy to understand and explain
- **No dependencies**: Uses only Python standard library
- **Sufficient**: Finds enough alternative routes for ranking
- **Configurable**: Max depth can be adjusted in the code (default: 6)

### Ranking

After generating journeys, they are sorted according to user preference:
- **Fastest**: Sort by total duration (ascending), then cost, then segments
- **Cheapest**: Sort by total cost (ascending), then duration, then segments
- **Fewest**: Sort by number of segments (ascending), then duration, then cost

The top 5 results are displayed.

## Case Studies

### Case 1: Budget Commuter
**Scenario**: A cost-conscious commuter traveling from Central to Sha Tin
- **Origin**: Central
- **Destination**: Sha Tin
- **Preference**: Cheapest
- **Expected**: Route with lowest total cost

### Case 2: Last-Minute Student
**Scenario**: A student running late for class, traveling from Kowloon Tong to Causeway Bay
- **Origin**: Kowloon Tong
- **Destination**: Causeway Bay
- **Preference**: Fastest
- **Expected**: Route with shortest total time

### Case 3: Transfer-Averse Traveler
**Scenario**: A traveler who prefers fewer transfers, going from Tuen Mun to Tsz Wan Shan
- **Origin**: Tuen Mun
- **Destination**: Tsz Wan Shan
- **Preference**: Fewest segments
- **Expected**: Route with minimum number of stops/segments

### Case 4: Morning Commuter
**Scenario**: A commuter in a rush from Prince Edward to Ocean Park
- **Origin**: Prince Edward
- **Destination**: Ocean Park
- **Preference**: Fastest
- **Expected**: Quickest route possible

## Running Case Studies

### Interactive Mode
Run the program normally and select option 2 (Query journeys), then enter:
- Origin: (as specified in case)
- Destination: (as specified in case)
- Preference: (as specified in case)

### Batch Mode
Run with `--batch` flag to automatically run all case studies:
```bash
python transport_advisor.py --batch
```

This outputs results for all 4 case studies in sequence.

## Error Handling

The program handles various error conditions:

| Error Type | Handling |
|------------|----------|
| File not found | Display error message, return to menu |
| Empty file | Display error, return to menu |
| Malformed data | Skip invalid lines, show warnings |
| Unknown stop | Display error, return to menu |
| Same origin/destination | Display error, return to menu |
| Invalid preference | Prompt again until valid |
| No journeys found | Display "no journeys found" message |

## Code Structure

```
transport_advisor.py
├── Data Classes
│   ├── Segment      # Single route segment
│   ├── Journey      # Complete route
│   └── TransportNetwork  # Full network
├── I/O Functions
│   └── load_network # Load CSV file
├── Journey Generation
│   └── generate_journeys  # DFS algorithm
├── Ranking
│   └── rank_journeys      # Sort by preference
├── Display Functions
│   ├── display_menu       # Show menu
│   ├── list_stops        # List all stops
│   ├── show_summary      # Network stats
│   └── display_journeys  # Show results
├── Validation
│   ├── validate_stops     # Check origin/destination
│   └── get_preference    # Get valid preference
└── Main
    ├── main()            # Interactive mode
    └── main_batch_test() # Batch case studies
```

## Customization

To adjust the maximum journey depth, modify line 192 in `transport_advisor.py`:

```python
def generate_journeys(..., max_depth: int = 6):
```

Increase to find more routes (may slow down), decrease for faster results.

## License

This is a COMP1110 group project for educational purposes.