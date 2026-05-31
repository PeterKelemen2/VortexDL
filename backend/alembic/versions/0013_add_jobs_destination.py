from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0013_add_jobs_destination'
down_revision = '0012_add_user_remote_machines'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('jobs') as batch_op:
        batch_op.add_column(
            sa.Column(
                'destination_type',
                sa.String(length=16),
                nullable=False,
                server_default='local',
            )
        )
        batch_op.add_column(
            sa.Column('remote_machine_id', sa.Integer(), nullable=True)
        )
        batch_op.create_foreign_key(
            'fk_jobs_remote_machine_id',
            'remote_machines',
            ['remote_machine_id'],
            ['id'],
            ondelete='SET NULL',
        )


def downgrade():
    with op.batch_alter_table('jobs') as batch_op:
        batch_op.drop_constraint('fk_jobs_remote_machine_id', type_='foreignkey')
        batch_op.drop_column('remote_machine_id')
        batch_op.drop_column('destination_type')
