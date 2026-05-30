from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0004_add_user_images_table'
down_revision = '0003_add_refresh_token_resolved_name'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'user_images',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id'), nullable=False),
        sa.Column('file_path', sa.String(255), nullable=False),
        sa.Column('original_filename', sa.String(255), nullable=False),
        sa.Column('mime_type', sa.String(50), nullable=False),
        sa.Column('original_width', sa.Integer, nullable=True),
        sa.Column('original_height', sa.Integer, nullable=True),
        sa.Column('crop_x', sa.Float, nullable=True),
        sa.Column('crop_y', sa.Float, nullable=True),
        sa.Column('crop_size', sa.Float, nullable=True),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default=sa.text('0')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )


def downgrade():
    op.drop_table('user_images')
