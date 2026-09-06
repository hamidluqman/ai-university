import os
import re

# Configure your project paths here
PROJECT_ROOT = "."  # Change to your Django project root directory if needed
TEMPLATES_DIR = os.path.join(PROJECT_ROOT, "templates")  # Or wherever your templates live

def scan_project():
    all_templates = set()
    referenced_templates = set()

    # 1. Gather all .html template files
    for root, dirs, files in os.walk(PROJECT_ROOT):
        # Skip virtual environments or git folders
        if any(p in root for p in ['.venv', 'venv', '.git', '__pycache__']):
            continue
        for file in files:
            if file.endswith('.html'):
                rel_path = os.path.relpath(os.path.join(root, file), PROJECT_ROOT)
                # Normalize path separators for cross-platform matching
                all_templates.add(rel_path.replace(os.sep, '/'))

    # 2. Search all python, html, and text files for template references
    patterns = [
        r"render\s*\(\s*[^,\)]+,\s*['\"]([^'\"]+\.html)['\"]",  # render(request, 'path/to/template.html')
        r"extends\s+['\"]([^'\"]+\.html)['\"]",               # {% extends 'layout.html' %}
        r"include\s+['\"]([^'\"]+\.html)['\"]",               # {% include 'partials/card.html' %}
        r"TemplateResponse\s*\([^,\)]+,\s*['\"]([^'\"]+\.html)['\"]",
    ]

    for root, dirs, files in os.walk(PROJECT_ROOT):
        if any(p in root for p in ['.venv', 'venv', '.git', '__pycache__']):
            continue
        for file in files:
            if file.endswith(('.py', '.html', '.txt')) and file != os.path.basename(__file__):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        for pattern in patterns:
                            matches = re.findall(pattern, content)
                            for match in matches:
                                referenced_templates.add(match)
                except Exception:
                    pass

    # 3. Match and categorize
    linked = []
    unlinked = []

    for template in sorted(all_templates):
        # Check if the template name matches any reference (exact or ending match)
        is_referenced = any(template.endswith(ref) or ref.endswith(template) for ref in referenced_templates)
        
        # Base templates like 'base.html' might only be extended, so check explicitly
        if is_referenced:
            linked.append(template)
        else:
            unlinked.append(template)

    print("=== LINKED / USED TEMPLATES ===")
    for t in linked:
        print(f"  [✓] {t}")

    print("\n=== UNLINKED / POTENTIALLY ORPHANED TEMPLATES ===")
    for t in unlinked:
        print(f"  [?] {t}")

if __name__ == "__main__":
    scan_project()