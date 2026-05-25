from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0005_add_user_image_variant_paths'
down_revision = '0004_add_user_images_table'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('user_images', sa.Column('avatar_path', sa.String(255), nullable=True))
    op.add_column('user_images', sa.Column('thumbnail_path', sa.String(255), nullable=True))
    op.add_column('user_images', sa.Column('preview_path', sa.String(255), nullable=True))


def downgrade():
    op.drop_column('user_images', 'preview_path')
    op.drop_column('user_images', 'thumbnail_path')
    op.drop_column('user_images', 'avatar_path')
