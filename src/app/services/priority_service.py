from datetime import date


def calculate_priorities(project):
    today = date.today()
    incomplete = [m for m in project.milestones if not m.completed]
    incomplete.sort(key=lambda m: (m.due_date >= today, m.due_date))

    priorities = []
    for milestone in incomplete[:5]:
        days = (milestone.due_date - today).days
        priorities.append({
            "milestone_id": milestone.id,
            "title": milestone.title,
            "due_date": milestone.due_date,
            "days_remaining": days,
            "priority": "Critical" if days < 0 else "High" if days <= 3 else "Medium",
        })
    return {"project_id": project.id, "priorities": priorities}
