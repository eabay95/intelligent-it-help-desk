from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Response
from sqlalchemy import select, update, delete
from sqlalchemy.orm import Session

from app.api.auth import CurrentProfile, DB, require_employee, require_technician
from app.api.schemas import Category, Priority, Status, TicketCreate, TicketRead, TicketUpdate
from app.models.profile import Profile
from app.models.ticket import Ticket
from app.services.classifier import classify_ticket
from app.services.routing import TEAMS, initial_priority

router = APIRouter(prefix="/tickets", tags=["tickets"])
TicketID = Annotated[int, Path(gt=0, le=2_147_483_647)]


def find_ticket(ticket_id: int, db: Session) -> Ticket:
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(404, "Ticket not found.")
    return ticket


@router.post("", response_model=TicketRead, status_code=201)
def create_ticket(
    payload: TicketCreate,
    db: DB,
    employee: Annotated[Profile, Depends(require_employee)],
):
    ticket = Ticket(
        title=payload.title,
        description=payload.description,
        requester_id=employee.id,
        category="Unclassified",
        priority=initial_priority(payload.impact, payload.urgency),
        recommended_team=TEAMS["Unclassified"],
        status="Open",
        classification_source="fallback",
    )
    db.add(ticket)
    db.flush()
    ticket_id = ticket.id
    db.commit()

    prediction = classify_ticket(payload.title, payload.description)
    if prediction is not None:
        db.execute(
            update(Ticket)
            .where(Ticket.id == ticket_id, Ticket.classification_source == "fallback")
            .values(
                category=prediction.category,
                recommended_team=TEAMS[prediction.category],
                classification_source="model",
                classification_confidence=prediction.confidence,
                classification_model_version=prediction.model_version,
            )
        )
        db.commit()
    db.refresh(ticket)
    return ticket


@router.get("", response_model=list[TicketRead])
def list_tickets(
    db: DB,
    profile: CurrentProfile,
    status: Status | None = None,
    category: Category | None = None,
    priority: Priority | None = None,
):
    query = select(Ticket).order_by(Ticket.id.desc())
    if profile.role == "employee":
        query = query.where(Ticket.requester_id == profile.id)
    for field, value in (
        (Ticket.status, status),
        (Ticket.category, category),
        (Ticket.priority, priority),
    ):
        if value is not None:
            query = query.where(field == value)
    return db.scalars(query).all()


@router.get("/{ticket_id}", response_model=TicketRead)
def get_ticket(ticket_id: TicketID, db: DB, profile: CurrentProfile):
    ticket = find_ticket(ticket_id, db)
    if profile.role == "employee" and ticket.requester_id != profile.id:
        raise HTTPException(403, "You do not have access to this ticket.")
    return ticket


@router.patch(
    "/{ticket_id}", response_model=TicketRead, dependencies=[Depends(require_technician)]
)
def update_ticket(ticket_id: TicketID, payload: TicketUpdate, db: DB):
    ticket = find_ticket(ticket_id, db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(ticket, field, value)
    if payload.category is not None:
        ticket.classification_source = "manual"
        ticket.recommended_team = TEAMS[payload.category]
        ticket.classification_confidence = None
        ticket.classification_model_version = None
    db.commit()
    db.refresh(ticket)
    return ticket

@router.delete(
    "/{ticket_id}",
    status_code=204,
    dependencies=[Depends(require_technician)],
    responses={
        401: {"description": "Valid access token required"},
        403: {"description": "Technician access required"},
        404: {"description": "Ticket not found"},
    },
)
def delete_ticket(ticket_id: TicketID, db: DB) -> Response:
    deleted_id = db.scalar(delete(Ticket).where(Ticket.id == ticket_id).returning(Ticket.id))
    if deleted_id is None:
        raise HTTPException(404, "Ticket not found.")
    db.commit()
    return Response(status_code=204)