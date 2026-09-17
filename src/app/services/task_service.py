from collections import defaultdict
from datetime import date, timedelta

from app.crud.task import create_task
from app.models.task import DevelopmentTask
from app.schemas.task import DevelopmentTaskCreate


def _priority_rank(value: str) -> int:
    return {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(value, 2)


def _candidate_tasks(project):
    tasks = []
    for req in project.requirements or []:
        tasks.append({"title": f"Implement: {req.title}", "description": req.description, "task_type": "development", "priority": req.priority if req.priority in {"low", "medium", "high", "critical"} else "medium", "requirement_id": req.id, "estimate_hours": 8})
        for criterion in req.acceptance_criteria or []:
            tasks.append({"title": f"Test: {req.title} — acceptance criterion", "description": criterion.criterion, "task_type": "testing", "priority": req.priority if req.priority in {"low", "medium", "high", "critical"} else "medium", "requirement_id": req.id, "estimate_hours": 3})
    for story in project.user_stories or []:
        tasks.append({"title": f"Deliver story: {story.title}", "description": f"As a {story.as_a}, {story.i_want}, so that {story.so_that}.", "task_type": "development", "priority": story.priority if story.priority in {"low", "medium", "high", "critical"} else "medium", "user_story_id": story.id, "estimate_hours": 8})
    for item in project.maintenance_items or []:
        priority = item.priority if item.priority in {"low", "medium", "high", "critical"} else ("critical" if item.priority == "urgent" else "medium")
        tasks.append({"title": f"Resolve: {item.title}", "description": item.description, "task_type": "maintenance", "priority": priority, "maintenance_item_id": item.id, "estimate_hours": 6})
    for milestone in project.milestones or []:
        if not milestone.completed:
            tasks.append({"title": f"Complete milestone: {milestone.title}", "description": milestone.description, "task_type": "development", "priority": "high", "milestone_id": milestone.id, "due_date": milestone.due_date, "estimate_hours": 8})
    return tasks


def generate_execution_plan(project, existing_tasks=None, today=None):
    today = today or date.today()
    existing_tasks = list(existing_tasks or [])
    existing_titles = {t.title.lower() for t in existing_tasks}
    candidates = [x for x in _candidate_tasks(project) if x["title"].lower() not in existing_titles]
    candidates.sort(key=lambda x: (_priority_rank(x["priority"]), x.get("due_date") or project.target_date, x["title"].lower()))
    return candidates


def task_plan(project, tasks, today=None):
    today = today or date.today()
    tasks = list(tasks)
    completed = [t for t in tasks if t.completed or t.status == "done"]
    blocked = [t for t in tasks if t.status == "blocked"]
    remaining = [t for t in tasks if t not in completed]
    estimate_total = sum(t.estimate_hours or 0 for t in tasks)
    remaining_hours = sum(t.estimate_hours or 0 for t in remaining)

    # Longest dependency chain; dependency cycles are ignored safely.
    by_id = {t.id: t for t in tasks}
    memo = {}
    visiting = set()
    def path_hours(task):
        if task.id in memo:
            return memo[task.id]
        if task.id in visiting:
            return task.estimate_hours or 0
        visiting.add(task.id)
        parent = by_id.get(task.depends_on_task_id)
        value = (task.estimate_hours or 0) + (path_hours(parent) if parent else 0)
        visiting.discard(task.id)
        memo[task.id] = value
        return value
    critical = max((path_hours(t) for t in remaining), default=0)

    recommendations = sorted(remaining, key=lambda t: (_priority_rank(t.priority), t.due_date or project.target_date, t.id))[:10]
    deps = []
    for t in tasks:
        if t.depends_on_task_id and t.depends_on_task_id in by_id:
            parent = by_id[t.depends_on_task_id]
            deps.append({"task_id": t.id, "task_key": t.task_key, "title": t.title, "status": t.status})
    return {
        "project_id": project.id, "project_name": project.name, "generated_at": today,
        "total_tasks": len(tasks), "completed_tasks": len(completed), "blocked_tasks": len(blocked),
        "total_estimate_hours": estimate_total, "remaining_estimate_hours": remaining_hours,
        "critical_path_hours": critical, "recommended_tasks": recommendations, "dependencies": deps,
    }


def auto_schedule(project, tasks, today=None):
    today = today or date.today()
    active = [t for t in tasks if not t.completed and t.status not in {"cancelled", "done"}]
    active.sort(key=lambda t: (_priority_rank(t.priority), t.due_date or project.target_date, t.id))
    cursor = today
    changed = []
    for task in active:
        if task.due_date is None:
            hours = task.estimate_hours or 8
            days = max(1, (hours + 7) // 8)
            task.due_date = cursor + timedelta(days=days - 1)
            cursor = task.due_date + timedelta(days=1)
            changed.append(task)
        else:
            cursor = max(cursor, task.due_date + timedelta(days=1))
    return changed
