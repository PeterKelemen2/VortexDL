from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0012_add_user_remote_machines'
down_revision = '0011_add_remote_machines'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'user_remote_machines',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('remote_machine_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(
            ['remote_machine_id'], ['remote_machines.id'], ondelete='CASCADE'
        ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'user_id', 'remote_machine_id', name='uq_user_remote_machine'
        ),
    )
    op.create_index(
        'ix_user_remote_machines_user_id', 'user_remote_machines', ['user_id']
    )
    op.create_index(
        'ix_user_remote_machines_remote_machine_id',
        'user_remote_machines',
        ['remote_machine_id'],
    )


def downgrade():
    op.drop_index(
        'ix_user_remote_machines_remote_machine_id', table_name='user_remote_machines'
    )
    op.drop_index(
        'ix_user_remote_machines_user_id', table_name='user_remote_machines'
    )
    op.drop_table('user_remote_machines')
