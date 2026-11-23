"""Record external dispatch evidence and protect stored originals and audit events."""

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("notices") as batch:
        batch.add_column(sa.Column("delivery_channel", sa.String(30)))
        batch.add_column(sa.Column("delivery_reference", sa.String(120)))
        batch.add_column(sa.Column("delivery_evidence_id", sa.Integer()))
        batch.add_column(sa.Column("delivery_recorded_by", sa.Integer()))
        batch.create_foreign_key("fk_notice_delivery_evidence", "documents", ["delivery_evidence_id"], ["id"])
        batch.create_foreign_key("fk_notice_delivery_officer", "users", ["delivery_recorded_by"], ["id"])
    if op.get_context().dialect.name == "postgresql":
        op.execute("CREATE FUNCTION prevent_record_mutation() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'Original evidence and audit events are immutable'; END; $$")
        for table in ("documents", "audit_logs"):
            op.execute(f"CREATE TRIGGER immutable_{table} BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION prevent_record_mutation()")
    else:
        for table in ("documents", "audit_logs"):
            for action in ("UPDATE", "DELETE"):
                op.execute(f"CREATE TRIGGER immutable_{table}_{action.lower()} BEFORE {action} ON {table} BEGIN SELECT RAISE(ABORT, 'Original evidence and audit events are immutable'); END")


def downgrade():
    for table in ("documents", "audit_logs"):
        if op.get_context().dialect.name == "postgresql":
            op.execute(f"DROP TRIGGER immutable_{table} ON {table}")
        else:
            for action in ("update", "delete"):
                op.execute(f"DROP TRIGGER immutable_{table}_{action}")
    if op.get_context().dialect.name == "postgresql":
        op.execute("DROP FUNCTION prevent_record_mutation()")
    with op.batch_alter_table("notices") as batch:
        batch.drop_constraint("fk_notice_delivery_evidence", type_="foreignkey")
        batch.drop_constraint("fk_notice_delivery_officer", type_="foreignkey")
        for column in ("delivery_recorded_by", "delivery_evidence_id", "delivery_reference", "delivery_channel"):
            batch.drop_column(column)
