from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base, _new_uuid


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_new_uuid)
    google_id: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    lang: Mapped[str] = mapped_column(String, default="es")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Player(Base):
    __tablename__ = "players"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_new_uuid)
    user_id: Mapped[str | None] = mapped_column(String, nullable=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    telegram_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    token: Mapped[str] = mapped_column(String, unique=True, nullable=False, default=_new_uuid)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class GameSession(Base):
    __tablename__ = "game_sessions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_new_uuid)
    user_id: Mapped[str | None] = mapped_column(String, nullable=True)
    category: Mapped[str] = mapped_column(String, nullable=False)
    mode: Mapped[str] = mapped_column(String, nullable=False)
    difficulty: Mapped[str] = mapped_column(String, nullable=False)
    n_impostors: Mapped[int] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    results: Mapped[list["GamePlayerResult"]] = relationship(
        "GamePlayerResult", back_populates="session", cascade="all, delete-orphan"
    )


class GamePlayerResult(Base):
    __tablename__ = "game_player_results"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_new_uuid)
    session_id: Mapped[str] = mapped_column(
        String, ForeignKey("game_sessions.id", ondelete="CASCADE"), nullable=False
    )
    player_id: Mapped[str] = mapped_column(
        String, ForeignKey("players.id", ondelete="CASCADE"), nullable=False
    )
    player_name: Mapped[str] = mapped_column(String, nullable=False)
    is_impostor: Mapped[bool] = mapped_column(Boolean, nullable=False)
    category_shown: Mapped[str] = mapped_column(String, nullable=False)
    # Curated (or LLM) hint given to the impostor. Null when there is none.
    hint: Mapped[str | None] = mapped_column(String, nullable=True)

    session: Mapped["GameSession"] = relationship("GameSession", back_populates="results")
