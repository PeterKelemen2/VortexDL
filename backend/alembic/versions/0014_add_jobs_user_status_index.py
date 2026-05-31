"""Add composite index on jobs (user_id, status).

Job listings filter by user_id and optionally by status on every request; the
composite index avoids a full table scan as the jobs table grows.
"""
from alembic import op

# revision identifiers, used by Alembic.
revision = '0014_add_jobs_user_status_index'
down_revision = '0013_add_jobs_destination'
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(
        'ix_jobs_user_id_status', 'jobs', ['user_id', 'status']
    )


def downgrade():
    op.drop_index('ix_jobs_user_id_status', table_name='jobs')
