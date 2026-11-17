from fastapi import APIRouter, Request

from app.core.db import DB
from app.core.security import Officer
from app.schemas import LawAnswer, LawQuestion
from app.services.law import ask

router = APIRouter(prefix="/law")


@router.post("/ask", response_model=LawAnswer)
def ask_law(values: LawQuestion, request: Request, db: DB, user: Officer):
    return ask(db, values.question, request.app.state.llm)
