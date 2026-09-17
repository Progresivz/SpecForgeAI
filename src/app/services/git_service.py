from __future__ import annotations
from datetime import datetime
from pathlib import Path
import os, re, subprocess
from app.core.config import settings

class GitError(RuntimeError): pass

GIT_FILES = {".gitignore", "requirements.txt", "package.json", "package-lock.json", "poetry.lock", "pyproject.toml", "uv.lock"}
RISK_PATTERNS = [("high", re.compile(r"(^|/)(auth|security|secrets?|config)(/|\\.|$)|(^|/)(migrations?|alembic)(/|$)", re.I)), ("high", re.compile(r"(^|/)(\.env|Dockerfile|docker-compose[^/]*|\.github/)(/|$)", re.I)), ("medium", re.compile(r"(^|/)(models?|database|schemas?|api|routes?|services?)(/|$)", re.I))]

def _validate_path(repo: str) -> Path:
    path = Path(repo).expanduser().resolve()
    if settings.git_allowed_roots:
        allowed = [Path(root).expanduser().resolve() for root in settings.git_allowed_roots]
        if not any(path == root or root in path.parents for root in allowed):
            raise GitError("Repository path is outside the configured Git allowed roots")
    return path

def _run(repo: str, args: list[str], check=True) -> str:
    path = _validate_path(repo)
    if not path.is_dir() or not (path / ".git").exists(): raise GitError("Configured path is not a Git working tree")
    try:
        p = subprocess.run(["git", "-C", str(path), *args], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15, check=check)
    except FileNotFoundError: raise GitError("Git executable is not installed")
    except subprocess.CalledProcessError as e: raise GitError(e.stderr.strip() or "Git command failed")
    except subprocess.TimeoutExpired: raise GitError("Git command timed out")
    return p.stdout

def configure_path(repo: str) -> str:
    return str(_validate_path(repo))

def status(repo: str):
    branch = _run(repo, ["branch", "--show-current"]).strip() or "HEAD"
    counts = _run(repo, ["rev-list", "--left-right", "--count", f"{branch}...@{{u}}"], check=False).strip()
    ahead = behind = 0
    if counts and not counts.startswith("fatal"):
        try: behind, ahead = map(int, counts.split())
        except ValueError: pass
    rows=[]
    for line in _run(repo,["status","--porcelain=v1"]).splitlines():
        if len(line) < 4: continue
        code=line[:2]; path=line[3:]
        old=None
        if " -> " in path: old, path=path.split(" -> ",1)
        rows.append({"status": code.strip() or "?", "path": path, "old_path": old})
    return {"branch":branch,"ahead":ahead,"behind":behind,"clean":not rows,"changes":rows}

def commits(repo: str, limit=50):
    fmt="%H%x1f%h%x1f%an%x1f%ae%x1f%aI%x1f%s%x1e"
    out=_run(repo,["log",f"-n{max(1,min(limit,200))}",f"--pretty=format:{fmt}"])
    result=[]
    for row in out.split("\x1e"):
        row=row.strip("\n")
        if not row: continue
        p=row.split("\x1f")
        if len(p)!=6: continue
        result.append({"hash":p[0],"short_hash":p[1],"author":p[2],"email":p[3],"date":datetime.fromisoformat(p[4]),"subject":p[5]})
    return result

def contributors(repo: str):
    result=[]
    for line in _run(repo,["shortlog","-sne","--all"]).splitlines():
        m=re.match(r"\s*(\d+)\s+(.+?)\s+<([^>]+)>$",line)
        if m: result.append({"name":m.group(2),"email":m.group(3),"commits":int(m.group(1))})
    return result

def compare(repo: str, base: str, head: str):
    _run(repo,["rev-parse","--verify",base]); _run(repo,["rev-parse","--verify",head])
    stat=_run(repo,["diff","--shortstat",f"{base}..{head}"]).strip()
    nums=re.search(r"(\d+) files? changed",stat); ins=re.search(r"(\d+) insertions?",stat); dels=re.search(r"(\d+) deletions?",stat)
    changes=[]
    for line in _run(repo,["diff","--name-status",f"{base}..{head}"]).splitlines():
        p=line.split("\t")
        if len(p)>=2: changes.append({"status":p[0],"path":p[-1],"old_path":p[1] if p[0].startswith("R") and len(p)>2 else None})
    return {"base":base,"head":head,"files_changed":int(nums.group(1)) if nums else len(changes),"insertions":int(ins.group(1)) if ins else 0,"deletions":int(dels.group(1)) if dels else 0,"changes":changes}

def risk(repo: str, base: str | None=None, head: str="HEAD"):
    if base:
        data=compare(repo,base,head); files=data["changes"]; volume=data["insertions"]+data["deletions"]
    else:
        files=status(repo)["changes"]; volume=0
    score=0; reasons=[]
    for f in files:
        path=f["path"]
        if path in GIT_FILES: score=max(score,2); reasons.append(f"Dependency/build configuration changed: {path}")
        for level, pat in RISK_PATTERNS:
            if pat.search(path):
                score=max(score,3 if level=="high" else 2); reasons.append(f"Sensitive architectural area changed: {path}"); break
    if len(files)>=10: score=max(score,2); reasons.append(f"Large change surface: {len(files)} files affected")
    if volume>=500: score=max(score,2); reasons.append(f"Large diff volume: {volume} lines changed")
    level="high" if score>=3 else "medium" if score>=2 else "low"
    return {"level":level,"score":score,"reasons":list(dict.fromkeys(reasons)),"affected_files":[f["path"] for f in files]}

def rollback_suggestions(repo: str, limit=10):
    items=[]
    for c in commits(repo,limit):
        subject=c["subject"].lower()
        if any(x in subject for x in ["revert","rollback","fix","hotfix","security"]):
            items.append({"priority":"high" if any(x in subject for x in ["security","hotfix"]) else "medium","reason":f"Commit message indicates corrective work: {c['subject']}","commit":c["hash"],"suggestion":f"Review {c['short_hash']} and consider reverting it only if its change is confirmed to be the source of a regression."})
    if not items:
        cs=commits(repo,2)
        if cs: items.append({"priority":"low","reason":"No explicit rollback marker was found in recent commit messages.","commit":cs[0]["hash"],"suggestion":f"Use {cs[0]['short_hash']} as the review point and create a new revert commit if rollback is required; do not reset shared history automatically."})
    return items

def changelog(repo: str, limit=20):
    cs=commits(repo,limit)
    lines=["# Changelog","",f"Generated from the latest {len(cs)} Git commits.",""]
    for c in cs: lines.append(f"- **{c['short_hash']}** — {c['subject']} ({c['author']})")
    return {"title":"Generated Changelog","content_markdown":"\n".join(lines)+"\n"}



def diff(repo: str, base: str = "HEAD", paths: list[str] | None = None, max_chars: int = 200_000):
    args = ["diff", "--no-ext-diff", "--unified=40", base]
    if paths:
        args += ["--", *paths]
    raw = _run(repo, args)
    return {"base": base, "diff": raw[:max_chars], "truncated": len(raw) > max_chars, "characters": min(len(raw), max_chars)}


def untracked_file_content(repo: str, path: str, max_chars: int = 50_000):
    root = Path(repo).resolve()
    candidate = (root / path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise GitError("Path must remain inside the configured repository") from exc
    if not candidate.is_file():
        return ""
    return candidate.read_text(encoding="utf-8", errors="replace")[:max_chars]
