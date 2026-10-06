"""Transactional event outbox for retryable cloud delivery."""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("event_outbox",sa.Column("id",sa.String(64),primary_key=True),sa.Column("delivered",sa.Boolean(),nullable=False),sa.Column("payload",sa.JSON(),nullable=False))
    op.create_index("ix_event_outbox_delivered","event_outbox",["delivered"])


def downgrade():
    op.drop_table("event_outbox")
