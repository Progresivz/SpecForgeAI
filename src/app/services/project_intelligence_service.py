from __future__ import annotations
from datetime import date

from app.services.deadline_service import report as deadline_report
from app.services.git_service import GitError, risk as git_risk, status as git_status
from app.services.priority_service import calculate_priorities
from app.services.progress_service import calculate_progress
from app.services.risk_service import calculate_risk
from app.services.schedule_service import estimate_schedule
from app.services.task_service import task_plan


def _counts(project):
    reqs = list(project.requirements or [])
    stories = list(project.user_stories or [])
    maint = list(project.maintenance_items or [])
    tasks = list(project.development_tasks or [])
    deadlines = list(project.deadlines or [])
    milestones = list(project.milestones or [])
    return {
        "requirements": len(reqs),
        "user_stories": len(stories),
        "milestones": len(milestones),
        "milestones_completed": sum(m.completed for m in milestones),
        "maintenance_open": sum(1 for m in maint if m.status not in {"resolved", "closed", "done", "cancelled"}),
        "tasks": len(tasks),
        "tasks_completed": sum(1 for t in tasks if t.completed or t.status == "done"),
        "tasks_blocked": sum(1 for t in tasks if t.status == "blocked"),
        "deadlines_active": sum(1 for d in deadlines if not d.completed),
        "deadlines_overdue": sum(1 for d in deadlines if not d.completed and d.due_date < date.today()),
        "knowledge_entries": len(project.knowledge_entries or []),
        "ai_artifacts": len(project.ai_artifacts or []),
    }


def _requirements_coverage(project):
    reqs = list(project.requirements or [])
    if not reqs:
        return {"total": 0, "covered": 0, "coverage_percent": 0.0}
    tasks = list(project.development_tasks or [])
    covered_ids = {t.requirement_id for t in tasks if t.requirement_id is not None}
    covered = sum(1 for r in reqs if r.id in covered_ids)
    return {"total": len(reqs), "covered": covered, "coverage_percent": round(covered / len(reqs) * 100, 1)}


def _maintenance_health(project):
    items = list(project.maintenance_items or [])
    high = [x for x in items if x.priority in {"critical", "high", "urgent"} and x.status not in {"resolved", "closed", "done", "cancelled"}]
    security = [x for x in items if x.item_type == "security" and x.status not in {"resolved", "closed", "done", "cancelled"}]
    return {"open": sum(x.status not in {"resolved", "closed", "done", "cancelled"} for x in items), "high_priority_open": len(high), "security_open": len(security)}


def _recommendations(project, progress, risk, schedule, deadlines, tasks, git):
    recs = []
    if risk["risk_level"] == "High": recs.append({"priority": "critical", "area": "schedule", "message": "Address overdue milestones and deadline risk before starting lower-priority work."})
    if deadlines["predicted_delay_days"] > 0:
        recs.append({
        "priority": "high",
        "area": "deadlines",
        "message": (
            f"Estimated completion is {deadlines['predicted_delay_days']} "
            "day(s) beyond the target date; reduce remaining scope or "
            "increase execution capacity."
        ),
    })
    if tasks["blocked_tasks"]: recs.append({"priority": "high", "area": "tasks", "message": f"Resolve {tasks['blocked_tasks']} blocked development task(s)."})
    if tasks["remaining_estimate_hours"] > 0 and tasks["recommended_tasks"]:
        recs.append({"priority": "medium", "area": "execution", "message": f"Start with: {tasks['recommended_tasks'][0]['title']}."})
    if git and git.get("level") == "high": recs.append({"priority": "high", "area": "git", "message": "Review high-risk Git changes before merging or releasing."})
    mh = _maintenance_health(project)
    if mh["security_open"]: recs.append({"priority": "high", "area": "security", "message": f"Review {mh['security_open']} open security maintenance item(s)."})
    if progress["progress_percent"] == 0 and project.milestones: recs.append({"priority": "medium", "area": "progress", "message": "No milestones are complete yet; establish the first completed milestone to create measurable progress."})
    if not recs: recs.append({"priority": "low", "area": "general", "message": "Project is currently on track. Continue with the recommended execution tasks."})
    return recs


def build_intelligence(project):
    progress = calculate_progress(project)
    schedule = estimate_schedule(project)
    risk = calculate_risk(project)

    deadlines = deadline_report(
        project,
        list(project.deadlines or []),
    )

    task_data = task_plan(
        project,
        list(project.development_tasks or []),
    )

    git = None

    if project.git_repository and project.git_repository.enabled:
        try:
            gs = git_status(project.git_repository.repo_path)
            gr = git_risk(project.git_repository.repo_path)

            git = {
                "available": True,
                "branch": gs.get("branch"),
                "clean": gs.get("clean"),
                "changed_files": len(gs.get("changes", [])),
                "risk": gr,
            }

        except GitError as exc:
            git = {
                "available": False,
                "error": str(exc),
            }

    else:
        git = {
            "available": False,
            "error": "Git monitoring is not configured or is disabled.",
        }

    counts = _counts(project)

    task_summary = {
        "total_tasks": task_data["total_tasks"],
        "completed_tasks": task_data["completed_tasks"],
        "blocked_tasks": task_data["blocked_tasks"],
        "total_estimate_hours": task_data["total_estimate_hours"],
        "remaining_estimate_hours": task_data["remaining_estimate_hours"],
        "critical_path_hours": task_data["critical_path_hours"],
        "recommended_tasks": [
            {
                "id": t.id,
                "task_key": t.task_key,
                "title": t.title,
                "priority": t.priority,
                "status": t.status,
            }
            for t in task_data["recommended_tasks"]
        ],
    }

    return {
        "project": {
            "id": project.id,
            "name": project.name,
            "status": project.status,
            "start_date": project.start_date,
            "target_date": project.target_date,
        },
        "health": {
            "risk_level": risk["risk_level"],
            "schedule_on_track": schedule["likely_to_meet_deadline"],
            "deadline_on_track": deadlines["likely_to_meet_deadline"],
            "overall": (
                "critical"
                if risk["risk_level"] == "High"
                or deadlines["predicted_delay_days"] > 0
                else "healthy"
                if risk["risk_level"] == "Low"
                else "attention"
            ),
        },
        "counts": counts,
        "progress": progress,
        "requirements_coverage": _requirements_coverage(project),
        "maintenance": _maintenance_health(project),
        "schedule": schedule,
        "deadlines": deadlines,
        "tasks": task_summary,
        "git": git,
        "priorities": calculate_priorities(project),
        "recommendations": _recommendations(
            project,
            progress,
            risk,
            schedule,
            deadlines,
            task_summary,
            git.get("risk") if git else None,
        ),
        "as_of": date.today(),
    }

def daily_priorities(project):
    intelligence = build_intelligence(project)
    items = []
    for item in intelligence["recommendations"]:
        items.append({"priority": item["priority"], "area": item["area"], "action": item["message"]})
    for task in intelligence["tasks"]["recommended_tasks"][:5]:
        items.append({"priority": task["priority"], "area": "development", "action": f"Work on {task['task_key']}: {task['title']}"})
    return {"project_id": project.id, "date": date.today(), "items": items[:10]}
