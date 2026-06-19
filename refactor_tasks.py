import re
from pathlib import Path

def refactor_tasks():
    file_path = Path("workers/tasks.py")
    content = file_path.read_text(encoding="utf-8")
    
    # Add get_project_for_lead helper at the top, just before dispatch_voice_call
    if "async def get_project_for_lead" not in content:
        helper_code = """
async def get_project_for_lead(lead, db):
    from core.models import Project
    if lead.project_key and lead.project_key != "unknown":
        result = await db.execute(select(Project).where(Project.project_key == lead.project_key))
        return result.scalars().first()
    return None

@safe_task
"""
        content = content.replace("@safe_task\nasync def dispatch_voice_call", helper_code + "async def dispatch_voice_call")
    
    # 1. replace process_message(lead, history, combined
    content = content.replace(
        "reply, extraction = await process_message(lead, history, combined",
        "reply, extraction = await process_message(lead, db, history, combined"
    )
    
    # 2. replace SEQUENCE_MESSAGES["first_touch"]
    if "SEQUENCE_MESSAGES[\"first_touch\"]" in content:
        content = content.replace(
            "opening_message = SEQUENCE_MESSAGES[\"first_touch\"].format(name=display_name)",
            "project = await get_project_for_lead(lead, db)\n        opening_message = get_sequence_message(\"first_touch\", project=project, name=display_name)"
        )
        
    # 3. replace SEQUENCE_MESSAGES["qual_nudge_24h"]
    if "SEQUENCE_MESSAGES[\"qual_nudge_24h\"]" in content:
        content = content.replace(
            "msg = SEQUENCE_MESSAGES[\"qual_nudge_24h\"].format(name=display_name)",
            "project = await get_project_for_lead(lead, db)\n        msg = get_sequence_message(\"qual_nudge_24h\", project=project, name=display_name)"
        )
        
    # 4. For every msg = get_sequence_message(..., we need to inject `project = await get_project_for_lead(lead, db)`
    # The pattern is: msg = get_sequence_message(
    # We should find `async def` functions, and if they contain `get_sequence_message(`, we prepend project fetch if `db` and `lead` exist.
    
    # Actually, a regex replace for `msg = get_sequence_message(` or `msg_lead = get_sequence_message(`
    # Let's use re.sub with a function
    
    def repl(m):
        prefix = m.group(1) # spaces before msg
        var_name = m.group(2) # msg or msg_lead or msg_sales
        return f"{prefix}project = await get_project_for_lead(lead, db)\n{prefix}{var_name} = get_sequence_message("

    # Regex to find where get_sequence_message is assigned, BUT we need to insert `project=project, ` in the arguments
    def repl2(m):
        prefix = m.group(1)
        var_name = m.group(2)
        args = m.group(3)
        # Check if project= is already there
        if "project=" in args:
            return m.group(0)
        
        return f"{prefix}project = await get_project_for_lead(lead, db)\n{prefix}{var_name} = get_sequence_message({args.split(',')[0]}, project=project, {','.join(args.split(',')[1:]) if ',' in args else ''})".replace(", )", ")")

    # Let's do a simpler string replace since all calls are somewhat standard
    # Let's find all get_sequence_message calls
    
    # Iterate over lines
    lines = content.split('\n')
    out_lines = []
    for i, line in enumerate(lines):
        if "= get_sequence_message(" in line:
            indent = line[:len(line) - len(line.lstrip())]
            if "project=" not in line:
                out_lines.append(f"{indent}project = await get_project_for_lead(lead, db)")
                
                # inject project=project after the first argument
                parts = line.split('(', 1)
                args_part = parts[1]
                arg_split = args_part.split(',', 1)
                if len(arg_split) == 1:
                    # e.g. msg = get_sequence_message("reactivation_week2")
                    new_line = parts[0] + "(" + arg_split[0].replace(')', ', project=project)')
                else:
                    new_line = parts[0] + "(" + arg_split[0] + ", project=project," + arg_split[1]
                out_lines.append(new_line)
            else:
                out_lines.append(line)
        else:
            out_lines.append(line)
            
    content = "\n".join(out_lines)

    # Clean up double project=project, if any
    content = content.replace("project=project,,", "project=project,")
    content = content.replace(", ,", ",")
    
    file_path.write_text(content, encoding="utf-8")
    print("Tasks.py refactored!")

if __name__ == "__main__":
    refactor_tasks()
