from alembic import op
import sqlalchemy as sa


revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("username", sa.String(50), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False))
    for name in ("id", "username", "email"):
        op.create_index(f"ix_users_{name}", "users", [name], unique=name != "id")
    op.create_table("scenarios",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(150), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("context", sa.Text, nullable=False),
        sa.Column("objective", sa.Text, nullable=False),
        sa.Column("counterpart_role", sa.String(150), nullable=False),
        sa.Column("counterpart_goal", sa.Text, nullable=False),
        sa.Column("counterpart_limits", sa.Text, nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False))
    op.create_table("negotiations",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("scenario_id", sa.Integer, sa.ForeignKey("scenarios.id"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("started_at", sa.DateTime, nullable=False),
        sa.Column("ended_at", sa.DateTime, nullable=True))
    op.create_table("messages",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("negotiation_id", sa.Integer, sa.ForeignKey("negotiations.id"), nullable=False),
        sa.Column("sender_type", sa.String(20), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False))
    for table, columns in (("scenarios", ["id", "user_id"]), ("negotiations", ["id", "user_id", "scenario_id"]), ("messages", ["id", "negotiation_id"])):
        for column in columns:
            op.create_index(f"ix_{table}_{column}", table, [column])


def downgrade():
    for name in ("messages", "negotiations", "scenarios", "users"):
        op.drop_table(name)
