from sqlalchemy import select, update
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.core.errors import DomainError, ExternalServiceError
from app.models import Analysis, User
from app.repositories.negotiation_repository import NegotiationRepository
from app.schemas.analysis import AnalysisResult, DIMENSION_NAMES
from app.services.event_service import record_event
from app.services.profile_service import rebuild_profile
from app.services.twin_service import build_twin_context


def validate_evidence(result: AnalysisResult, context) -> None:
    messages = {message.message_id: message.content for message in context.messages if message.sender_type == "user"}
    for name in DIMENSION_NAMES:
        for evidence in getattr(result.dimensions, name).evidence:
            if evidence.message_id not in messages or evidence.quote not in messages[evidence.message_id]:
                raise ExternalServiceError("AI returned evidence not found in the user's messages")


def prepare_analysis(db: Session, user_id: int, negotiation_id: int):
    negotiation = NegotiationRepository(db, user_id).negotiation(negotiation_id)
    existing = db.scalar(select(Analysis).where(Analysis.negotiation_id == negotiation_id, Analysis.user_id == user_id))
    if existing is not None:
        db.rollback()
        return existing, None
    if negotiation.status == "active":
        raise DomainError("Finish the negotiation before requesting analysis", 409)
    context = build_twin_context(db, user_id, negotiation_id)
    if not any(message.sender_type == "user" for message in context.messages):
        raise DomainError("Analysis requires user messages", 409)
    db.rollback()
    return None, context


def save_analysis(db: Session, user_id: int, negotiation_id: int, result: AnalysisResult):
    db.execute(update(User).where(User.id == user_id).values(username=User.username))
    existing = db.scalar(select(Analysis).where(Analysis.negotiation_id == negotiation_id, Analysis.user_id == user_id))
    if existing is not None:
        db.rollback()
        return existing
    analysis = Analysis(user_id=user_id, negotiation_id=negotiation_id, payload=result.model_dump())
    db.add(analysis)
    db.flush()
    rebuild_profile(db, user_id)
    record_event(db, user_id, negotiation_id, "analysis.completed", {"analysis_id": analysis.id})
    record_event(db, user_id, negotiation_id, "recommendation.created", {"analysis_id": analysis.id})
    record_event(db, user_id, negotiation_id, "profile.updated", {"analysis_id": analysis.id})
    db.commit()
    return analysis


async def analyze_negotiation(db: Session, user_id: int, negotiation_id: int, clients):
    existing, context = await run_in_threadpool(prepare_analysis, db, user_id, negotiation_id)
    if existing is not None:
        return existing
    result = await clients.analyze(context)
    validate_evidence(result, context)
    return await run_in_threadpool(save_analysis, db, user_id, negotiation_id, result)


def list_analyses(db: Session, user_id: int, offset: int = 0, limit: int = 50):
    return list(db.scalars(select(Analysis).where(Analysis.user_id == user_id).order_by(Analysis.id.desc()).offset(offset).limit(limit)))


def get_analysis(db: Session, user_id: int, analysis_id: int):
    analysis = db.scalar(select(Analysis).where(Analysis.id == analysis_id, Analysis.user_id == user_id))
    if analysis is None:
        raise DomainError("Analysis not found", 404)
    return analysis
