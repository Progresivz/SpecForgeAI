from __future__ import annotations
import re
from collections import Counter
from app.services import git_service

def _tokens(text: str) -> set[str]:
    return {x.lower() for x in re.findall(r"[A-Za-z0-9_]+", text or "") if len(x) > 2}

def _match(items, text: str, minimum: int = 2):
    hay = _tokens(text); matches = []
    for item in items:
        label = " ".join(str(getattr(item, k, "")) for k in ("title", "description"))
        tokens = _tokens(label); overlap = hay & tokens
        if len(overlap) >= minimum:
            matches.append({"id": item.id, "title": getattr(item, "title", ""), "score": round(len(overlap) / max(len(tokens), 1) * 100, 1)})
    return sorted(matches, key=lambda x: -x["score"])[:10]

def _suggest_tests(paths):
    out=[]
    for path in paths:
        low=path.lower()
        if any(x in low for x in ("auth","security","login","permission")):
            out.append({"priority":"high","type":"security","message":f"Run authentication, authorization, and negative security tests for {path}."})
        elif any(x in low for x in ("api","route","endpoint","controller","view")):
            out.append({"priority":"high","type":"integration","message":f"Run API/integration tests covering changed behavior in {path}."})
        elif any(x in low for x in ("model","schema","migration","database","crud")):
            out.append({"priority":"high","type":"database","message":f"Run database/schema regression tests for {path}."})
        elif low.endswith(".py"):
            out.append({"priority":"medium","type":"unit","message":f"Run focused unit tests for {path}."})
    return (out or [{"priority":"medium","type":"regression","message":"Run the project's regression test suite for the changed surface."}])[:12]

def build_impact(repo: str, project, max_files: int = 100):
    changes=git_service.status(repo).get("changes",[])
    paths=[c["path"] for c in changes if c.get("path")][:max_files]
    parts=[]
    for path in paths:
        try: content=git_service.untracked_file_content(repo,path,20000)
        except Exception: content=""
        parts.append(path+"\n"+content)
    context="\n".join(parts)
    requirements=_match(list(project.requirements or []),context)
    tasks=_match(list(project.development_tasks or []),context)
    req_ids={x["id"] for x in requirements}
    unmapped=[{"id":r.id,"title":getattr(r,"title","")} for r in (project.requirements or []) if r.id not in req_ids]
    findings=[]
    for change in changes[:max_files]:
        if change.get("status")=="D": findings.append({"severity":"high","category":"deletion","path":change["path"],"message":"Deleted source may remove implementation coverage; verify linked requirements and tasks."})
        elif change.get("status")=="??": findings.append({"severity":"medium","category":"untracked","path":change["path"],"message":"Untracked file is not part of a commit; verify it is intentionally added."})
    if paths and not requirements: findings.append({"severity":"medium","category":"traceability","path":None,"message":"Changed code could not be mapped confidently to a requirement."})
    if paths and not tasks: findings.append({"severity":"medium","category":"execution","path":None,"message":"Changed code could not be mapped confidently to a development task."})
    counts=Counter(f["severity"] for f in findings)
    return {
    "files_changed": len(paths),
    "changed_files": changes[:max_files],
    "code_files_changed": len(paths),
    "affected": {
        "requirements": requirements,
        "tasks": tasks,
    },
    "unmapped_requirements": unmapped[:25],
    "findings": findings,
    "finding_counts": {
        k: counts[k] for k in ("high", "medium", "low")
    },
    "test_suggestions": _suggest_tests(paths),
}

def build_diff_context(repo: str, project, base: str="HEAD", max_chars: int=120000):
    data=git_service.diff(repo,base=base,max_chars=max_chars)
    return {"base":base,"diff":data["diff"],"truncated":data["truncated"],"characters":data["characters"],"impact":build_impact(repo,project)}
