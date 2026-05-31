from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0011_add_remote_machines'
down_revision = '0010_add_audit_logs_table'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'remote_machines',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('host', sa.String(length=255), nullable=False),
        sa.Column('port', sa.Integer(), nullable=False, server_default='22'),
        sa.Column('username', sa.String(length=128), nullable=False),
        sa.Column(
            'auth_type',
            sa.Enum('password', 'key', native_enum=False, length=16, name='sshauthtype'),
            nullable=False,
            server_default='password',
        ),
        sa.Column('encrypted_password', sa.Text(), nullable=True),
        sa.Column('ssh_key_path', sa.String(length=1024), nullable=True),
        sa.Column('download_folder', sa.String(length=1024), nullable=False),
        sa.Column('host_key_fingerprint', sa.String(length=512), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', name='uq_remote_machines_name'),
    )


def downgrade():
    op.drop_table('remote_machines')
