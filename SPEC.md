# Smart Public Transport Advisor - Specification

## Project Overview
- **Project Name**: Smart Public Transport Advisor
- **Type**: Text-based Python application
- **Core Functionality**: Transport network modeling with journey generation and ranking based on user preferences
- **Target Users**: Commuters, students, and transport planners

## Data Model

### Network Structure
- **Stops**: Nodes representing transport stations/stops (minimum 10)
- **Segments**: Edges connecting exactly two stops with:
  - `from_stop`: origin stop name
  - `to_stop`: destination stop name
  - `duration`: travel time in minutes (positive integer)
  - `cost`: fare in HKD (positive float/integer)

### File Format (CSV-like)
```
from_stop,to_stop,duration,cost
Central,Admiralty,15,10.5
...
```

## UI/UX Specification

### Menu Structure
```
=== Smart Public Transport Advisor ===
1. List all stops
2. Query journeys
3. Show network summary
4. Load different network file
5. Exit
```

### Journey Query Flow
1. Prompt for origin stop
2. Prompt for destination stop
3. Prompt for preference (fastest/cheapest/fewest)
4. Display top 5 ranked journeys with breakdown

### Output Format
Journey results should show:
- Journey number
- Total duration (minutes)
- Total cost (HKD)
- Number of segments
- Segment-by-segment breakdown

## Functionality Specification

### Core Features

1. **Network Loading**
   - Load from CSV-format text file
   - Validate stop names and segment data
   - Handle malformed data gracefully

2. **Stop Listing**
   - Display all available stops alphabetically

3. **Network Summary**
   - Total number of stops
   - Total number of segments
   - Average segment duration and cost

4. **Journey Query**
   - Input validation for origin/destination
   - Preference mode: fastest, cheapest, fewest
   - Generate candidate journeys using DFS with depth limit
   - Rank and display top 5

5. **Different Network Loading**
   - Allow user to specify new network file path

### Input Validation
- Unknown stops: show error, return to menu
- Same origin/destination: show error, return to menu
- Invalid preference: prompt again
- Missing/empty file: show error, return to menu
- Malformed data: skip invalid segments, continue

### Journey Generation Method
- **Algorithm**: Depth-Limited Depth-First Search (DFS)
- **Max Depth**: 6 segments (to avoid overly long routes)
- **Discovery**: Find all valid paths from origin to destination within depth limit
- **Rationale**: Simple, no external dependencies, clearly understandable

### Ranking Criteria
- **Fastest**: Sort by total duration (ascending)
- **Cheapest**: Sort by total cost (ascending)
- **Fewest Segments**: Sort by number of segments (ascending)

## Acceptance Criteria

1. Program runs without external dependencies
2. Menu displays and accepts input correctly
3. Network loads from file with validation
4. Invalid inputs are handled gracefully
5. Journey queries return relevant results
6. Results are correctly ranked by preference
7. Top 5 journeys displayed with full breakdown
8. Case studies can be executed and produce expected results

## File Structure
```
/project/
├── transport_advisor.py    # Main Python program
├── network.csv            # Sample network data
├── README.md              # Documentation
└── case_studies/          # Case study files
    ├── case1.txt
    ├── case2.txt
    └── case3.txt
```