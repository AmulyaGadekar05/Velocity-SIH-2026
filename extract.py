import os

with open('index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

start_idx = -1
end_idx = -1
for i, line in enumerate(lines):
    if '<style>' in line.lower() and start_idx == -1:
        start_idx = i
    if '</style>' in line.lower() and start_idx != -1:
        end_idx = i
        break

if start_idx != -1 and end_idx != -1:
    css_content = ''.join(lines[start_idx+1:end_idx])
    with open('style.css', 'w', encoding='utf-8') as f:
        f.write(css_content)
    
    new_html = lines[:start_idx] + ['  <link rel="stylesheet" href="/style.css">\n'] + lines[end_idx+1:]
    with open('index.html', 'w', encoding='utf-8') as f:
        f.writelines(new_html)
    print('CSS extracted to style.css and index.html updated.')
else:
    print('Could not find style block')
