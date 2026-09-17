from collections import Counter
from datetime import date


def _words(value: str) -> set[str]:
    return {w.strip('.,:;!?()[]{}').lower() for w in (value or '').split() if len(w.strip()) >= 4}


def requirement_quality(project):
    requirements = list(project.requirements or [])
    findings = []
    scores = []
    title_counts = Counter((r.title or '').strip().lower() for r in requirements)
    for req in requirements:
        score = 100
        issues = []
        if len((req.description or '').strip()) < 30:
            score -= 20; issues.append('description is too short to be implementation-ready')
        if not req.rationale:
            score -= 10; issues.append('missing rationale')
        if not req.source:
            score -= 5; issues.append('missing source')
        criteria = list(req.acceptance_criteria or [])
        if not criteria:
            score -= 25; issues.append('no acceptance criteria')
        else:
            vague = sum(len(_words(c.criterion)) < 5 for c in criteria)
            if vague:
                score -= min(15, vague * 5); issues.append(f'{vague} acceptance criterion/criteria may be too vague')
        if title_counts[(req.title or '').strip().lower()] > 1:
            score -= 15; issues.append('duplicate requirement title')
        title_words = _words(req.title)
        if title_words and len(title_words) <= 2:
            score -= 5; issues.append('title is unusually short')
        score = max(0, score)
        scores.append(score)
        if issues:
            findings.append({'requirement_id': req.id, 'requirement_key': req.requirement_id, 'title': req.title, 'score': score, 'issues': issues})
    avg = round(sum(scores) / len(scores), 1) if scores else 0.0
    return {'total': len(requirements), 'average_score': avg, 'quality_band': 'strong' if avg >= 80 else 'attention' if avg >= 60 else 'weak', 'findings': findings}


def traceability_gaps(project):
    requirements = list(project.requirements or [])
    links = []
    for req in requirements:
        links.extend(list(req.trace_links or []))
    linked_req_ids = {x.requirement_id for x in links}
    tasks = list(project.development_tasks or [])
    task_req_ids = {x.requirement_id for x in tasks if x.requirement_id is not None}
    stories = list(getattr(project, 'user_stories', []) or [])
    story_ids = {x.id for x in stories}
    linked_story_ids = {x.user_story_id for x in links if x.user_story_id is not None}
    gaps = []
    for req in requirements:
        if req.id not in linked_req_ids:
            gaps.append({'type': 'missing_traceability', 'requirement_id': req.id, 'requirement_key': req.requirement_id, 'message': 'Requirement has no user-story/use-case trace.'})
        if req.id not in task_req_ids:
            gaps.append({'type': 'missing_task', 'requirement_id': req.id, 'requirement_key': req.requirement_id, 'message': 'Requirement is not linked to a development task.'})
    orphan_stories = [s for s in stories if s.id not in linked_story_ids]
    return {'requirements': len(requirements), 'trace_links': len(links), 'requirements_with_trace': len(linked_req_ids), 'requirements_with_tasks': len(task_req_ids), 'orphan_user_stories': [{'id': s.id, 'story_id': s.story_id, 'title': s.title} for s in orphan_stories], 'gaps': gaps, 'coverage_percent': round(len(linked_req_ids) / len(requirements) * 100, 1) if requirements else 0.0}

def traceability_matrix(project):
    requirements = list(project.requirements or [])
    tasks = list(project.development_tasks or [])
    stories = list(getattr(project, "user_stories", []) or [])

    tasks_by_requirement = {}
    for task in tasks:
        if task.requirement_id is not None:
            tasks_by_requirement.setdefault(task.requirement_id, []).append(task)

    stories_by_requirement = {}
    for req in requirements:
        linked_story_ids = {
            link.user_story_id
            for link in list(req.trace_links or [])
            if link.user_story_id is not None
        }

        stories_by_requirement[req.id] = [
            story
            for story in stories
            if story.id in linked_story_ids
        ]

    matrix = []

    for req in requirements:
        criteria = list(req.acceptance_criteria or [])
        req_tasks = tasks_by_requirement.get(req.id, [])
        req_stories = stories_by_requirement.get(req.id, [])

        matrix.append(
            {
                "requirement_id": req.id,
                "requirement_key": req.requirement_id,
                "requirement_title": req.title,
                "acceptance_criteria_count": len(criteria),
                "acceptance_criteria": [
                    {
                        "id": criterion.id,
                        "criterion": criterion.criterion,
                        "is_met": criterion.is_met,
                    }
                    for criterion in criteria
                ],
                "user_stories": [
                    {
                        "id": story.id,
                        "story_id": story.story_id,
                        "title": story.title,
                    }
                    for story in req_stories
                ],
                "tasks": [
                    {
                        "id": task.id,
                        "task_key": task.task_key,
                        "title": task.title,
                        "status": task.status,
                        "priority": task.priority,
                    }
                    for task in req_tasks
                ],
                "has_traceability": bool(req.trace_links),
                "has_user_story": bool(req_stories),
                "has_task": bool(req_tasks),
                "has_acceptance_criteria": bool(criteria),
            }
        )

    covered_requirements = sum(
        1
        for item in matrix
        if item["has_traceability"]
        and item["has_user_story"]
        and item["has_task"]
        and item["has_acceptance_criteria"]
    )

    coverage_percent = (
        round(covered_requirements / len(matrix) * 100, 1)
        if matrix
        else 0.0
    )

    return {
        "project_id": project.id,
        "requirements": len(requirements),
        "covered_requirements": covered_requirements,
        "coverage_percent": coverage_percent,
        "matrix": matrix,
    }

