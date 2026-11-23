from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utc_now():
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Ticket(Base):
    __tablename__ = "tickets"
    __table_args__ = (CheckConstraint(
        "requester_id IS NOT NULL OR legacy_requester_id IS NOT NULL",
        name="ck_tickets_owner_or_legacy",
    ),)

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text)
    requester_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("profiles.id", name="fk_tickets_requester", ondelete="RESTRICT"), index=True
    )
    legacy_requester_id: Mapped[str | None] = mapped_column(String(64))
    category: Mapped[str] = mapped_column(String(40))
    priority: Mapped[str] = mapped_column(String(12))
    recommended_team: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(20))
    classification_source: Mapped[str] = mapped_column(String(12))
    classification_confidence: Mapped[float | None]
    classification_model_version: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
