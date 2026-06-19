import re
from sqlalchemy import select
from core.models import Project

def normalize(text: str) -> str:
    """Normalize text by lowercasing and removing spaces, dashes, numbers, and version tags."""
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r'[_\-\s]+', '', text)  # remove separators
    text = re.sub(r'\d{4}', '', text)     # remove years like 2026
    text = re.sub(r'v\d+', '', text)      # remove version tags like v2
    return text

async def match_project(source_ad: str, db) -> str:
    """
    Returns project_key, or "unknown" if no match found.
    """
    if not source_ad:
        return "unknown"
    
    result = await db.execute(select(Project).where(Project.active == True))
    projects = result.scalars().all()
    
    normalized_source = normalize(source_ad)
    
    # Step 1: exact match
    for project in projects:
        if normalize(project.project_key) == normalized_source:
            return project.project_key
            
    # Step 2: substring match (project_key inside source_ad)
    for project in projects:
        if normalize(project.project_key) in normalized_source:
            return project.project_key
            
    # Step 3: no match
    return "unknown"
