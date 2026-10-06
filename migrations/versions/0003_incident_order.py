"""Order incidents chronologically before applying database pagination."""
import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("incidents", sa.Column("started_at", sa.DateTime(timezone=True), nullable=True))
    if op.get_bind().dialect.name == "sqlite":
        op.execute("UPDATE incidents SET started_at = strftime('%Y-%m-%d %H:%M:%f', json_extract(payload, '$.started_at'))")
    else:
        op.execute("UPDATE incidents SET started_at = CAST(payload->>'started_at' AS TIMESTAMP WITH TIME ZONE)")
    with op.batch_alter_table("incidents") as batch:
        batch.alter_column("started_at", existing_type=sa.DateTime(timezone=True), nullable=False)
        batch.create_index("ix_incidents_started_at", ["started_at"])


def downgrade():
    with op.batch_alter_table("incidents") as batch:
        batch.drop_index("ix_incidents_started_at")
        batch.drop_column("started_at")
