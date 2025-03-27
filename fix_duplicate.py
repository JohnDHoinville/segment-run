#!/usr/bin/env python3

with open('backend/app/database.py', 'r') as f:
    lines = f.readlines()

# Look for duplicate __init__ methods
init_positions = []
for i, line in enumerate(lines):
    if '    def __init__' in line:
        init_positions.append(i)

# If we found more than one __init__, keep only the last complete one
fixed_lines = []
if len(init_positions) > 1:
    # Keep lines before the first __init__
    fixed_lines.extend(lines[:init_positions[0]])
    
    # Keep lines from the last __init__ onwards
    fixed_lines.extend(lines[init_positions[-1]:])
else:
    fixed_lines = lines

with open('backend/app/database.py', 'w') as f:
    f.writelines(fixed_lines)

print("Fixed duplicate __init__ method in database.py") 