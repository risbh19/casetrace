from datetime import UTC, date, datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import (
    JSON,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    LargeBinary,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import TypeDecorator


class Embedding(TypeDecorator):
    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            from pgvector.sqlalchemy import Vector

            return dialect.type_descriptor(Vector(768))
        return dialect.type_descriptor(JSON())


def now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class Role(StrEnum):
    IO = "IO"
    SHO = "SHO"
    CO = "CO"
    SP = "SP"


class NoticeState(StrEnum):
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    SENT = "SENT"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(40), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    role: Mapped[Role] = mapped_column(Enum(Role, native_enum=False, create_constraint=True))
    station: Mapped[str] = mapped_column(String(40))
    password_hash: Mapped[str] = mapped_column(String(250))


class Case(Base):
    __tablename__ = "cases"

    id: Mapped[int] = mapped_column(primary_key=True)
    reference: Mapped[str] = mapped_column(String(40), unique=True)
    title: Mapped[str] = mapped_column(String(140))
    summary: Mapped[str] = mapped_column(Text)
    case_type: Mapped[str] = mapped_column(String(40), default="financial_fraud")
    station: Mapped[str] = mapped_column(String(40), index=True)
    assigned_to: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    opened_on: Mapped[date] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (UniqueConstraint("case_id", "sha256"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"), index=True)
    filename: Mapped[str] = mapped_column(String(200))
    media_type: Mapped[str] = mapped_column(String(60))
    sha256: Mapped[str] = mapped_column(String(64))
    size: Mapped[int]
    content: Mapped[bytes] = mapped_column(LargeBinary, deferred=True)
    text: Mapped[str] = mapped_column(Text)
    extraction_method: Mapped[str] = mapped_column(String(40))
    uploaded_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Entity(Base):
    __tablename__ = "extracted_entities"
    __table_args__ = (UniqueConstraint("document_id", "kind", "value"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), index=True)
    kind: Mapped[str] = mapped_column(String(25))
    value: Mapped[str] = mapped_column(String(160))
    method: Mapped[str] = mapped_column(String(20))


class LawSection(Base):
    __tablename__ = "law_sections"
    __table_args__ = (UniqueConstraint("act", "section"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    act: Mapped[str] = mapped_column(String(20))
    section: Mapped[str] = mapped_column(String(25))
    title: Mapped[str] = mapped_column(String(180))
    summary: Mapped[str] = mapped_column(Text)
    keywords: Mapped[list[str]] = mapped_column(JSON)
    source_url: Mapped[str] = mapped_column(String(400))
    source_page: Mapped[int | None]
    embedding: Mapped[list[float] | None] = mapped_column(Embedding())


class PlanStep(Base):
    __tablename__ = "plan_steps"
    __table_args__ = (UniqueConstraint("case_id", "step_key"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"), index=True)
    step_key: Mapped[str] = mapped_column(String(45))
    title: Mapped[str] = mapped_column(String(180))
    instructions: Mapped[str] = mapped_column(Text)
    legal_basis: Mapped[dict | None] = mapped_column(JSON)
    due_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(12), default="OPEN")


class Notice(Base):
    __tablename__ = "notices"

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"), index=True)
    kind: Mapped[str] = mapped_column(String(30))
    recipient: Mapped[str] = mapped_column(String(120))
    body: Mapped[str] = mapped_column(Text)
    status: Mapped[NoticeState] = mapped_column(
        Enum(NoticeState, native_enum=False, create_constraint=True), default=NoticeState.DRAFT
    )
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    approved_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (UniqueConstraint("case_id", "reference"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"), index=True)
    reference: Mapped[str] = mapped_column(String(50))
    from_acc: Mapped[str] = mapped_column(String(40))
    to_acc: Mapped[str] = mapped_column(String(40))
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    balance_remaining: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))


class Deadline(Base):
    __tablename__ = "deadlines"
    __table_args__ = (UniqueConstraint("case_id", "kind"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"), index=True)
    kind: Mapped[str] = mapped_column(String(35))
    anchor_date: Mapped[date] = mapped_column(Date)
    due_date: Mapped[date] = mapped_column(Date)
    basis: Mapped[str] = mapped_column(String(110))
    note: Mapped[str] = mapped_column(String(320))
    completed: Mapped[bool] = mapped_column(default=False)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    case_id: Mapped[int | None] = mapped_column(ForeignKey("cases.id"), index=True)
    action: Mapped[str] = mapped_column(String(80))
    entity: Mapped[str] = mapped_column(String(60))
    entity_id: Mapped[str | None] = mapped_column(String(60))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    payload: Mapped[dict] = mapped_column(JSON)
