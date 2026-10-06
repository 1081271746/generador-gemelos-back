from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.database.database import get_db
from app.models.user import User
from app.schemas.negotiation import NegotiationCreate, NegotiationResponse
from app.services.negotiation_service import (
    create_negotiation,
    get_user_negotiations,
)

from app.services.negotiation_service import (
    create_negotiation,
    get_user_negotiations,
    get_negotiation_by_id,
)


router = APIRouter(
    prefix="/negotiations",
    tags=["Negotiations"],
)


@router.post(
    "/",
    response_model=NegotiationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_new_negotiation(
    negotiation_data: NegotiationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return create_negotiation(
            db,
            current_user.id,
            negotiation_data,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        )


@router.get(
    "/",
    response_model=list[NegotiationResponse],
)
def get_negotiations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_user_negotiations(
        db,
        current_user.id,
    )

@router.get(
    "/{negotiation_id}",
    response_model=NegotiationResponse,
)
def get_negotiation(
    negotiation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    negotiation = get_negotiation_by_id(
        db,
        negotiation_id,
        current_user.id,
    )

    if negotiation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Negotiation not found.",
        )

    return negotiation