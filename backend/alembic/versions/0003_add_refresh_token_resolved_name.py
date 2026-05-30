from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0003_add_refresh_token_resolved_name'
down_revision = '0002_add_refresh_token_metadata'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('refresh_tokens', sa.Column('resolved_name', sa.String(255), nullable=True))


def downgrade():
    op.drop_column('refresh_tokens', 'resolved_name')
