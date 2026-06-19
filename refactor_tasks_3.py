import re
from pathlib import Path

def refactor():
    content = Path('workers/tasks.py').read_text('utf-8')
    
    # 1. First, we need to inject the context fetching right after project fetching
    # Find all `project = await get_project_for_lead(lead, db)`
    
    lines = content.split('\n')
    out_lines = []
    for line in lines:
        out_lines.append(line)
        if "project = await get_project_for_lead(lead, db)" in line:
            indent = line[:len(line) - len(line.lstrip())]
            out_lines.append(f"{indent}context = await get_campaign_context_dict(db, project_key=project.project_key if project else None)")
            
    content = "\n".join(out_lines)
    
    # 2. Now find `get_sequence_message(` and add `pain_point=lead.pain_point, **context`
    # We can use regex to find `get_sequence_message(` and its closing `)`
    # Since we know `get_sequence_message` might span multiple lines, we use DOTALL
    def repl(m):
        inner = m.group(1)
        # remove existing **context
        inner = re.sub(r',\s*\*\*context', '', inner)
        # remove existing pain_point
        inner = re.sub(r',\s*pain_point=lead\.pain_point(?: or "[^"]*")?', '', inner)
        return f"get_sequence_message({inner}, pain_point=lead.pain_point, **context)"
    
    content = re.sub(r'get_sequence_message\((.*?)\)', repl, content, flags=re.DOTALL)
    
    # Now we must clean up any double fetch of context in dnp_message_2
    # Check if there are lines with `context = await get_campaign_context_dict(db)` directly
    lines = content.split('\n')
    final_lines = []
    for i, line in enumerate(lines):
        if "context = await get_campaign_context_dict(db)" in line and "project_key" not in line:
            continue
        final_lines.append(line)
        
    Path('workers/tasks.py').write_text("\n".join(final_lines), 'utf-8')
    print("Done")

if __name__ == "__main__":
    refactor()
