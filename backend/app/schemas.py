from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.models import NoticeState, Role

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=140)]
Reference = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,39}$")]
Amount = Annotated[Decimal, Field(gt=0, max_digits=14, decimal_places=2)]
Balance = Annotated[Decimal, Field(ge=0, max_digits=14, decimal_places=2)]
NoticeKind = Literal["bank_statement", "bank_freeze", "telecom_cdr"]
PlanState = Literal["OPEN", "DONE"]
CustodyBand = Literal["other_offence", "death_life_or_ten_years_or_more"]


class FromDB(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Login(BaseModel):
    username: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=40)]
    password: str = Field(min_length=1, max_length=128)


class OfficerView(FromDB):
    id: int
    username: str
    name: str
    role: Role
    station: str


class LoginView(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    officer: OfficerView


class CaseCreate(BaseModel):
    reference: Reference
    title: Name
    summary: str = Field(min_length=1, max_length=4000)
    opened_on: date

    @model_validator(mode="after")
    def validate_opening_date(self):
        if self.opened_on > date.today():
            raise ValueError("Opening date cannot be in the future")
        return self


class CaseView(FromDB):
    id: int
    reference: str
    title: str
    summary: str
    case_type: str
    opened_on: date
    station: str
    assigned_to: int


class EntityView(FromDB):
    kind: str
    value: str
    method: str


class DocumentView(FromDB):
    id: int
    filename: str
    media_type: str
    sha256: str
    size: int
    extraction_method: str
    created_at: datetime


class DocumentDetail(DocumentView):
    text: str
    entities: list[EntityView]


class Citation(BaseModel):
    act: str
    section: str
    title: str
    summary: str
    source_url: str
    source_page: int | None = None


class LawQuestion(BaseModel):
    question: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=700)]


class LawAnswer(BaseModel):
    status: Literal["grounded", "unsure"]
    answer: str
    citations: list[Citation]


class PlanStepView(FromDB):
    id: int
    title: str
    instructions: str
    legal_basis: Citation | Literal["unsure"]
    due_date: date
    status: PlanState


class PlanUpdate(BaseModel):
    status: PlanState


class NoticeCreate(BaseModel):
    kind: NoticeKind
    recipient: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
    facts: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1200)]


class NoticeView(FromDB):
    id: int
    kind: NoticeKind
    recipient: str
    body: str
    status: NoticeState
    created_by: int
    approved_by: int | None
    created_at: datetime
    approved_at: datetime | None
    sent_at: datetime | None


class TransactionCreate(BaseModel):
    reference: Reference
    from_acc: Reference
    to_acc: Reference
    amount: Amount
    ts: AwareDatetime
    balance_remaining: Balance | None = None

    @model_validator(mode="after")
    def distinct_accounts(self):
        if self.from_acc == self.to_acc:
            raise ValueError("Source and destination account must differ")
        self.ts = self.ts.astimezone(UTC)
        return self


class DeadlineInputs(BaseModel):
    custody_on: date | None = None
    custody_band: CustodyBand | None = None
    supervisor_report_due: date | None = None

    @model_validator(mode="after")
    def require_custody_details(self):
        if (self.custody_on is None) != (self.custody_band is None):
            raise ValueError("Custody date and reviewed offence band must be supplied together")
        return self


class DeadlineUpdate(BaseModel):
    completed: bool


class DeadlineView(FromDB):
    id: int
    kind: str
    anchor_date: date
    due_date: date
    basis: str
    note: str
    completed: bool


class AuditView(FromDB):
    id: int
    user_id: int | None
    action: str
    entity: str
    entity_id: str | None
    timestamp: datetime
    payload: dict
