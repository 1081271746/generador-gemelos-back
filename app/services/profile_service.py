from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Analysis, NegotiatorProfile
from app.schemas.analysis import DIMENSION_NAMES


def rebuild_profile(db: Session, user_id: int) -> NegotiatorProfile:
    analyses = list(db.scalars(select(Analysis).where(Analysis.user_id == user_id).order_by(Analysis.id)))
    count = len(analyses)
    averages = {name: round(sum(item.payload["dimensions"][name]["score"] for item in analyses) / count, 2)
        for name in DIMENSION_NAMES} if count else {}
    payload = {
        "interpretation": "contextual_indicators",
        "dimension_averages": averages,
        "strategies": sorted({value for item in analyses for value in item.payload["strategies"]}),
        "strengths": sorted({value for item in analyses for value in item.payload["strengths"]}),
        "improvement_areas": sorted({value for item in analyses for value in item.payload["improvement_areas"]}),
        "recommendations": analyses[-1].payload["recommendations"] if analyses else [],
        "exercises": analyses[-1].payload["exercises"] if analyses else [],
        "evolution": [{"analysis_id": item.id, "negotiation_id": item.negotiation_id,
            "created_at": item.created_at.isoformat(),
            "dimensions": {name: item.payload["dimensions"][name]["score"] for name in DIMENSION_NAMES}} for item in analyses],
    }
    profile = db.get(NegotiatorProfile, user_id)
    if profile is None:
        profile = NegotiatorProfile(user_id=user_id)
        db.add(profile)
    profile.payload = payload
    profile.sample_count = count
    profile.updated_at = datetime.utcnow()
    db.flush()
    return profile


def get_profile(db: Session, user_id: int) -> dict:
    profile = db.get(NegotiatorProfile, user_id)
    if profile is None:
        return {"sample_count": 0, "payload": {"interpretation": "contextual_indicators", "evolution": []}}
    return {"sample_count": profile.sample_count, "payload": profile.payload, "updated_at": profile.updated_at}
