from __future__ import annotations
import json, re
from collections import Counter
from app.models.release import SDLCTtraceLink
from app.models.workflow import GeneratedTest, EngineeringFinding
from app.services.advanced_intelligence_service import requirement_quality, traceability_gaps, architecture_review, test_plan
from app.services.change_impact_service import build_impact
from app.services.git_service import GitError, status as git_status, risk as git_risk


def _tokens(s): return {x.lower() for x in re.findall(r'[A-Za-z0-9_]+', s or '') if len(x)>2}
def _match(source, targets):
    st=_tokens(source); out=[]
    for t in targets:
        tt=_tokens((getattr(t,'title','')+' '+getattr(t,'description','')))
        overlap=st & tt
        if len(overlap)>=2: out.append((len(overlap),t))
    return sorted(out,key=lambda x:-x[0])

def build_traceability(db, project):
    existing={(x.source_type,x.source_id,x.target_type,x.target_id,x.relation) for x in db.query(SDLCTtraceLink).filter(SDLCTtraceLink.project_id==project.id).all()}
    created=[]
    reqs=list(project.requirements or []); tasks=list(project.development_tasks or []); tests=db.query(GeneratedTest).filter(GeneratedTest.project_id==project.id).all()
    for req in reqs:
        for _,task in _match(req.title+' '+req.description,tasks)[:3]:
            key=('requirement',req.id,'development_task',task.id,'implements')
            if key not in existing:
                created.append(SDLCTtraceLink(project_id=project.id,source_type='requirement',source_id=req.id,target_type='development_task',target_id=task.id,relation='implements',confidence=70,notes='Heuristic semantic match.'))
        for _,test in _match(req.title+' '+req.description,tests)[:3]:
            key=('requirement',req.id,'generated_test',test.id,'verifies')
            if key not in existing:
                created.append(SDLCTtraceLink(project_id=project.id,source_type='requirement',source_id=req.id,target_type='generated_test',target_id=test.id,relation='verifies',confidence=65,notes='Heuristic semantic match.'))
        if project.database_design:
            key=('requirement',req.id,'database_design',project.database_design.id,'supports')
            if key not in existing: created.append(SDLCTtraceLink(project_id=project.id,source_type='requirement',source_id=req.id,target_type='database_design',target_id=project.database_design.id,relation='supports',confidence=50,notes='Project-level design association; review for exact table mapping.'))
        if project.prototype_design:
            key=('requirement',req.id,'prototype_design',project.prototype_design.id,'supports')
            if key not in existing: created.append(SDLCTtraceLink(project_id=project.id,source_type='requirement',source_id=req.id,target_type='prototype_design',target_id=project.prototype_design.id,relation='supports',confidence=50,notes='Project-level prototype association; review for exact screen mapping.'))
        if project.documentation_set:
            for doc in (project.documentation_set.documents or [])[:5]:
                key=('requirement',req.id,'documentation_document',doc.id,'documents')
                if key not in existing: created.append(SDLCTtraceLink(project_id=project.id,source_type='requirement',source_id=req.id,target_type='documentation_document',target_id=doc.id,relation='documents',confidence=50,notes='Documentation association; review exact section coverage.'))
    for task in tasks:
        if task.requirement_id:
            key=('development_task',task.id,'requirement',task.requirement_id,'implements')
            if key not in existing: created.append(SDLCTtraceLink(project_id=project.id,source_type='development_task',source_id=task.id,target_type='requirement',target_id=task.requirement_id,relation='implements',confidence=100,notes='Explicit task requirement link.'))
    if created: db.add_all(created); db.commit()
    return created

def release_gate_report(db, project, release=None):
    reqs=list(project.requirements or []); tasks=list(project.development_tasks or [])
    quality=requirement_quality(project); gaps=traceability_gaps(project); arch=architecture_review(project); tests=test_plan(project)
    traces=list(db.query(SDLCTtraceLink).filter(SDLCTtraceLink.project_id==project.id).all())
    req_task={x.source_id for x in traces if x.source_type=='requirement' and x.target_type=='development_task' and x.relation=='implements'}
    req_test={x.source_id for x in traces if x.source_type=='requirement' and x.target_type=='generated_test' and x.relation=='verifies'}
    completed=sum(1 for t in tasks if t.completed or t.status=='done')
    open_findings=sum(1 for f in db.query(EngineeringFinding).filter(EngineeringFinding.project_id==project.id, EngineeringFinding.status.in_(['open','accepted'])).all())
    git={'available':False}; git_risk_level='unknown'
    if project.git_repository and project.git_repository.enabled:
        try:
            gs=git_status(project.git_repository.repo_path); gr=git_risk(project.git_repository.repo_path)
            git={'available':True,'clean':gs.get('clean'),'branch':gs.get('branch'),'changed_files':len(gs.get('changes',[]))}; git_risk_level=gr.get('level','unknown')
        except GitError as exc: git={'available':False,'error':str(exc)}
    gates={
      'requirements_quality': {'passed': quality['average_score']>=70, 'score': quality['average_score']},
      'traceability': {'passed': (len(reqs)==0 or len(req_task)/len(reqs)>=0.8) and (len(reqs)==0 or len(req_test)/len(reqs)>=0.5), 'task_coverage_percent': round(len(req_task)/len(reqs)*100,1) if reqs else 100.0, 'test_coverage_percent': round(len(req_test)/len(reqs)*100,1) if reqs else 100.0},
      'architecture': {'passed': not arch.get('findings'), 'finding_count': len(arch.get('findings',[]))},
      'execution': {'passed': completed>=len(tasks) if tasks else True, 'completed_tasks': completed, 'total_tasks': len(tasks)},
      'testing': {'passed': tests.get('coverage_percent', 0) > 0 if reqs else True, 'planned_tests': sum(len(x.get('cases',[])) for x in tests.get('test_items',[]))},
      'engineering_findings': {'passed': open_findings==0, 'open_findings': open_findings},
      'git': {'passed': git.get('clean',False) if git.get('available') else False, 'risk_level': git_risk_level, **git},
      'documentation': {'passed': bool(project.documentation_set and (project.documentation_set.documents or [])), 'documents': len(project.documentation_set.documents or []) if project.documentation_set else 0},
      'maintenance': {'passed': not any(x.priority in {'critical','urgent'} and x.status not in {'resolved','closed','done','cancelled'} for x in (project.maintenance_items or [])), 'critical_open': sum(1 for x in (project.maintenance_items or []) if x.priority in {'critical','urgent'} and x.status not in {'resolved','closed','done','cancelled'})},
    }
    passed=sum(1 for x in gates.values() if x['passed']); score=round(passed/len(gates)*100)
    # A release can be considered ready only when all mandatory gates pass.
    ready=all(x['passed'] for x in gates.values())
    return {'ready':ready,'readiness_score':score,'gate_status':'ready' if ready else 'blocked','gates':gates,'requirements':len(reqs),'tasks':len(tasks),'completed_tasks':completed,'trace_links':len(traces),'open_engineering_findings':open_findings}
