def calculate_progress(project):
    milestones = list(project.milestones)
    total = len(milestones)
    completed = sum(1 for milestone in milestones if milestone.completed)
    percentage = round((completed / total) * 100, 2) if total else 0.0
    return {"project_id": project.id, "total_milestones": total, "completed_milestones": completed, "progress_percent": percentage}
