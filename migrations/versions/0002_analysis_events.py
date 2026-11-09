from alembic import op
import sqlalchemy as sa


revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("token_version", sa.Integer, nullable=False, server_default="0"))
    op.add_column("negotiations", sa.Column("scenario_snapshot", sa.JSON, nullable=False, server_default="{}"))
    op.add_column("negotiations", sa.Column("result", sa.Text, nullable=True))
    op.add_column("negotiations", sa.Column("processing_token", sa.String(36), nullable=True))
    op.add_column("negotiations", sa.Column("processing_until", sa.DateTime, nullable=True))
    op.add_column("messages", sa.Column("kind", sa.String(30), nullable=False, server_default="argument"))
    op.add_column("messages", sa.Column("request_id", sa.String(36), nullable=True))
    with op.batch_alter_table("messages") as batch:
        batch.create_unique_constraint("uq_messages_request_sender", ["negotiation_id", "request_id", "sender_type"])
    op.create_table("analyses",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("negotiation_id", sa.Integer, sa.ForeignKey("negotiations.id"), nullable=False, unique=True),
        sa.Column("payload", sa.JSON, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False))
    op.create_index("ix_analyses_user_id", "analyses", ["user_id"])
    op.create_table("negotiator_profiles",
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("payload", sa.JSON, nullable=False),
        sa.Column("sample_count", sa.Integer, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False))
    op.create_table("events",
        sa.Column("sequence", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("event_id", sa.String(36), nullable=False, unique=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("negotiation_id", sa.Integer, sa.ForeignKey("negotiations.id"), nullable=False),
        sa.Column("event_type", sa.String(60), nullable=False),
        sa.Column("payload", sa.JSON, nullable=False),
        sa.Column("delivered", sa.Boolean, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False))
    for column in ("user_id", "negotiation_id", "delivered"):
        op.create_index(f"ix_events_{column}", "events", [column])
    connection = op.get_bind()
    rows = connection.execute(sa.text("SELECT n.id, s.title, s.description, s.context, s.objective, s.counterpart_role, s.counterpart_goal, s.counterpart_limits FROM negotiations n JOIN scenarios s ON s.id=n.scenario_id")).mappings()
    table = sa.table("negotiations", sa.column("id", sa.Integer), sa.column("scenario_snapshot", sa.JSON))
    for row in rows:
        snapshot = {key: value for key, value in row.items() if key != "id"}
        connection.execute(table.update().where(table.c.id == row["id"]).values(scenario_snapshot=snapshot))


def downgrade():
    for table in ("events", "negotiator_profiles", "analyses"):
        op.drop_table(table)
    with op.batch_alter_table("messages") as batch:
        batch.drop_constraint("uq_messages_request_sender", type_="unique")
        batch.drop_column("request_id")
        batch.drop_column("kind")
    with op.batch_alter_table("negotiations") as batch:
        for column in ("processing_until", "processing_token", "result", "scenario_snapshot"):
            batch.drop_column(column)
    with op.batch_alter_table("users") as batch:
        batch.drop_column("token_version")
