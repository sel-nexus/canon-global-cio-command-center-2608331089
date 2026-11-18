"""Expose authenticated executive assistant operations."""
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.routers.auth import current_session
from app.schemas.ai import ChatRequest, ChatResponse, Recommendation, Tab
from app.services.ai import chat, recommendations

router = APIRouter(prefix='/api/v1/ai', tags=['assistant'], dependencies=[Depends(current_session)])


@router.get('/recommendations', response_model=list[Recommendation])
def get_recommendations(context_tab: Tab = 'strategic') -> list[Recommendation]:
    """Offer starter questions appropriate to the requested tab."""
    return recommendations(context_tab)


@router.post('/chat', response_model=ChatResponse)
def post_chat(request: ChatRequest, db: Annotated[Session, Depends(get_db)]) -> ChatResponse:
    """Generate an evidence-scoped analysis through the configured provider."""
    return chat(db, request)
