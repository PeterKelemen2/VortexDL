from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column
from sqlalchemy import String

"""initial

Revision ID: 0001_initial
Revises: 
Create Date: 2026-05-19 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0001_initial'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "roles",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(32), unique=True, nullable=False),
        sa.Column("description", sa.String(255)),
    )
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("username", sa.String(64), unique=True, nullable=False),
        sa.Column("email", sa.String(255), unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("role_id", sa.Integer, sa.ForeignKey("roles.id"), nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
    )
    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("token_hash", sa.String(255), nullable=False),
        sa.Column("expires_at", sa.DateTime, nullable=False),
        sa.Column("revoked", sa.Boolean, default=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("last_used_at", sa.DateTime),
    )
    # Seed roles
    roles_table = table(
        'roles',
        column('name', String),
        column('description', String)
    )
    conn = op.get_bind()
    existing_roles = [row[0] for row in conn.execute(sa.text("SELECT name FROM roles")).fetchall()]
    for name, desc in [("admin", "Administrator role"), ("user", "Default user role")]:
        if name not in existing_roles:
            op.execute(roles_table.insert().values(name=name, description=desc))

def downgrade():
    op.drop_table("refresh_tokens")
    op.drop_table("users")
    op.drop_table("roles")
