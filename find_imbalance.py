with open('frontend/app.js', 'r', encoding='utf-8') as f:
    lines = f.readlines()

brace = 0
in_template = False

for i, line in enumerate(lines, 1):
    for ch in line:
        if ch == '`':
            in_template = not in_template
        elif not in_template:
            if ch == '{': brace += 1
            elif ch == '}': brace -= 1
    if i % 100 == 0 or i == len(lines):
        print(f"Line {i}: brace balance = {brace}")
