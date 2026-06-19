import re
from pathlib import Path

def refactor_tasks():
    file_path = Path("workers/tasks.py")
    content = file_path.read_text(encoding="utf-8")
    
    # We will look for lines like: msg = get_sequence_message("...", project=project...)
    lines = content.split('\n')
    out_lines = []
    
    for i, line in enumerate(lines):
        if "= get_sequence_message(" in line:
            # Check if this line is preceded by project fetch
            # Let's just add the context fetch right before it if we are inside a task.
            # But wait, some have `context = await get_campaign_context_dict(db)` already. We should remove those old ones.
            indent = line[:len(line) - len(line.lstrip())]
            
            # Remove old context lines
            if i > 0 and "context = await get_campaign_context_dict" in out_lines[-1]:
                out_lines.pop()
            
            out_lines.append(f"{indent}context = await get_campaign_context_dict(db, project_key=project.project_key if project else None)")
            
            # Now we add **context and pain_point=lead.pain_point to the get_sequence_message call
            # Parse the args
            parts = line.split('get_sequence_message(')
            prefix = parts[0]
            args_str = parts[1]
            
            # Remove trailing closing parenthesis
            args_str = args_str.rstrip()
            if args_str.endswith(')'):
                args_str = args_str[:-1]
                
            # If "**context" is already there, remove it to avoid duplication
            args_str = args_str.replace(', **context', '').replace('**context,', '').replace('**context', '')
            args_str = args_str.replace('pain_point=lead.pain_point or "your current challenges"', '')
            args_str = args_str.replace('pain_point=lead.pain_point', '')
            
            # Clean up commas
            args_str = args_str.replace(', ,', ',').rstrip(',')
            
            new_line = f"{prefix}get_sequence_message({args_str}, pain_point=lead.pain_point, **context)"
            out_lines.append(new_line)
        else:
            out_lines.append(line)
            
    # Remove any stray old context lines
    final_lines = []
    for line in out_lines:
        if "context = await get_campaign_context_dict(db)" in line and "project_key=project.project_key" not in line:
            continue
        final_lines.append(line)
        
    file_path.write_text("\n".join(final_lines), encoding="utf-8")
    print("Tasks refactored with context injection!")

if __name__ == "__main__":
    refactor_tasks()
