from __future__ import annotations

import ast
import re
from pathlib import Path
from collections import Counter

from app.services.git_service import GitError, status as git_status

DEFAULT_EXTENSIONS = {'.py', '.js', '.jsx', '.ts', '.tsx', '.java', '.cs', '.go', '.rs', '.php', '.rb', '.sql', '.html', '.css'}
IGNORED_DIRS = {'.git', '.venv', 'venv', '__pycache__', 'node_modules', '.pytest_cache', 'dist', 'build'}
SECRET_PATTERNS = [
    re.compile(r'(?i)(api[_-]?key|secret[_-]?key|password|token)\s*[=:]\s*["\'][^"\']{8,}["\']'),
    re.compile(r'(?i)-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
]


def _tokens(text: str) -> set[str]:
    return {t for t in re.findall(r'[a-zA-Z0-9_]+', text or ''.lower()) if len(t) > 2}


def _safe_relative(path: str) -> str:
    p = Path(path)
    if p.is_absolute() or '..' in p.parts:
        raise ValueError('Path must remain inside the configured repository')
    return p.as_posix()


def _read_files(repo: str, max_files: int = 250, max_bytes: int = 250_000):
    root = Path(repo).expanduser().resolve()
    if not root.is_dir() or not (root / '.git').exists():
        raise GitError('Configured path is not a Git working tree')
    files = []
    for path in root.rglob('*'):
        if not path.is_file() or any(part in IGNORED_DIRS for part in path.relative_to(root).parts):
            continue
        if path.suffix.lower() not in DEFAULT_EXTENSIONS:
            continue
        rel = path.relative_to(root).as_posix()
        try:
            size = path.stat().st_size
            if size > max_bytes:
                files.append({'path': rel, 'size_bytes': size, 'skipped': True, 'reason': 'file exceeds analysis size limit'})
                continue
            text = path.read_text(encoding='utf-8', errors='replace')
            files.append({'path': rel, 'size_bytes': size, 'content': text, 'skipped': False})
        except OSError:
            continue
        if len(files) >= max_files:
            break
    return files


def _python_metrics(content: str):
    try:
        tree = ast.parse(content)
    except SyntaxError as exc:
        return {'language': 'python', 'syntax_error': str(exc), 'functions': 0, 'classes': 0, 'imports': 0}
    functions = sum(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) for n in ast.walk(tree))
    classes = sum(isinstance(n, ast.ClassDef) for n in ast.walk(tree))
    imports = sum(isinstance(n, (ast.Import, ast.ImportFrom)) for n in ast.walk(tree))
    return {'language': 'python', 'syntax_error': None, 'functions': functions, 'classes': classes, 'imports': imports}


def _file_findings(path: str, content: str):
    findings = []
    lines = content.splitlines()
    if len(lines) > 500:
        findings.append({'severity': 'medium', 'category': 'maintainability', 'path': path, 'line': None, 'message': f'Large source file: {len(lines)} lines.'})
    for idx, line in enumerate(lines, 1):
        if re.search(r'\b(TODO|FIXME|HACK)\b', line, re.I):
            findings.append({'severity': 'low', 'category': 'technical_debt', 'path': path, 'line': idx, 'message': 'TODO/FIXME/HACK marker found.'})
        if re.search(r'\beval\s*\(|\bexec\s*\(', line):
            findings.append({'severity': 'high', 'category': 'security', 'path': path, 'line': idx, 'message': 'Dynamic code execution pattern detected; review for injection risk.'})
        if re.search(r'subprocess\.[A-Za-z_]+\([^\n]*shell\s*=\s*True', line):
            findings.append({'severity': 'high', 'category': 'security', 'path': path, 'line': idx, 'message': 'subprocess call uses shell=True; prefer argument lists and avoid untrusted shell input.'})
        if re.search(r'(?i)(password|secret|api[_-]?key|token)\s*[=:]\s*["\'][^"\']{8,}["\']', line):
            if not re.search(r'(?i)(example|placeholder|your_|change_me|dev-only)', line):
                findings.append({'severity': 'high', 'category': 'secrets', 'path': path, 'line': idx, 'message': 'Possible hard-coded secret or credential.'})
        if re.search(r'(?i)except\s*:\s*$', line.strip()):
            findings.append({'severity': 'medium', 'category': 'correctness', 'path': path, 'line': idx, 'message': 'Bare except catches every exception; handle expected exceptions explicitly.'})
    return findings


