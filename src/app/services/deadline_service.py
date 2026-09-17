from datetime import date


def _days_remaining(due_date: date, today: date) -> int:
    return (due_date - today).days


def project_progress(project) -> float:
    milestones = list(project.milestones or [])
    if not milestones:
        return 0.0
    return round(sum(1 for m in milestones if m.completed) / len(milestones) * 100, 1)


def remaining_work_days(project, deadlines) -> int:
    milestone_days = sum(1 for m in project.milestones if not m.completed)
    deadline_days = sum(d.estimated_work_days for d in deadlines if not d.completed)
    return max(milestone_days, deadline_days)


def estimate_finish(project, remaining_days: int, today: date | None = None) -> date:
    today = today or date.today()
    return today.fromordinal(today.toordinal() + max(0, remaining_days))


def build_calendar(deadlines, today: date | None = None):
    today = today or date.today()
    result = []
    for item in deadlines:
        days = _days_remaining(item.due_date, today)
        result.append({
            "id": item.id,
            "title": item.title,
            "deadline_type": item.deadline_type,
            "due_date": item.due_date,
            "completed": item.completed,
            "days_remaining": days,
            "overdue": not item.completed and days < 0,
            "alert": not item.completed and 0 <= days <= item.alert_days_before,
        })
    return result


def build_alerts(deadlines, project, today: date | None = None):
    today = today or date.today()
    alerts = []
    for item in deadlines:
        if item.completed:
            continue
        days = _days_remaining(item.due_date, today)
        if days < 0:
            severity = "critical" if days <= -7 else "high"
            message = f"{item.title} is {abs(days)} day(s) overdue."
        elif days == 0:
            severity = "critical"
            message = f"{item.title} is due today."
        elif days <= item.alert_days_before:
            severity = "high" if days <= 1 else "medium"
            message = f"{item.title} is due in {days} day(s)."
        else:
            continue
        alerts.append({"deadline_id": item.id, "title": item.title, "due_date": item.due_date, "days_remaining": days, "severity": severity, "message": message})

    project_days = _days_remaining(project.target_date, today)
    if project_days < 0:
        alerts.append({"deadline_id": 0, "title": project.name, "due_date": project.target_date, "days_remaining": project_days, "severity": "critical", "message": f"Project target date passed {abs(project_days)} day(s) ago."})
    return sorted(alerts, key=lambda a: (a["severity"] != "critical", a["days_remaining"]))


def report(project, deadlines, today: date | None = None):
    today = today or date.today()
    remaining = remaining_work_days(project, deadlines)
    estimated_finish = estimate_finish(project, remaining, today)
    predicted_delay = max(0, (estimated_finish - project.target_date).days)
    upcoming = build_calendar(deadlines, today)
    active = [d for d in deadlines if not d.completed]
    overdue = [d for d in active if d.due_date < today]
    alerts = build_alerts(deadlines, project, today)
    return {
        "project_id": project.id,
        "project_name": project.name,
        "as_of": today,
        "target_date": project.target_date,
        "project_days_remaining": _days_remaining(project.target_date, today),
        "project_overdue": project.target_date < today and bool(active),
        "completion_percent": project_progress(project),
        "remaining_work_days": remaining,
        "estimated_finish": estimated_finish,
        "predicted_delay_days": predicted_delay,
        "likely_to_meet_deadline": predicted_delay == 0,
        "active_deadlines": len(active),
        "overdue_deadlines": len(overdue),
        "upcoming_deadlines": upcoming,
        "alerts": alerts,
    }
