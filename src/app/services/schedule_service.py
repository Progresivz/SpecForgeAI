from datetime import date, timedelta


def estimate_schedule(project):
    today = date.today()
    incomplete = [m for m in project.milestones if not m.completed]
    completed = len(project.milestones) - len(incomplete)

    if not incomplete:
        estimated_finish = today
    elif completed:
        durations = [
            (m.due_date - project.start_date).days
            for m in project.milestones if m.completed
        ]
        avg_duration = max(1, round(sum(durations) / len(durations))) if durations else 7
        estimated_finish = today + timedelta(days=avg_duration * len(incomplete))
    else:
        estimated_finish = max(m.due_date for m in incomplete)

    return {
        "project_id": project.id,
        "estimated_finish": estimated_finish,
        "target_date": project.target_date,
        "likely_to_meet_deadline": estimated_finish <= project.target_date,
    }
