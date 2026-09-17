from app.models.workflow import EngineeringFinding, GeneratedTest
from app.models.maintenance import MaintenanceItem
from app.models.task import DevelopmentTask
from app.crud.workflow import add_activity

def materialize_findings(db, project, user_id, impact):
    created=[]
    for f in impact.get('findings',[]):
        item=EngineeringFinding(project_id=project.id, source='change_impact', severity=f.get('severity','medium'), category=f.get('category','general'), title=f.get('message','Engineering finding')[:200], description=f.get('message',''), file_path=f.get('path'))
        db.add(item); created.append(item)
    db.commit()
    for item in created: db.refresh(item)
    if created: add_activity(db,project.id,user_id,'findings_created',f'Created {len(created)} engineering findings from change impact.','finding')
    return created

def create_work_items(db, project, user_id, impact):
    created=[]
    for f in impact.get('findings',[]):
        if f.get('category') in {'deletion','traceability','execution','untracked'}:
            task=DevelopmentTask(project_id=project.id,task_key='',title=f"Investigate: {f.get('category','finding')}",description=f.get('message',''),task_type='review',priority=f.get('severity','medium'),status='todo',notes='Created by SpecForge engineering workflow.')
            db.add(task); db.flush(); task.task_key=f'TASK-{task.id:04d}'; created.append(task)
    db.commit()
    if created: add_activity(db,project.id,user_id,'tasks_created_from_findings',f'Created {len(created)} development tasks from engineering findings.','development_task')
    return created

def generate_tests(db, project, user_id, impact):
    created=[]
    reqs=list(project.requirements or [])
    mapped={x['id'] for x in impact.get('affected',{}).get('requirements',[])}
    suggestions=impact.get('test_suggestions',[])
    targets=[r for r in reqs if r.id in mapped] or reqs[:5]
    for i,r in enumerate(targets):
        s=suggestions[i % len(suggestions)] if suggestions else {'priority':'medium','type':'functional','message':'Run the expected behavior and regression checks.'}
        t=GeneratedTest(project_id=project.id, requirement_id=r.id, title=f"Verify requirement: {r.title}"[:200], test_type=s.get('type','functional'), priority=s.get('priority','medium'), steps=f"1. Arrange the system for '{r.title}'.\n2. Execute the behavior described by the requirement.\n3. Verify acceptance criteria and regression behavior.", expected_result=f"The implementation satisfies '{r.title}' without introducing regression.", source='change_impact')
        db.add(t); created.append(t)
    db.commit()
    if created: add_activity(db,project.id,user_id,'tests_generated',f'Generated {len(created)} proposed tests from change impact.','generated_test')
    return created
