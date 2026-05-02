from files import Segment, Journey

print("=" * 60)
print("Testing Consolidation for All Transport Modes")
print("=" * 60)

# Test 1: Bus consolidation (existing)
print("\nTest 1: BUS - Same route (consecutive segments)")
bus_segments = [
    Segment('Stop A', 'Stop B', 5, 6.6, mode='Bus', route_id='Route1'),
    Segment('Stop B', 'Stop C', 5, 6.6, mode='Bus', route_id='Route1'),
    Segment('Stop C', 'Stop D', 5, 6.6, mode='Bus', route_id='Route1'),
]
journey = Journey(bus_segments, {}, 'Stop A', 'Stop D')
print(f"  Segments: {len(journey.segments)}")
print(f"  Total cost: ${journey.total_cost:.2f}")
print(f"  Expected: $6.60 (single fare, not 19.80)")
print(f"  ✓ PASSED" if journey.total_cost == 6.6 else f"  ✗ FAILED")

# Test 2: MTR consolidation (new)
print("\nTest 2: MTR - Same line & direction (consecutive segments)")
mtr_segments = [
    Segment('Central', 'Admiralty', 3, 4.5, mode='MTR', route_id='Island_DT'),
    Segment('Admiralty', 'Wan Chai', 3, 4.5, mode='MTR', route_id='Island_DT'),
    Segment('Wan Chai', 'Causeway Bay', 3, 4.5, mode='MTR', route_id='Island_DT'),
]
journey = Journey(mtr_segments, {}, 'Central', 'Causeway Bay')
print(f"  Segments: {len(journey.segments)}")
print(f"  Total cost: ${journey.total_cost:.2f}")
print(f"  Expected: $4.50 (single fare, not 13.50)")
print(f"  ✓ PASSED" if journey.total_cost == 4.5 else f"  ✗ FAILED")

# Test 3: Light Rail consolidation (new)
print("\nTest 3: LIGHT RAIL - Same line & direction (consecutive segments)")
lr_segments = [
    Segment('Tuen Mun', 'Sam Shing', 4, 2.9, mode='Light Rail', route_id='505_1'),
    Segment('Sam Shing', 'Siu Lun', 4, 2.9, mode='Light Rail', route_id='505_1'),
    Segment('Siu Lun', 'On Ting', 4, 2.9, mode='Light Rail', route_id='505_1'),
]
journey = Journey(lr_segments, {}, 'Tuen Mun', 'On Ting')
print(f"  Segments: {len(journey.segments)}")
print(f"  Total cost: ${journey.total_cost:.2f}")
print(f"  Expected: $2.90 (single fare, not 8.70)")
print(f"  ✓ PASSED" if journey.total_cost == 2.9 else f"  ✗ FAILED")

# Test 4: Different routes (should charge separately)
print("\nTest 4: MTR - Different lines (should charge separately)")
mtr_segments = [
    Segment('Central', 'Admiralty', 3, 4.5, mode='MTR', route_id='Island_DT'),
    Segment('Admiralty', 'Wan Chai', 3, 5.0, mode='MTR', route_id='Tsuen_Wan_DT'),
]
journey = Journey(mtr_segments, {}, 'Central', 'Wan Chai')
print(f"  Segments: {len(journey.segments)}")
print(f"  Total cost: ${journey.total_cost:.2f}")
print(f"  Expected: $9.50 (two different lines)")
print(f"  ✓ PASSED" if journey.total_cost == 9.5 else f"  ✗ FAILED")

# Test 5: Mixed transport modes
print("\nTest 5: MIXED - Bus + MTR + Light Rail")
mixed_segments = [
    Segment('Stop A', 'Stop B', 5, 6.6, mode='Bus', route_id='Route1'),
    Segment('Stop B', 'Stop C', 5, 6.6, mode='Bus', route_id='Route1'),
    Segment('Stop C', 'Central', 5, 4.5, mode='MTR', route_id='Island_DT'),
    Segment('Central', 'Admiralty', 3, 4.5, mode='MTR', route_id='Island_DT'),
    Segment('Admiralty', 'Tuen Mun', 10, 2.9, mode='Light Rail', route_id='505_1'),
]
journey = Journey(mixed_segments, {}, 'Stop A', 'Tuen Mun')
print(f"  Segments: {len(journey.segments)}")
print(f"  Total cost: ${journey.total_cost:.2f}")
print(f"  Expected: $18.50 (6.6 for bus + 4.5 for MTR + 2.9 for Light Rail)")
print(f"  ✓ PASSED" if journey.total_cost == 18.5 else f"  ✗ FAILED")

# Test 6: Non-consecutive same route (should charge separately)
print("\nTest 6: MTR - Non-consecutive same line (should charge separately)")
mtr_segments = [
    Segment('Central', 'Admiralty', 3, 4.5, mode='MTR', route_id='Island_DT'),
    Segment('Admiralty', 'Wan Chai', 3, 5.0, mode='Bus', route_id='Route2'),
    Segment('Wan Chai', 'Causeway Bay', 3, 4.5, mode='MTR', route_id='Island_DT'),
]
journey = Journey(mtr_segments, {}, 'Central', 'Causeway Bay')
print(f"  Segments: {len(journey.segments)}")
print(f"  Total cost: ${journey.total_cost:.2f}")
print(f"  Expected: $14.00 (4.5 + 5.0 + 4.5)")
print(f"  ✓ PASSED" if journey.total_cost == 14.0 else f"  ✗ FAILED")

print("\n" + "=" * 60)
print("All consolidation tests completed!")
print("=" * 60)
