import re
from collections import Counter

from app.models.project import Project
from app.schemas.knowledge import KnowledgeEntryCreate
from app.crud.knowledge import upsert_entry


def _tokens(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9_]+", (text or "").lower()) if len(t) > 2]


def _add(items, source_type, source_id, title, content, tags=()):
    items.append(KnowledgeEntryCreate(source_type=source_type, source_id=str(source_id), title=title,
                                      content=content[:20000], tags=list(tags)))


def collect_project_entries(project: Project, db=None):
    items = []
    _add(items, "project", project.id, project.name, f"{project.description}\nStatus: {project.status}\nTarget date: {project.target_date}", ["project", project.status])
    for m in project.milestones or []:
        _add(items, "milestone", m.id, m.name, f"{m.description}\nDue: {m.due_date}\nCompleted: {m.completed}", ["milestone"])
    for r in project.requirements or []:
        _add(items, "requirement", r.id, getattr(r, "title", f"Requirement {r.id}"), f"{getattr(r, 'description', '')}\nType: {getattr(r, 'requirement_type', '')}\nPriority: {getattr(r, 'priority', '')}", ["requirements"])
        for c in getattr(r, "acceptance_criteria", []) or []:
            _add(items, "acceptance_criterion", c.id, f"Acceptance criterion for {r.id}", getattr(c, "description", ""), ["acceptance", "requirements"])
    for s in project.user_stories or []:
        _add(items, "user_story", s.id, getattr(s, "title", f"User Story {s.id}"), f"As a {getattr(s, 'role', '')}, I want {getattr(s, 'goal', '')}, so that {getattr(s, 'benefit', '')}", ["user-story"])
    for u in project.use_cases or []:
        _add(items, "use_case", u.id, getattr(u, "name", f"Use Case {u.id}"), f"Actor: {getattr(u, 'actor', '')}\n{getattr(u, 'description', '')}", ["use-case"])
    if project.database_design:
        d = project.database_design
        for t in d.tables or []:
            cols = "\n".join(f"{c.name} {c.data_type}" for c in t.columns or [])
            _add(items, "database_table", t.id, t.name, f"{t.description}\n{cols}", ["database", "table"])
    if project.prototype_design:
        for screen in project.prototype_design.screens or []:
            comps = ", ".join(c.name for c in screen.components or [])
            _add(items, "prototype_screen", screen.id, screen.name, f"Route: {screen.route}\nPurpose: {screen.purpose}\nComponents: {comps}", ["prototype", "ui"])
    if project.documentation_set:
        for doc in project.documentation_set.documents or []:
            _add(items, "documentation", doc.id, doc.title, doc.content_markdown, ["documentation", doc.document_type])
    for item in project.maintenance_items or []:
        _add(items, "maintenance", item.id, item.title, f"{item.description}\nType: {item.item_type}\nSeverity: {item.severity}\nStatus: {item.status}", ["maintenance", item.item_type])
    for d in project.deadlines or []:
        _add(items, "deadline", d.id, d.title, f"{d.description}\nDue: {d.due_date}\nCompleted: {d.completed}", ["deadline"])
    return items


def index_project(db, project):
    from app.models.knowledge import KnowledgeEntry
    items = collect_project_entries(project, db)
    existing = {(e.source_type, e.source_id): e for e in project.knowledge_entries or []}
    incoming = {(i.source_type, i.source_id) for i in items}
    removed = 0
    for key, entry in existing.items():
        if key not in incoming:
            db.delete(entry); removed += 1
    for item in items:
        upsert_entry(db, project.id, item)
    return len(items), removed


def search_entries(entries, query: str, limit: int = 20):
    q_tokens = set(_tokens(query))
    if not q_tokens:
        return []
    results = []
    for e in entries:
        title_tokens = set(_tokens(e.title))
        content_tokens = set(_tokens(e.content))
        tag_tokens = set(_tokens(e.tags.replace(',', ' ')))
        matched = q_tokens & (title_tokens | content_tokens | tag_tokens)
        if not matched:
            continue
        score = (len(matched) / len(q_tokens)) * 100
        score += len(matched & title_tokens) * 20 + len(matched & tag_tokens) * 10
        results.append((round(score, 2), sorted(matched), e))
    results.sort(key=lambda x: (-x[0], x[2].id))
    return results[:limit]


def tags_for_entry(entry):
    return [t for t in entry.tags.split(',') if t]
