"""Versioned incident aggregates, append-only audit and local runtime snapshots."""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("incidents", sa.Column("id", sa.String(64), primary_key=True), sa.Column("service_id", sa.String(128), nullable=False), sa.Column("state", sa.String(32), nullable=False), sa.Column("version", sa.Integer(), nullable=False), sa.Column("payload", sa.JSON(), nullable=False))
    op.create_index("ix_incidents_service_id", "incidents", ["service_id"])
    op.create_index("ix_incidents_state", "incidents", ["state"])
    op.create_table("audit_events", sa.Column("id", sa.String(64), primary_key=True), sa.Column("incident_id", sa.String(64)), sa.Column("payload", sa.JSON(), nullable=False))
    op.create_index("ix_audit_events_incident_id", "audit_events", ["incident_id"])
    op.create_table("runtime_state", sa.Column("key", sa.String(128), primary_key=True), sa.Column("payload", sa.JSON(), nullable=False))


def downgrade():
    op.drop_table("runtime_state")
    op.drop_table("audit_events")
    op.drop_table("incidents")
