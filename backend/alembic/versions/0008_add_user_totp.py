from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0008_add_user_totp'
down_revision = '0007_add_jobs_table'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('users', sa.Column('totp_secret', sa.String(64), nullable=True))
    op.add_column('users', sa.Column('totp_enabled', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('users', sa.Column('totp_backup_codes', sa.String(2048), nullable=True))


def downgrade():
    op.drop_column('users', 'totp_backup_codes')
    op.drop_column('users', 'totp_enabled')
    op.drop_column('users', 'totp_secret')
