from sqlalchemy.orm import Session
from app.models.project import Project
from app.models.requirement import Requirement, UserStory, UseCase

KEYWORDS = {
 'login': ('Login', '/login', 'Authenticate the user'), 'sign in': ('Login', '/login', 'Authenticate the user'),
 'register': ('Registration', '/register', 'Create a user account'), 'dashboard': ('Dashboard', '/', 'View project and application status'),
 'profile': ('Profile', '/profile', 'View and update user profile'), 'report': ('Reports', '/reports', 'Review generated reports'),
 'search': ('Search', '/search', 'Find relevant records or knowledge'), 'settings': ('Settings', '/settings', 'Configure application settings'),
}

def _screen_for(text, fallback):
    low = text.lower()
    for key, value in KEYWORDS.items():
        if key in low: return value
    return (fallback, '/' + fallback.lower().replace(' ', '-'), text[:180])

def generate_prototype(project: Project, db: Session):
    requirements = db.query(Requirement).filter(Requirement.project_id == project.id).order_by(Requirement.id).all()
    stories = db.query(UserStory).filter(UserStory.project_id == project.id).order_by(UserStory.id).all()
    cases = db.query(UseCase).filter(UseCase.project_id == project.id).order_by(UseCase.id).all()
    screens, seen = [], set()
    def add_screen(name, route, purpose, comps):
        key = route.lower()
        if key in seen: return
        seen.add(key); screens.append({'name': name, 'route': route, 'purpose': purpose, 'layout': 'standard', 'components': comps})
    add_screen('Dashboard', '/', 'Project overview and primary navigation', [
        {'name':'Header','component_type':'header','description':'Application title and account actions','interaction':'Navigate to major areas'},
        {'name':'Navigation','component_type':'navigation','description':'Primary application navigation','interaction':'Open selected screen'},
        {'name':'Summary Cards','component_type':'card-group','description':'Key status, progress, and alerts','interaction':'Open related detail'},
    ])
    for item in requirements + stories + cases:
        text = getattr(item, 'title', '') or getattr(item, 'description', '')
        name, route, purpose = _screen_for(text, 'Requirement Detail')
        add_screen(name, route, purpose, [
            {'name':'Page Header','component_type':'header','description':name + ' title and context','interaction':'Navigate back or forward'},
            {'name':'Content Area','component_type':'content','description':purpose,'interaction':'Read and interact with information'},
            {'name':'Primary Action','component_type':'button','description':'Main action for this screen','interaction':'Submit, save, or continue'},
        ])
    if len(screens) == 1: add_screen('Project Details','/projects/{project_id}','Review project information and milestones', [{'name':'Project Summary','component_type':'card','description':'Project metadata and progress','interaction':'Open project sections'}])
    flows=[]
    for a,b in zip(screens, screens[1:]): flows.append({'name':f'{a["name"]} to {b["name"]}','from_screen':a['name'],'to_screen':b['name'],'trigger':'Primary navigation or action','notes':'Generated from project requirements'})
    lines=[f'# Prototype Specification: {project.name}','', '## UX Goals', f'- Provide a clear path through the project workflow for **{project.name}**.', '- Keep primary actions visible and minimize unnecessary navigation.', '', '## Screen Hierarchy']
    for i,s in enumerate(screens,1): lines += [f'{i}. **{s["name"]}** (`{s["route"]}`) — {s["purpose"]}', *[f'   - {c["component_type"]}: {c["name"]} — {c["description"]}' for c in s['components']]]
    lines += ['', '## UI Flow']
    for f in flows: lines.append(f'- {f["from_screen"]} → {f["to_screen"]}: {f["trigger"]}')
    lines += ['', '## UX Recommendations', '- Use consistent navigation and terminology across screens.', '- Provide validation and clear feedback for user actions.', '- Make important status, risks, and next actions visually prominent.', '', '## Requirements Coverage', f'- Requirements: {len(requirements)}', f'- User stories: {len(stories)}', f'- Use cases: {len(cases)}']
    return {'screens': screens, 'flows': flows, 'summary_markdown':'\n'.join(lines)}
