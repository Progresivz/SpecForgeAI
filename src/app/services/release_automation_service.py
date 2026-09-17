from __future__ import annotations
import json, re
from app.models.release_automation import ReleaseAutomationRun
from app.models.workflow import GeneratedTest
from app.services.release_service import release_gate_report
from app.services.git_service import GitError, commits, changelog, status, risk
from app.services.ai_service import generate


def _safe_git(repo):
    if not repo or not repo.enabled:
        return {'available': False}
    try:
        return {'available': True, 'status': status(repo.repo_path), 'commits': commits(repo.repo_path, 30), 'risk': risk(repo.repo_path)}
    except GitError as exc:
        return {'available': False, 'error': str(exc)}


def release_notes(db, project, release):
    git = _safe_git(project.git_repository)
    lines = [f'# {release.version} — {release.name}', '', release.description or '']
    tasks = list(project.development_tasks or [])
    done = [t for t in tasks if t.completed or t.status == 'done']
    if done:
        lines += ['', '## Completed work']
        lines += [f'- {t.task_key}: {t.title}' for t in done[:50]]
    maint = [m for m in project.maintenance_items or [] if m.status in {'resolved','closed','done'}]
    if maint:
        lines += ['', '## Maintenance fixes']
        lines += [f'- {m.title}' for m in maint[:30]]
    if git['available']:
        lines += ['', '## Recent Git changes']
        lines += [f"- {c['short_hash']} — {c['subject']}" for c in git['commits'][:20]]
        if git['risk']['level'] != 'low':
            lines += ['', f"**Change risk:** {git['risk']['level']} — " + '; '.join(git['risk']['reasons'][:5])]
    else:
        lines += ['', '_Git evidence unavailable for this release._']
    lines += ['', '## Release readiness', f"- Readiness score: {release.readiness_score}%", f"- Gate status: {release.gate_status}"]
    return '\n'.join(lines).strip() + '\n'


def build_test_suite(project, readiness):
    suite=[]
    reqs=list(project.requirements or [])
    for req in reqs:
        criteria=list(req.acceptance_criteria or [])
        suite.append({'requirement_id': req.id, 'requirement_key': req.requirement_id, 'title': f'Regression: {req.title}', 'type': 'acceptance' if criteria else 'functional', 'priority': 'high' if not criteria else 'medium', 'steps': [f'Arrange the system for {req.title}.', 'Execute the implemented behavior.', 'Verify every available acceptance criterion.'], 'expected': f"Requirement {req.requirement_id} remains satisfied."})
    if not reqs:
        suite.append({'title':'Release smoke test','type':'smoke','priority':'high','steps':['Start the application.','Exercise authentication and the main project workflow.','Verify health/readiness endpoints.'],'expected':'Core application workflow is operational.'})
    for gate, info in readiness['gates'].items():
        if not info['passed']:
            suite.append({'title':f'Gate remediation: {gate}','type':'release_gate','priority':'high','steps':[f'Review the failed {gate} gate.', 'Correct the underlying evidence gap.', 'Re-run release readiness.'],'expected':f'{gate} gate passes.'})
    return suite


def evidence(project, release, readiness, suite, notes):
    return {'release_id': release.id, 'readiness': readiness, 'test_count': len(suite), 'release_notes_characters': len(notes), 'requirements': len(project.requirements or []), 'tasks': len(project.development_tasks or []), 'documentation_documents': len(project.documentation_set.documents or []) if project.documentation_set else 0}


def ai_release_review(db, project, release, readiness, notes, suite):
    prompt = '''Act as a senior release manager. Review this proposed release using ONLY the supplied evidence. Return JSON with keys: decision (GO or NO-GO), score (0-100), summary, blockers (array), risks (array), required_actions (array), evidence_gaps (array). Do not invent facts. A GO recommendation requires no material unresolved blocker and sufficient evidence.'''
    context = json.dumps({'release': {'version':release.version,'name':release.name}, 'readiness':readiness, 'release_notes':notes[:12000], 'test_suite':suite[:40]}, default=str)
    try:
        result=generate(db, project, prompt+'\n\nEVIDENCE:\n'+context, knowledge_query='release quality', max_output_tokens=2200)
        raw=result.content.strip()
        match=re.search(r'\{.*\}', raw, re.S)
        parsed=json.loads(match.group(0)) if match else {'decision':'NO-GO','score':0,'summary':raw,'blockers':['AI response was not valid JSON'],'risks':[],'required_actions':['Review the release manually.'],'evidence_gaps':[]}
        return parsed | {'provider':result.provider,'model':result.model}
    except RuntimeError as exc:
        return {'decision':'NO-GO','score':0,'summary':'AI release review unavailable.','blockers':[str(exc)],'risks':[],'required_actions':['Perform manual release review.'],'evidence_gaps':['AI review evidence unavailable.']}


def determine_release_decision(readiness, ai=None):
    ai_ok = True if ai is None else ai.get('decision', 'NO-GO').upper() == 'GO'
    return 'GO' if readiness.get('ready') and ai_ok else 'NO-GO'


def run_automation(db, project, release, include_ai=False):
    readiness=release_gate_report(db, project, release)
    notes=release_notes(db, project, release)
    suite=build_test_suite(project, readiness)
    ai={'decision':'NOT_RUN','score':None,'summary':'AI review was not requested.','blockers':[],'risks':[],'required_actions':[],'evidence_gaps':[]}
    if include_ai:
        ai=ai_release_review(db, project, release, readiness, notes, suite)
    evidence_data=evidence(project, release, readiness, suite, notes)
    # Deterministic gate decision remains authoritative; AI can add a NO-GO but cannot override failed gates.
    decision=determine_release_decision(readiness, ai if include_ai else None)
    score=round((readiness['readiness_score'] + (ai.get('score') or readiness['readiness_score']))/2) if include_ai else readiness['readiness_score']
    run=ReleaseAutomationRun(project_id=project.id, release_id=release.id, release_notes=notes, test_suite=json.dumps(suite), ai_review=json.dumps(ai), decision=decision, score=score, evidence=json.dumps(evidence_data, default=str))
    db.add(run); db.commit(); db.refresh(run)
    return run
