"""Create investigation tables."""

import sqlalchemy as sa
from alembic import op


revision = '0001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    embedding = sa.JSON()
    if op.get_context().dialect.name == "postgresql":
        from pgvector.sqlalchemy import Vector

        op.execute("CREATE EXTENSION IF NOT EXISTS vector")
        embedding = Vector(768)
    op.create_table('law_sections',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('act', sa.String(length=20), nullable=False),
    sa.Column('section', sa.String(length=25), nullable=False),
    sa.Column('title', sa.String(length=180), nullable=False),
    sa.Column('summary', sa.Text(), nullable=False),
    sa.Column('keywords', sa.JSON(), nullable=False),
    sa.Column('source_url', sa.String(length=400), nullable=False),
    sa.Column('source_page', sa.Integer(), nullable=True),
    sa.Column('embedding', embedding, nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('act', 'section')
    )
    op.create_table('users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('username', sa.String(length=40), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('role', sa.Enum('IO', 'SHO', 'CO', 'SP', name='role', native_enum=False, create_constraint=True), nullable=False),
    sa.Column('station', sa.String(length=40), nullable=False),
    sa.Column('password_hash', sa.String(length=250), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('username')
    )
    op.create_table('cases',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('reference', sa.String(length=40), nullable=False),
    sa.Column('title', sa.String(length=140), nullable=False),
    sa.Column('summary', sa.Text(), nullable=False),
    sa.Column('case_type', sa.String(length=40), nullable=False),
    sa.Column('station', sa.String(length=40), nullable=False),
    sa.Column('assigned_to', sa.Integer(), nullable=False),
    sa.Column('opened_on', sa.Date(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['assigned_to'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('reference')
    )
    with op.batch_alter_table('cases', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_cases_assigned_to'), ['assigned_to'], unique=False)
        batch_op.create_index(batch_op.f('ix_cases_station'), ['station'], unique=False)

    op.create_table('audit_logs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('case_id', sa.Integer(), nullable=True),
    sa.Column('action', sa.String(length=80), nullable=False),
    sa.Column('entity', sa.String(length=60), nullable=False),
    sa.Column('entity_id', sa.String(length=60), nullable=True),
    sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
    sa.Column('payload', sa.JSON(), nullable=False),
    sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('audit_logs', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_audit_logs_case_id'), ['case_id'], unique=False)

    op.create_table('deadlines',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('case_id', sa.Integer(), nullable=False),
    sa.Column('kind', sa.String(length=35), nullable=False),
    sa.Column('anchor_date', sa.Date(), nullable=False),
    sa.Column('due_date', sa.Date(), nullable=False),
    sa.Column('basis', sa.String(length=110), nullable=False),
    sa.Column('note', sa.String(length=320), nullable=False),
    sa.Column('completed', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('case_id', 'kind')
    )
    with op.batch_alter_table('deadlines', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_deadlines_case_id'), ['case_id'], unique=False)

    op.create_table('documents',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('case_id', sa.Integer(), nullable=False),
    sa.Column('filename', sa.String(length=200), nullable=False),
    sa.Column('media_type', sa.String(length=60), nullable=False),
    sa.Column('sha256', sa.String(length=64), nullable=False),
    sa.Column('size', sa.Integer(), nullable=False),
    sa.Column('content', sa.LargeBinary(), nullable=False),
    sa.Column('text', sa.Text(), nullable=False),
    sa.Column('extraction_method', sa.String(length=40), nullable=False),
    sa.Column('uploaded_by', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ),
    sa.ForeignKeyConstraint(['uploaded_by'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('case_id', 'sha256')
    )
    with op.batch_alter_table('documents', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_documents_case_id'), ['case_id'], unique=False)

    op.create_table('notices',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('case_id', sa.Integer(), nullable=False),
    sa.Column('kind', sa.String(length=30), nullable=False),
    sa.Column('recipient', sa.String(length=120), nullable=False),
    sa.Column('body', sa.Text(), nullable=False),
    sa.Column('status', sa.Enum('DRAFT', 'APPROVED', 'SENT', name='noticestate', native_enum=False, create_constraint=True), nullable=False),
    sa.Column('created_by', sa.Integer(), nullable=False),
    sa.Column('approved_by', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['approved_by'], ['users.id'], ),
    sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('notices', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_notices_case_id'), ['case_id'], unique=False)

    op.create_table('plan_steps',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('case_id', sa.Integer(), nullable=False),
    sa.Column('step_key', sa.String(length=45), nullable=False),
    sa.Column('title', sa.String(length=180), nullable=False),
    sa.Column('instructions', sa.Text(), nullable=False),
    sa.Column('legal_basis', sa.JSON(), nullable=True),
    sa.Column('due_date', sa.Date(), nullable=False),
    sa.Column('status', sa.String(length=12), nullable=False),
    sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('case_id', 'step_key')
    )
    with op.batch_alter_table('plan_steps', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_plan_steps_case_id'), ['case_id'], unique=False)

    op.create_table('transactions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('case_id', sa.Integer(), nullable=False),
    sa.Column('reference', sa.String(length=50), nullable=False),
    sa.Column('from_acc', sa.String(length=40), nullable=False),
    sa.Column('to_acc', sa.String(length=40), nullable=False),
    sa.Column('amount', sa.Numeric(precision=14, scale=2), nullable=False),
    sa.Column('ts', sa.DateTime(timezone=True), nullable=False),
    sa.Column('balance_remaining', sa.Numeric(precision=14, scale=2), nullable=True),
    sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('case_id', 'reference')
    )
    with op.batch_alter_table('transactions', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_transactions_case_id'), ['case_id'], unique=False)

    op.create_table('extracted_entities',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('document_id', sa.Integer(), nullable=False),
    sa.Column('kind', sa.String(length=25), nullable=False),
    sa.Column('value', sa.String(length=160), nullable=False),
    sa.Column('method', sa.String(length=20), nullable=False),
    sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('document_id', 'kind', 'value')
    )
    with op.batch_alter_table('extracted_entities', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_extracted_entities_document_id'), ['document_id'], unique=False)

def downgrade():
    with op.batch_alter_table('extracted_entities', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_extracted_entities_document_id'))

    op.drop_table('extracted_entities')
    with op.batch_alter_table('transactions', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_transactions_case_id'))

    op.drop_table('transactions')
    with op.batch_alter_table('plan_steps', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_plan_steps_case_id'))

    op.drop_table('plan_steps')
    with op.batch_alter_table('notices', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_notices_case_id'))

    op.drop_table('notices')
    with op.batch_alter_table('documents', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_documents_case_id'))

    op.drop_table('documents')
    with op.batch_alter_table('deadlines', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_deadlines_case_id'))

    op.drop_table('deadlines')
    with op.batch_alter_table('audit_logs', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_audit_logs_case_id'))

    op.drop_table('audit_logs')
    with op.batch_alter_table('cases', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_cases_station'))
        batch_op.drop_index(batch_op.f('ix_cases_assigned_to'))

    op.drop_table('cases')
    op.drop_table('users')
    op.drop_table('law_sections')
