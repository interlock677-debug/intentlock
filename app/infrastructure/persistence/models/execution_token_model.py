from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.database import Base


class ExecutionTokenModel(Base):
    """ORM model for execution token tracking."""

    __tablename__ = "execution_tokens"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    jti: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    agent_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    tool: Mapped[str] = mapped_column(String(255), nullable=False)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_consumed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