def architecture_review(project):
    findings = []
    design = project.database_design
    if not design:
        findings.append({'severity': 'high', 'area': 'database', 'message': 'No database design exists.'})
    else:
        tables = list(design.tables or [])
        names = [t.name.lower() for t in tables]
        duplicates = [n for n, c in Counter(names).items() if c > 1]
        if not tables:
            findings.append({'severity': 'high', 'area': 'database', 'message': 'Database design has no tables.'})
        if duplicates:
            findings.append({'severity': 'high', 'area': 'database', 'message': f'Duplicate table names: {duplicates}.'})
        for table in tables:
            columns = list(table.columns or [])
            if not columns:
                findings.append({'severity': 'medium', 'area': 'database', 'message': f'Table {table.name} has no columns.'})
            if not any(c.primary_key for c in columns):
                findings.append({'severity': 'medium', 'area': 'database', 'message': f'Table {table.name} has no primary key.'})
        table_names = {t.name for t in tables}
        table_map = {t.name: {c.name for c in list(t.columns or [])} for t in tables}
        for rel in list(design.relationships or []):
            if rel.from_table not in table_names or rel.to_table not in table_names:
                findings.append({'severity': 'high', 'area': 'database', 'message': f'Relationship {rel.from_table}->{rel.to_table} references a missing table.'})
            elif rel.from_column not in table_map[rel.from_table] or rel.to_column not in table_map[rel.to_table]:
                findings.append({'severity': 'high', 'area': 'database', 'message': f'Relationship {rel.from_table}.{rel.from_column} -> {rel.to_table}.{rel.to_column} references a missing column.'})
    prototype = project.prototype_design
    if not prototype:
        findings.append({'severity': 'medium', 'area': 'prototype', 'message': 'No prototype design exists.'})
    else:
        screens = list(prototype.screens or [])
        screen_names = {s.name for s in screens}
        if not screens:
            findings.append({'severity': 'medium', 'area': 'prototype', 'message': 'Prototype has no screens.'})
        for flow in list(prototype.flows or []):
            if flow.from_screen not in screen_names or flow.to_screen not in screen_names:
                findings.append({'severity': 'medium', 'area': 'prototype', 'message': f'Flow {flow.name} references a missing screen.'})
    tasks = list(project.development_tasks or [])
    task_ids = {t.id for t in tasks}
    for task in tasks:
        if task.depends_on_task_id == task.id:
            findings.append({'severity': 'high', 'area': 'execution', 'message': f'Task {task.task_key} depends on itself.'})
        elif task.depends_on_task_id and task.depends_on_task_id not in task_ids:
            findings.append({'severity': 'medium', 'area': 'execution', 'message': f'Task {task.task_key} references a missing dependency.'})
    counts = Counter(x['severity'] for x in findings)
    level = 'high' if counts['high'] else 'medium' if counts['medium'] else 'low'
    return {'architecture_health': level, 'findings': findings, 'summary': dict(counts)}


def test_plan(project):
    tests = []
    for req in list(project.requirements or []):
        criteria = list(req.acceptance_criteria or [])
        tests.append({'requirement_id': req.id, 'requirement_key': req.requirement_id, 'title': f'Verify: {req.title}', 'test_type': 'functional' if req.requirement_type == 'functional' else 'nonfunctional', 'acceptance_criteria_count': len(criteria), 'cases': [{'name': f'AC-{i+1}', 'expected': c.criterion} for i, c in enumerate(criteria)]})
    return {'project_id': project.id, 'generated_on': date.today(), 'total_requirements': len(list(project.requirements or [])), 'test_items': tests, 'coverage_percent': round(sum(bool(x['cases']) for x in tests) / len(tests) * 100, 1) if tests else 0.0}
