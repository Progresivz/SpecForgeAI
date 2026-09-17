from sqlalchemy.orm import Session
from app.models.git_repository import GitRepository

def get_repository(db: Session, project_id: int, owner_id: int):
    return (db.query(GitRepository).join(GitRepository.project).filter(
        GitRepository.project_id == project_id, GitRepository.project.has(owner_id=owner_id)
    ).first())

def create_or_replace_repository(db: Session, project, data):
    repo = get_repository(db, project.id, project.owner_id)
    if repo:
        repo.repo_path = data.repo_path
        repo.default_branch = data.default_branch
        repo.enabled = data.enabled
    else:
        repo = GitRepository(project_id=project.id, repo_path=data.repo_path, default_branch=data.default_branch, enabled=data.enabled)
        db.add(repo)
    db.commit(); db.refresh(repo); return repo

def delete_repository(db: Session, repo):
    db.delete(repo); db.commit()
