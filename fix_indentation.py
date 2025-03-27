#!/usr/bin/env python3

with open('backend/app/database.py', 'r') as f:
    lines = f.readlines()

with open('backend/app/database.py', 'w') as f:
    for i, line in enumerate(lines):
        # Fix the indentation issue at line 46
        if i == 45 and line.strip() == "self.init_db()":
            f.write("        self.init_db()\n")
        else:
            f.write(line)

print("Fixed indentation in database.py") 