import re

with open('../workers/tasks.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace assignments:
# msg = get_sequence_message(...)
# msg_lead = get_sequence_message(...)
# msg_sales = get_sequence_message(...)
# opening_message = get_sequence_message(...)

content = re.sub(
    r'(msg|msg_lead|msg_sales|opening_message)\s*=\s*get_sequence_message\(',
    r'\1, \1_tpl, \1_params = get_sequence_message(',
    content
)

# We also need a send wrapper at the top of tasks.py.
# Currently it uses `from services.whatsapp import send_message`
# Let's import `send_template_message` as well.
if 'send_template_message' not in content:
    content = content.replace('from services.whatsapp import send_message',
                              'from services.whatsapp import send_message, send_template_message')

# Now replace `await send_message(phone, msg)` with the new logic, but it's hard to do cleanly with regex.
# Let's write a helper in tasks.py:
helper_func = """
from core.config import settings
async def smart_send(phone, text, template_name=None, parameters=None):
    if settings.WHATSAPP_PROVIDER in ("meta", "vobiz") and template_name:
        return await send_template_message(phone, template_name, parameters)
    else:
        return await send_message(phone, text)
"""

if 'async def smart_send' not in content:
    content = content.replace('from core.database import AsyncSessionLocal', helper_func + '\nfrom core.database import AsyncSessionLocal')

# Now replace `await send_message(lead.phone, msg)` with `await smart_send(lead.phone, msg, msg_tpl, msg_params)`
content = re.sub(
    r'await send_message\(([^,]+),\s*(msg|msg_lead|msg_sales|opening_message)\)',
    r'await smart_send(\1, \2, \2_tpl, \2_params)',
    content
)

with open('../workers/tasks.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("tasks.py refactored")
