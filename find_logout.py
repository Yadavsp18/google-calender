with open('static/js/main.js', 'r', encoding='utf-8') as f:
    lines = f.readlines()
    for i, line in enumerate(lines):
        if 'function logout' in line:
            start = i
            end = min(i + 20, len(lines))
            for j in range(start, end):
                print(f'{j+1}: {lines[j]}', end='')
            break