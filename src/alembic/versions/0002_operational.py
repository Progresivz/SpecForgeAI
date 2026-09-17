"""Add operational job and backup history tables."""
from alembic import op
import sqlalchemy as sa

revision='0002_operational'; down_revision='0001_initial'; branch_labels=None; depends_on=None

def upgrade():
    bind=op.get_bind()
    insp=sa.inspect(bind)
    if 'operational_jobs' not in insp.get_table_names():
        op.create_table('operational_jobs', sa.Column('id',sa.Integer(),primary_key=True),sa.Column('job_type',sa.String(50),nullable=False),sa.Column('status',sa.String(30),nullable=False),sa.Column('started_at',sa.DateTime(),nullable=False),sa.Column('finished_at',sa.DateTime()),sa.Column('duration_ms',sa.Float()),sa.Column('output_path',sa.String(1000)),sa.Column('message',sa.Text(),nullable=False))
        op.create_index('ix_operational_jobs_id','operational_jobs',['id']); op.create_index('ix_operational_jobs_job_type','operational_jobs',['job_type']); op.create_index('ix_operational_jobs_status','operational_jobs',['status'])
    if 'backup_records' not in insp.get_table_names():
        op.create_table('backup_records', sa.Column('id',sa.Integer(),primary_key=True),sa.Column('job_id',sa.Integer()),sa.Column('database_type',sa.String(30),nullable=False),sa.Column('path',sa.String(1000),nullable=False),sa.Column('status',sa.String(30),nullable=False),sa.Column('size_bytes',sa.Integer(),nullable=False),sa.Column('verified',sa.Boolean(),nullable=False),sa.Column('retention_deleted',sa.Boolean(),nullable=False),sa.Column('created_at',sa.DateTime(),nullable=False),sa.Column('message',sa.Text(),nullable=False))
        for col in ['id','job_id','status']:
            op.create_index(f'ix_backup_records_{col}','backup_records',[col])

def downgrade():
    op.drop_table('backup_records'); op.drop_table('operational_jobs')