def analyze_repository(repo: str, project, max_files: int = 250):
    files = _read_files(repo, max_files=max_files)
    requirements = list(project.requirements or [])
    tasks = list(project.development_tasks or [])
    file_results = []
    findings = []
    req_tokens = [(r, _tokens(f'{getattr(r, "title", "")} {getattr(r, "description", "")}')) for r in requirements]
    task_tokens = [(t, _tokens(f'{getattr(t, "title", "")} {getattr(t, "description", "")}')) for t in tasks]
    for item in files:
        if item.get('skipped'):
            file_results.append({k: item[k] for k in ('path', 'size_bytes', 'skipped', 'reason')})
            continue
        path, content = item['path'], item['content']
        combined = _tokens(path.replace('/', ' ') + ' ' + content[:100000])
        req_matches = []
        for req, tokens in req_tokens:
            overlap = combined & tokens
            if len(overlap) >= 2:
                req_matches.append({'id': req.id, 'title': getattr(req, 'title', f'Requirement {req.id}'), 'score': round(len(overlap) / max(len(tokens), 1) * 100, 1)})
        req_matches.sort(key=lambda x: -x['score'])
        task_matches = []
        for task, tokens in task_tokens:
            overlap = combined & tokens
            if len(overlap) >= 2:
                task_matches.append({'id': task.id, 'task_key': task.task_key, 'title': task.title, 'score': round(len(overlap) / max(len(tokens), 1) * 100, 1)})
        task_matches.sort(key=lambda x: -x['score'])
        metrics = _python_metrics(content) if path.lower().endswith('.py') else {'language': Path(path).suffix.lower().lstrip('.') or 'unknown'}
        file_results.append({'path': path, 'size_bytes': item['size_bytes'], 'lines': len(content.splitlines()), 'metrics': metrics, 'requirements': req_matches[:5], 'tasks': task_matches[:5]})
        findings.extend(_file_findings(path, content))
        if metrics.get('syntax_error'):
            findings.append({'severity': 'high', 'category': 'correctness', 'path': path, 'line': None, 'message': f"Python syntax error: {metrics['syntax_error']}"})
    counts = Counter(f['severity'] for f in findings)
    return {
        'repository': str(Path(repo).resolve()),
        'files_analyzed': sum(1 for f in file_results if not f.get('skipped')),
        'files_skipped': sum(1 for f in file_results if f.get('skipped')),
        'requirements': len(requirements),
        'tasks': len(tasks),
        'findings': findings[:500],
        'finding_counts': {'high': counts['high'], 'medium': counts['medium'], 'low': counts['low']},
        'files': file_results,
    }


def changed_code_review(repo: str, project, max_files: int = 100):
    changes = git_status(repo).get('changes', [])
    code_changes = [c for c in changes if Path(c['path']).suffix.lower() in DEFAULT_EXTENSIONS][:max_files]
    analysis = analyze_repository(repo, project, max_files=max_files)
    by_path = {f['path']: f for f in analysis['files']}
    findings = []
    for change in code_changes:
        path = change['path']
        current = by_path.get(path)
        if current:
            findings.extend(f for f in analysis['findings'] if f['path'] == path)
        if change.get('status') in {'D', '??'}:
            findings.append({'severity': 'medium', 'category': 'change_review', 'path': path, 'line': None, 'message': 'Review this changed/deleted file for requirement or task coverage impact.'})
    return {
        'changed_files': code_changes,
        'code_files_changed': len(code_changes),
        'findings': findings[:500],
        'finding_counts': {k: sum(1 for f in findings if f['severity'] == k) for k in ('high', 'medium', 'low')},
        'mapped_files': [{k: v.get(k) for k in ('path', 'requirements', 'tasks')} for k, v in ((c['path'], by_path.get(c['path'], {})) for c in code_changes)],
    }
