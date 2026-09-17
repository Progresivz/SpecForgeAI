from datetime import date
from html import escape

DOCUMENT_TYPES = ['proposal','srs','design','database','api','test_plan','user_manual','installation','maintenance','release_notes','changelog']

def _bullets(items, attr):
    return '\n'.join(f'- **{getattr(x, attr)}** — {getattr(x, "description", "")}' for x in items) or '- None documented.'

def generate_documents(project, db):
    reqs=list(project.requirements); stories=list(project.user_stories); cases=list(project.use_cases)
    design=project.database_design; proto=project.prototype_design
    sections={}
    sections['proposal']=f'''# Project Proposal: {project.name}\n\n## Overview\n{project.description or "No project description provided."}\n\n## Objectives\n- Deliver the defined project scope.\n- Maintain traceable requirements, architecture, and implementation documentation.\n\n## Schedule\n- Start: {project.start_date}\n- Target: {project.target_date}\n- Status: {project.status}\n'''
    sections['srs']=f'''# Software Requirements Specification: {project.name}\n\n## Introduction\n{project.description}\n\n## Requirements\n{_bullets(reqs, 'title')}\n\n## User Stories\n''' + ('\n'.join(f'- **{s.story_id}: {s.title}** — As a {s.as_a}, I want {s.i_want}, so that {s.so_that}.' for s in stories) or '- None documented.') + '\n\n## Use Cases\n' + ('\n'.join(f'- **{c.use_case_id}: {c.title}** — Actor: {c.actor}; Goal: {c.goal}' for c in cases) or '- None documented.')
    sections['design']=f'''# System Design: {project.name}\n\n## Architecture Context\nSpecForge AI currently models requirements, database design, prototype specifications, and project management as connected project artifacts.\n\n## UI Prototype\n''' + ('\n'.join(f'- **{s.name}** (`{s.route}`): {s.purpose}' for s in proto.screens) if proto else '- No prototype has been defined.')
    sections['database']=f'''# Database Documentation: {project.name}\n\n## Database Design\n''' + (f'**{design.name}** — target dialect: {design.target_dialect}.\n\n' + '\n'.join(f'### {t.name}\n{t.description or ""}\n' + '\n'.join(f'- `{c.name}`: `{c.data_type}`' + (' PK' if c.primary_key else '') + (' NOT NULL' if not c.nullable else '') for c in t.columns) for t in design.tables) if design else '- No database design has been defined.')
    sections['api']=f'''# API Documentation: {project.name}\n\n## Authentication\nProtected project artifacts use the authenticated user context.\n\n## Project API Areas\n- Authentication\n- Projects and milestones\n- Requirements and traceability\n- Database design and SQL export\n- Prototype design\n- Documentation generation and export\n'''
    sections['test_plan']=f'''# Test Plan: {project.name}\n\n## Scope\nValidate requirements, project ownership, artifact generation, exports, and protected API endpoints.\n\n## Requirement Coverage\n{_bullets(reqs, 'title')}\n\n## Recommended Tests\n- Authentication and authorization\n- CRUD validation\n- SRS/prototype/document generation\n- SQL export\n- Markdown/HTML/DOCX/PDF export integrity\n'''
    sections['user_manual']=f'''# User Manual: {project.name}\n\n## Workflow\n1. Create a project.\n2. Capture requirements and user stories.\n3. Generate the database design.\n4. Generate the UI prototype specification.\n5. Generate project documentation.\n6. Export documents in the required format.\n'''
    sections['installation']=f'''# Installation Guide: {project.name}\n\n## Backend\nInstall the Python dependencies from `requirements.txt`, configure environment variables using `.env.example`, then start the FastAPI application with the project's runner.\n\n## Database\nThe MVP uses SQLite locally and can be configured for PostgreSQL through the database URL setting.\n'''
    sections['maintenance']=f'''# Maintenance Manual: {project.name}\n\n## Maintenance Areas\n- Review requirements and acceptance criteria.\n- Keep database and prototype artifacts synchronized.\n- Review project milestones and schedule risk.\n- Regenerate documentation after material architecture changes.\n'''
    sections['release_notes']=f'''# Release Notes: {project.name}\n\n## Current Release\nDocumentation generated from the current project state on {date.today()}.\n\n## Included Artifacts\n- Requirements and SRS\n- Database design\n- UI prototype specification\n- Project management data\n'''
    sections['changelog']=f'''# Changelog: {project.name}\n\n## {date.today()}\n- Generated documentation from the current project artifacts.\n- Included project requirements, architecture context, database, API, prototype, testing, and operational guidance.\n'''
    titles={'proposal':'Project Proposal','srs':'Software Requirements Specification','design':'System Design','database':'Database Documentation','api':'API Documentation','test_plan':'Test Plan','user_manual':'User Manual','installation':'Installation Guide','maintenance':'Maintenance Manual','release_notes':'Release Notes','changelog':'Changelog'}
    return [{'document_type':k,'title':f'{titles[k]} — {project.name}','content_markdown':v} for k,v in sections.items()]

def markdown_to_html(md):
    lines=md.splitlines(); out=[]
    for line in lines:
        if line.startswith('### '): out.append(f'<h3>{escape(line[4:])}</h3>')
        elif line.startswith('## '): out.append(f'<h2>{escape(line[3:])}</h2>')
        elif line.startswith('# '): out.append(f'<h1>{escape(line[2:])}</h1>')
        elif line.startswith('- '): out.append(f'<li>{escape(line[2:])}</li>')
        elif line.strip(): out.append(f'<p>{escape(line)}</p>')
    return '<!doctype html><html><body>' + ''.join(out) + '</body></html>'
