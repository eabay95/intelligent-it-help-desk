from datetime import datetime
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, StringConstraints, field_validator, model_validator

Category = Literal["Network", "Hardware", "Software", "Account Access", "Other", "Unclassified"]
Priority = Literal["Low", "Medium", "High", "Critical"]
Status = Literal["Open", "In Progress", "Resolved"]
Impact = Literal["Individual", "Team", "Organization"]
Urgency = Literal["Routine", "Blocked"]
Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)]
Description = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=5000)]


class TicketCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: Title
    description: Description
    impact: Impact | None = None
    urgency: Urgency | None = None

    @field_validator("title", "description")
    @classmethod
    def reject_null_characters(cls, value: str) -> str:
        if "\0" in value:
            raise ValueError("Ticket text cannot contain null characters.")
        return value


class TicketUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Status | None = None
    category: Category | None = None
    priority: Priority | None = None

    @model_validator(mode="after")
    def require_fields(self) -> Self:
        fields = self.model_dump(exclude_unset=True)
        if not fields or any(value is None for value in fields.values()):
            raise ValueError("Provide at least one update field and use a valid value for each.")
        return self


class TicketRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    requester_id: UUID | None
    category: Category
    priority: Priority
    recommended_team: str
    status: Status
    classification_source: Literal["model", "fallback", "manual"]
    classification_confidence: float | None
    classification_model_version: str | None
    created_at: datetime
    updated_at: datetime
