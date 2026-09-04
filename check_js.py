import re

with open('frontend/app.js', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print(f"Total lines: {len(lines)}")

# Check bracket balances
brace = 0
paren = 0
bracket = 0
in_template = False
in_string = False

for i, line in enumerate(lines, 1):
    for ch in line:
        if ch == '`':
            in_template = not in_template
        elif not in_template:
            if ch == '{': brace += 1
            elif ch == '}': brace -= 1
            elif ch == '(': paren += 1
            elif ch == ')': paren -= 1
            elif ch == '[': bracket += 1
            elif ch == ']': bracket -= 1

print(f"Braces balance: {brace}")
print(f"Parens balance: {paren}")
print(f"Brackets balance: {bracket}")
print(f"In template at EOF: {in_template}")
