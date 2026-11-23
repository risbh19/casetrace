"""Store original statutory pages and their provenance."""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("law_pages", sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("act", sa.String(20), nullable=False), sa.Column("page", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False), sa.Column("source_url", sa.String(400), nullable=False),
        sa.Column("source_sha256", sa.String(64), nullable=False), sa.Column("retrieved_on", sa.Date(), nullable=False),
        sa.UniqueConstraint("act", "page"))
    op.create_index("ix_law_pages_act", "law_pages", ["act"])


def downgrade():
    op.drop_index("ix_law_pages_act", "law_pages")
    op.drop_table("law_pages")
