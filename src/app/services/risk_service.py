from datetime import date


def calculate_risk(project):
    today = date.today()
    milestones = list(project.milestones)
    incomplete = [m for m in milestones if not m.completed]
    overdue = [m for m in incomplete if m.due_date < today]
    days_to_deadline = (project.target_date - today).days

    if overdue or days_to_deadline < 0:
        level = "High"
    elif days_to_deadline <= 7 and incomplete:
        level = "Medium"
    else:
        level = "Low"

    return {
        "project_id": project.id,
        "risk_level": level,
        "days_to_deadline": days_to_deadline,
        "overdue_milestones": len(overdue),
        "incomplete_milestones": len(incomplete),
        "recommendation": (
            "Address overdue milestones immediately."
            if overdue else
            "Prioritize the remaining milestones before the deadline."
            if incomplete and days_to_deadline <= 7 else
            "Schedule is currently on track."
        ),
    }
