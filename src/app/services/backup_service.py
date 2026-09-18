import os, shutil, sqlite3, subprocess, time
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.datetime_utils import utcnow
from app.models.operations import BackupRecord, OperationalJob


def _db_kind():
    return make_url(settings.DATABASE_URL).get_backend_name()


def _backup_dir():
    path = Path(settings.BACKUP_DIR).expanduser().resolve(); path.mkdir(parents=True, exist_ok=True); return path


def _sqlite_source(url):
    if url.database == ':memory:': raise RuntimeError('In-memory SQLite cannot be backed up to a persistent file')
    return Path(url.database).expanduser().resolve()


def verify_backup(path: Path, kind: str) -> tuple[bool, str]:
    try:
        if not path.exists() or path.stat().st_size == 0: return False, 'Backup file is missing or empty'
        if kind == 'sqlite':
            con = sqlite3.connect(str(path));
            try: result = con.execute('PRAGMA integrity_check').fetchone()[0]
            finally: con.close()
            return result == 'ok', f'SQLite integrity_check={result}'
        proc = subprocess.run(['pg_restore', '--list', str(path)], capture_output=True, text=True, timeout=60)
        if proc.returncode != 0: return False, proc.stderr.strip() or 'pg_restore validation failed'
        return True, 'PostgreSQL archive listing verified'
    except Exception as exc: return False, str(exc)


def run_backup(db: Session | None = None) -> BackupRecord:
    started = time.perf_counter(); kind = _db_kind(); stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    ext = 'sqlite3' if kind == 'sqlite' else 'dump'; path = _backup_dir() / f'specforge_{stamp}.{ext}'
    job = OperationalJob(job_type='backup', status='running', started_at=utcnow())
    if db: db.add(job); db.commit(); db.refresh(job)
    try:
        if kind == 'sqlite':
            src = _sqlite_source(make_url(settings.DATABASE_URL))
            if not src.exists(): raise RuntimeError(f'SQLite database not found: {src}')
            src_con = sqlite3.connect(str(src)); dst_con = sqlite3.connect(str(path))
            try: src_con.backup(dst_con)
            finally: dst_con.close(); src_con.close()
        elif kind == 'postgresql':
            subprocess.run(['pg_dump', '--format=custom', '--file', str(path), settings.DATABASE_URL], check=True, capture_output=True, text=True, timeout=300)
        else: raise RuntimeError(f'Unsupported database backend: {kind}')
        verified, message = verify_backup(path, kind)
        record = BackupRecord(job_id=job.id if job else None, database_type=kind, path=str(path), status='success' if verified else 'unverified', size_bytes=path.stat().st_size, verified=verified, message=message)
        if db: db.add(record); job.status='success' if verified else 'warning'; job.output_path=str(path); job.message=message
    except Exception as exc:
        record = BackupRecord(job_id=job.id if job else None, database_type=kind, path=str(path), status='failed', message=str(exc))
        if db: db.add(record); job.status='failed'; job.message=str(exc)
    finally:
        elapsed=round((time.perf_counter()-started)*1000,2)
        if db: job.finished_at=utcnow(); job.duration_ms=elapsed; db.commit(); db.refresh(record)
    return record


def apply_retention(db: Session) -> dict:
    records=db.query(BackupRecord).filter(BackupRecord.status.in_(['success','unverified'])).order_by(BackupRecord.created_at.desc()).all()
    now=datetime.now(timezone.utc); keep=[]; deleted=0
    for i,r in enumerate(records):
        age=(now-r.created_at.replace(tzinfo=timezone.utc)).days
        if i < settings.BACKUP_RETENTION_COUNT and age <= settings.BACKUP_RETENTION_DAYS: keep.append(r); continue
        try:
            if os.path.exists(r.path): os.remove(r.path)
            r.retention_deleted=True; deleted += 1
        except OSError: pass
    db.commit(); return {'kept':len(keep),'deleted':deleted,'retention_days':settings.BACKUP_RETENTION_DAYS,'retention_count':settings.BACKUP_RETENTION_COUNT}


def backup_status(db: Session):
    latest=db.query(BackupRecord).order_by(BackupRecord.created_at.desc()).first()
    return {'configured':True,'database_type':_db_kind(),'backup_dir':str(_backup_dir()),'latest':latest}

