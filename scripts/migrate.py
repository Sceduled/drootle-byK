import re
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from client_config import SEQUENCE_MESSAGES

new_content = 'SEQUENCE_TEMPLATES = {\n'

for key, text in SEQUENCE_MESSAGES.items():
    vars_found = re.findall(r'\{([^\}]+)\}', text)
    unique_vars = []
    for v in vars_found:
        if v not in unique_vars:
            unique_vars.append(v)
            
    # Max length of template name in Meta is 512, usually much shorter and lowercase
    template_name = f"{key}_optout".replace('-', '_').lower()
    escaped_text = text.replace('"', '\\"').replace('\n', ' ')
    
    new_content += f'    "{key}": {{\n'
    new_content += f'        "template_name": "{template_name}",\n'
    new_content += f'        "variables": {unique_vars},\n'
    new_content += f'        "fallback_text": "{escaped_text}"\n'
    new_content += f'    }},\n'

new_content += '}\n'

with open('../client_config.py', 'r', encoding='utf-8') as f:
    orig = f.read()

orig = re.sub(r'SEQUENCE_MESSAGES = \{.*?\}\n', new_content, orig, flags=re.DOTALL)

with open('../client_config.py', 'w', encoding='utf-8') as f:
    f.write(orig)

print('Migration successful')
