
def parse_coordinate(coord_str):
    parts = coord_str.split(",")
    return [float(p) for p in parts]

def test_parser_logic():
    # Simulate spec coming from shorthand.py
    # shorthand.py converts ; to | in 'points' field
    # Input: leader|0,0;10,10~~20,0;10,10~~0,20;10,10|...
    # Shorthand parser does: 
    # value = "0,0;10,10~~20,0;10,10~~0,20;10,10"
    # value.replace(";", "|") -> "0,0|10,10~~20,0|10,10~~0,20|10,10"
    
    spec_points = "0,0|10,10~~20,0|10,10~~0,20|10,10"
    spec = {"points": spec_points}
    
    print(f"Spec Points: {spec_points}")
    
    # Logic from drawing.py _draw_leader_unified
    leader_groups = []
    points_or_groups = spec["points"]

    if "~~" in points_or_groups:
         # Multi-arrow shorthand
        groups_str = points_or_groups
        print("Detected ~~")
        
        for group_str in groups_str.split("~~"):
            group_str = group_str.strip()
            print(f"Processing group: {group_str}")
            if group_str:
                # Handle both | and ; separators for robustness
                # Shorthand might have converted ; to | already
                clean_str = group_str.replace(";", "|")
                group_points = [
                    parse_coordinate(p.strip()) for p in clean_str.split("|") if p.strip()
                ]
                
                print(f"  -> Points: {group_points}")
                if group_points:
                    leader_groups.append(group_points)
    else:
        print("No ~~ detected")
        
    print(f"Total Groups: {len(leader_groups)}")

if __name__ == "__main__":
    test_parser_logic()
