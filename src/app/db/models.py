from datetime import datetime
from typing import Optional, List

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import BigInteger, Integer, Boolean, JSON, DateTime
from sqlalchemy import (
    Text, JSON, DateTime, ForeignKey, CheckConstraint, String
)

from app.db.base import BaseDBT



class Chats(BaseDBT):
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True) # оригинальный от самого телеграма

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    admin_ids: Mapped[Optional[dict]] = mapped_column(JSON)

    last_poll_id: Mapped[Optional[int]] = mapped_column(Integer, default=None)

    history_version: Mapped[int] = mapped_column(Integer, default=1)

    polls: Mapped[List["Polls"]] = relationship(back_populates="chat")
    code_lines: Mapped[List["CodeLines"]] = relationship(back_populates="chat")
    # should_send_next_poll: Mapped[bool] = mapped_column(Boolean, default=False)

    def __repr__(self) -> str:
        return f"ChatsObj: id={self.id}, history_version={self.history_version}"


class Polls(BaseDBT):
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True) 

    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.id"), nullable=False) # оригинальный от самого телеграма

    tg_poll_id: Mapped[str] = mapped_column(Text, nullable=False) # оригинальный от самого телеграма
    tg_message_id: Mapped[int] = mapped_column(BigInteger)

    status: Mapped[str] = mapped_column(String(16), default="active")

    __table_args__ = (
        CheckConstraint(
            "status in ('active', 'closed', 'failed', 'rejected')",
            name="poll_status_check"
        ),
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    timeout_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    history_version: Mapped[int] = mapped_column(Integer, nullable=False)

    llm_request: Mapped[Optional[dict]] = mapped_column(JSON)
    llm_response: Mapped[Optional[dict]] = mapped_column(JSON)

    options: Mapped[List["PollOptions"]] = relationship(back_populates="poll")
    votes: Mapped[List["PollVotes"]] = relationship(back_populates="poll")
    chat: Mapped["Chats"] = relationship(back_populates="polls")
    code_line: Mapped[Optional["CodeLines"]] = relationship(back_populates="poll", uselist=False)


class PollOptions(BaseDBT):
    id: Mapped[int] = mapped_column(primary_key=True)

    poll_id: Mapped[int] = mapped_column(ForeignKey("polls.id"), nullable=False)

    index: Mapped[int] = mapped_column(Integer)  # 0..3
    code_line: Mapped[str] = mapped_column(Text)
    votes: Mapped[int] = mapped_column(Integer, default=0)

    poll: Mapped["Polls"] = relationship(back_populates="options")


class PollVotes(BaseDBT):
    id: Mapped[int] = mapped_column(primary_key=True)

    poll_id: Mapped[int] = mapped_column(ForeignKey("polls.id"))
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=True)

    option_index: Mapped[int] = mapped_column(Integer)
    answered_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    poll: Mapped["Polls"] = relationship(back_populates="votes")


class CodeLines(BaseDBT):
    id: Mapped[int] = mapped_column(primary_key=True)

    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.id"))
    poll_id: Mapped[int] = mapped_column(ForeignKey("polls.id"))

    line_number: Mapped[int] = mapped_column(Integer)
    code_line: Mapped[str] = mapped_column(Text)

    is_final: Mapped[bool] = mapped_column(Boolean, default=True)

    chat: Mapped["Chats"] = relationship(back_populates="code_lines")
    poll: Mapped["Polls"] = relationship(back_populates="code_line")


class CompletedCode(BaseDBT):
    id: Mapped[int] = mapped_column(primary_key=True)

    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.id"))
    history_version: Mapped[int] = mapped_column(Integer)

    code_text: Mapped[str] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    llm_request: Mapped[Optional[dict]] = mapped_column(JSON)
    llm_response: Mapped[Optional[dict]] = mapped_column(JSON)


class SchedulerState(BaseDBT):
    id: Mapped[int] = mapped_column(primary_key=True)  # всегда 1

    next_run_at: Mapped[datetime] = mapped_column(DateTime)
    uptime_started_at: Mapped[datetime] = mapped_column(DateTime)
    active_jobs: Mapped[dict] = mapped_column(JSON)


class Logs(BaseDBT):
    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    level: Mapped[str] = mapped_column(Text)
    message: Mapped[str] = mapped_column(Text)
    context: Mapped[Optional[dict]] = mapped_column(JSON)
