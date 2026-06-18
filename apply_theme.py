import os
import re

DIR = 'frontend/src'

replacements = [
    # Backgrounds
    (r'bg-\[\#09090b\](/\d+)?', r'bg-background'),
    (r'bg-\[\#0f0f13\]', r'bg-card'),
    (r'bg-\[\#1f2937\]', r'bg-card'),
    (r'bg-\[\#111827\]', r'bg-input'),
    (r'bg-\[\#18181b\]', r'bg-card'),
    
    # Borders
    (r'border-white/\[0\.05\]', r'border-border'),
    (r'border-white/\[0\.1\]', r'border-border'),
    (r'border-white/\[0\.08\]', r'border-border'),
    (r'border-gray-800', r'border-border'),
    (r'border-gray-700', r'border-border'),

    # Text Colors
    # Only replace text-white and text-gray-100 if they are not inside buttons or colored backgrounds. This is tricky.
    # A safer bet is to use standard dark: modifier for text where needed, but we can map text-white to text-foreground.
    (r'text-white', r'text-foreground'),
    (r'text-gray-100', r'text-foreground'),
    (r'text-gray-200', r'text-foreground-muted'),
    (r'text-gray-300', r'text-foreground-muted'),
    (r'text-gray-400', r'text-muted'),
    (r'text-gray-500', r'text-muted'),
    
    # Glass backgrounds
    (r'bg-white/\[0\.02\]', r'bg-card-hover'),
    (r'bg-white/\[0\.03\]', r'bg-card-hover'),
    (r'bg-white/\[0\.04\]', r'bg-card-hover'),
]

def process_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    new_content = content
    for pattern, repl in replacements:
        new_content = re.sub(pattern, repl, new_content)
        
    # Manual fixups for buttons where text-white is needed
    new_content = new_content.replace('bg-emerald-600 text-foreground', 'bg-emerald-600 text-white')
    new_content = new_content.replace('bg-blue-600 text-foreground', 'bg-blue-600 text-white')
    new_content = new_content.replace('bg-indigo-600 text-foreground', 'bg-indigo-600 text-white')
    new_content = new_content.replace('bg-red-500 text-foreground', 'bg-red-500 text-white')

    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Updated {filepath}")

for root, _, files in os.walk(DIR):
    for file in files:
        if file.endswith('.jsx'):
            process_file(os.path.join(root, file))
