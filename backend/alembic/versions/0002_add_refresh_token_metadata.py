from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0002_add_refresh_token_metadata'
down_revision = '0001_initial'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('refresh_tokens', sa.Column('device_os', sa.String(32), nullable=True))
    op.add_column('refresh_tokens', sa.Column('device_name', sa.String(255), nullable=True))
    op.add_column('refresh_tokens', sa.Column('user_agent', sa.String(1024), nullable=True))


def downgrade():
    op.drop_column('refresh_tokens', 'user_agent')
    op.drop_column('refresh_tokens', 'device_name')
    op.drop_column('refresh_tokens', 'device_os')
