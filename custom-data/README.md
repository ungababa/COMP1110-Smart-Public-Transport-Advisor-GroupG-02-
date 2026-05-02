# Custom Data Guide

This folder is for loading custom transport network data into the Smart Public Transport Advisor.

## File Format

Create CSV files with the following format:

```
from_stop,to_stop,duration,cost
Origin Station,Destination Station,15,5.5
Another Station,Next Station,8,3.2
```

**Columns:**
- `from_stop`: Starting station name
- `to_stop`: Ending station name  
- `duration`: Travel time in minutes (integer)
- `cost`: Fare in HKD (decimal)

## Loading Custom Data

### CLI (Command Line Interface)
1. Run `python main.py`
2. Select menu option **5** to replace the existing network with custom data
3. Or select option **6** to merge custom data with the existing network

### GUI
1. Run `python main.py --gui`
2. In the left panel, click **Replace Network** or **Merge** buttons
3. Messages appear in the status bar indicating success or errors

## Notes

- All CSV files in this folder will be loaded automatically
- Multiple CSV files can be placed here; they will all be combined
- If merging with existing data, duplicate routes are replaced with custom versions
- Station names must match exactly (case-sensitive)
- Invalid rows are silently skipped
- The mode for all custom routes is set to "Custom"

## Example

See `example.csv` for a sample file.
