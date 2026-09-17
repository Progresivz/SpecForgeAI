import json
from types import SimpleNamespace
from app.services.release_automation_service import build_test_suite, release_notes

def test_release_test_suite_has_requirement_cases():
    ac=SimpleNamespace(criterion='User can sign in successfully')
    req=SimpleNamespace(id=1, requirement_id='REQ-1', title='User login', acceptance_criteria=[ac])
    project=SimpleNamespace(requirements=[req])
    readiness={'gates':{'requirements_quality':{'passed':True},'testing':{'passed':True}}}
    suite=build_test_suite(project, readiness)
    assert suite and suite[0]['requirement_id']==1

def test_release_notes_without_git():
    release=SimpleNamespace(version='v1.0',name='Initial',description='First release',readiness_score=90,gate_status='ready')
    project=SimpleNamespace(git_repository=None, development_tasks=[], maintenance_items=[], documentation_set=None, requirements=[])
    text=release_notes(None,project,release)
    assert '# v1.0 — Initial' in text
    assert 'Git evidence unavailable' in text

def test_ai_decision_cannot_override_failed_readiness():
    from app.services.release_automation_service import determine_release_decision
    readiness={'ready':False,'readiness_score':20}
    assert determine_release_decision(readiness, {'decision':'GO','score':100}) == 'NO-GO'

def test_go_requires_ai_go_when_ai_is_used():
    from app.services.release_automation_service import determine_release_decision
    readiness={'ready':True,'readiness_score':100}
    assert determine_release_decision(readiness, {'decision':'NO-GO','score':100}) == 'NO-GO'
    assert determine_release_decision(readiness, {'decision':'GO','score':90}) == 'GO'
