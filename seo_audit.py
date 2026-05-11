import os
import re

html_files = [f for f in os.listdir('.') if f.endswith('.html')]
results = []

for file in html_files:
    with open(file, 'r') as f:
        content = f.read()
        title = re.search(r'<title>(.*?)</title>', content)
        desc = re.search(r'<meta name="description" content="(.*?)">', content)
        results.append({
            'file': file,
            'title': title.group(1) if title else 'MISSING',
            'desc': desc.group(1) if desc else 'MISSING'
        })

print("SEO Audit Results:")
for r in results:
    print(f"File: {r['file']}")
    print(f"  Title: {r['title']}")
    print(f"  Description: {r['desc']}")
    print("-" * 20)

titles = [r['title'] for r in results if r['title'] != 'MISSING']
descriptions = [r['desc'] for r in results if r['desc'] != 'MISSING']

if len(titles) == len(set(titles)):
    print("SUCCESS: All titles are unique.")
else:
    print("WARNING: Duplicate titles found!")

if len(descriptions) == len(set(descriptions)):
    print("SUCCESS: All descriptions are unique.")
else:
    print("WARNING: Duplicate descriptions found!")
