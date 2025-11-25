from __future__ import annotations

from datetime import datetime
from typing import Sequence, Optional

from sqlalchemy import (
    select,
    update,
    func,
    delete,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    Chats,
    Polls,
    PollOptions,
    PollVotes,
    CodeLines,
    CompletedCode,
    SchedulerState,
    Logs)

# =========================
# Chats
# =========================

class ChatsRepository:
    """Работа с чатами и их состоянием (история, активный опрос)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_or_create_chat(self, chat_id: int) -> Chats:
        """Получить чат, если нет – создать."""
        result = await self.session.execute(
            select(Chats).where(Chats.id == chat_id)
        )
        chat = result.scalar_one_or_none()
        if chat is None:
            chat = Chats(id=chat_id)
            self.session.add(chat)
        return chat

    async def get_chat(self, chat_id: int) -> Optional[Chats]:
        result = await self.session.execute(
            select(Chats).where(Chats.id == chat_id)
        )
        return result.scalar_one_or_none()

    async def reset_history(self, chat_id: int) -> Chats:
        """
        /start: очистка истории конкретного чата.
        Логика: инкремент history_version, сброс last_poll_id.
        Фактические данные не удаляем – просто работаем с новой версией.
        """
        chat = await self.get_or_create_chat(chat_id)
        print("CHAT OBJ", chat)
        # # TODO убрать?
        chat.history_version += 1
        print("CHAT OBJ AFTER", chat)

        chat.last_poll_id = None
        chat.updated_at = datetime.now()
        return chat

    async def set_last_poll(self, chat_id: int, poll_id: Optional[int]) -> None:
        await self.session.execute(
            update(Chats)
            .where(Chats.id == chat_id)
            .values(last_poll_id=poll_id, updated_at=datetime.now())
        )

    async def set_admin_ids(self, chat_id: int, admin_ids: list[int]) -> None:
        chat = await self.get_or_create_chat(chat_id)
        chat.admin_ids = {"admins": admin_ids}
        chat.updated_at = datetime.now()


# =========================
# Polls, options, votes
# =========================

class PollsRepository:
    """Создание/закрытие опросов, варианты и голоса."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_poll(
        self,
        chat: Chats,
        options: Sequence[str],
        tg_poll_id: str,
        tg_message_id: int,
        timeout_at: Optional[datetime],
        llm_request: Optional[dict] = None,
        llm_response: Optional[dict] = None,
    ) -> Polls:
        """
        Создание опроса + 4 варианта.
        history_version берём из чата.
        """
        poll = Polls(
            chat_id=chat.id,
            tg_poll_id=tg_poll_id,
            tg_message_id=tg_message_id,
            status="active",
            created_at=datetime.now(),
            timeout_at=timeout_at,
            history_version=chat.history_version,
            llm_request=llm_request,
            llm_response=llm_response,
        )
        self.session.add(poll)
        await self.session.flush()  # чтобы появился poll.id

        for idx, line in enumerate(options):
            self.session.add(
                PollOptions(
                    poll_id=poll.id,
                    index=idx,
                    code_line=line,
                    votes=0,
                )
            )

        # заодно обновим last_poll_id
        chat.last_poll_id = poll.id
        chat.updated_at = datetime.now()

        return poll

    async def get_poll_by_tg_id(self, tg_poll_id: str) -> Optional[Polls]:
        result = await self.session.execute(
            select(Polls).where(Polls.tg_poll_id == tg_poll_id)
        )
        return result.scalar_one_or_none()

    async def get_poll_with_options(self, poll_id: int) -> Optional[Polls]:
        """
        Вернуть опрос с подгруженными options (через relationship lazy='selectin' в настройке).
        """
        result = await self.session.execute(
            select(Polls)
            .where(Polls.id == poll_id)
            .options()
        )
        return result.scalar_one_or_none()
    
    async def get_poll_by_id(self, poll_id: int) -> Optional[Polls]:
        """
        Вернуть опрос с подгруженными options (через relationship lazy='selectin' в настройке).
        """
        result = await self.session.execute(
            select(Polls)
            .where(Polls.id == poll_id)
        )
        return result.scalar_one_or_none()

    async def get_active_poll_for_chat(self, chat_id: int) -> Optional[Polls]:
        result = await self.session.execute(
            select(Polls)
            .where(
                Polls.chat_id == chat_id,
                Polls.status == "active",
            )
            .order_by(Polls.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
    
    async def reject_poll_if_active_by_poll_id(self, poll_id: int) -> None:
        poll = await self.get_poll_by_id(poll_id=poll_id)
        if poll and poll.status == "active":
            poll.status = "rejected"
            self.session.add(poll)
            await self.session.commit()
        return None
        

    async def close_poll(
        self,
        poll: Polls,
        status: str = "closed", # active / closed / rejected
    ) -> None:
        """Закрываем опрос (по таймеру или команде)."""
        if poll:
            poll.status = status
            poll.closed_at = datetime.now()

    # ----- Votes -----

    async def add_or_update_vote(
        self,
        poll_id: int,
        user_id: int,
        option_index: int,
    ) -> None:
        """
        Добавить или обновить голос пользователя.
        Бэкенд-агностично (SQLite + Postgres): сначала ищем, затем обновляем/создаём.
        """
        if user_id:
            result = await self.session.execute(
                select(PollVotes)
                .where(
                    PollVotes.poll_id == poll_id,
                    PollVotes.user_id == user_id,
                )
            )
            vote = result.scalar_one_or_none()

            now = datetime.now()

            if vote is None:
                vote = PollVotes(
                    poll_id=poll_id,
                    user_id=user_id,
                    option_index=option_index,
                    answered_at=now,
                )
                self.session.add(vote)
            else:
                vote.option_index = option_index
                vote.answered_at = now
        else:
            vote = PollVotes(
                    poll_id=poll_id,
                    user_id=user_id,
                    option_index=option_index,
                    answered_at=now,
                )
            self.session.add(vote)


    async def recalc_votes_for_poll(self, poll_id: int) -> None:
        """
        Пересчёт счётчиков options.votes по poll_votes.
        Полезно при рестарте: на всякий случай синхронизировать агрегаты.
        """
        # Считаем голоса по вариантам
        result = await self.session.execute(
            select(
                PollVotes.option_index,
                func.count(PollVotes.id),
            )
            .where(PollVotes.poll_id == poll_id)
            .group_by(PollVotes.option_index)
        )
        counts = {row.option_index: row[1] for row in result.all()}

        # Обновляем options
        opts_result = await self.session.execute(
            select(PollOptions).where(PollOptions.poll_id == poll_id)
        )
        options = opts_result.scalars().all()

        for opt in options:
            opt.votes = counts.get(opt.index, 0)
    
    async def update_telegram_ids(
        self,
        poll_id: int,
        tg_poll_id: str,
        tg_message_id: int,
    ) -> bool:
        """
        Привязать реальные tg_poll_id и message_id после отправки опроса.
        Возвращает True, если poll найден.
        """
        result = await self.session.execute(
            select(Polls).where(Polls.id == poll_id)
        )
        poll = result.scalar_one_or_none()
        if not poll:
            return False

        poll.tg_poll_id = tg_poll_id
        poll.tg_message_id = tg_message_id

        return True

    async def get_winner(self, poll_id: int) -> PollOptions:
        """
        Возвращает победившую опцию.
        Перед этим стоит вызвать recalc_votes_for_poll().
        """

        result = await self.session.execute(
            select(PollOptions)
            .where(PollOptions.poll_id == poll_id)
            .order_by(PollOptions.votes.desc())
            .limit(1)
        )

        winner = result.scalar_one_or_none()
        return winner

# =========================
# CodeLines / текущий код
# =========================

class CodeRepository:
    """Работа с текущим кодом чата (строки + выбор победителей)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def append_code_line_from_poll(
        self,
        chat: Chats,
        poll: Polls,
        winning_option_index: int,
    ) -> CodeLines:
        """
        Добавить победившую строку в code_lines.
        line_number = макс+1 в рамках текущей history_version.
        """
        # найдём победившую опцию
        result = await self.session.execute(
            select(PollOptions)
            .where(
                PollOptions.poll_id == poll.id,
                PollOptions.index == winning_option_index,
            )
            .limit(1)
        )
        option = result.scalar_one_or_none()
        if option is None:
            raise ValueError("Winning PollOption not found")

        # считаем текущий max line_number по актуальной истории
        # через join с Polls, чтобы учитывать history_version
        result = await self.session.execute(
            select(func.max(CodeLines.line_number))
            .join(Polls, CodeLines.poll_id == Polls.id)
            .where(
                CodeLines.chat_id == chat.id,
                Polls.history_version == chat.history_version,
            )
        )
        max_line_number = result.scalar_one() or 0
        line_number = max_line_number + 1

        code_line = CodeLines(
            chat_id=chat.id,
            poll_id=poll.id,
            line_number=line_number,
            code_line=option.code_line,
            is_final=True,
        )
        self.session.add(code_line)
        return code_line

    async def get_current_code(
        self,
        chat: Chats,
    ) -> list[str]:
        """
        Вернуть текущий код как список строк (для /code).
        Фильтруем по текущему history_version чата.
        """
        result = await self.session.execute(
            select(CodeLines.code_line)
            .join(Polls, CodeLines.poll_id == Polls.id)
            .where(
                CodeLines.chat_id == chat.id,
                Polls.history_version == chat.history_version,
                CodeLines.is_final.is_(True),
            )
            .order_by(CodeLines.line_number.asc())
        )
        return [row.code_line for row in result.all()]

    async def delete_all_code_for_chat(self, chat: Chats) -> None:
        """
        Полная очистка code_lines по чату (если захочешь делать жёсткий reset).
        """
        await self.session.execute(
            delete(CodeLines).where(CodeLines.chat_id == chat.id)
        )


# =========================
# CompletedCode (/code_completed)
# =========================

class CompletedCodeRepository:
    """Сохранение и получение результата автодополнения кода."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save_completed_code(
        self,
        chat: Chats,
        code_text: str,
        llm_request: Optional[dict],
        llm_response: Optional[dict],
    ) -> CompletedCode:
        completed = CompletedCode(
            chat_id=chat.id,
            history_version=chat.history_version,
            code_text=code_text,
            created_at=datetime.now(),
            llm_request=llm_request,
            llm_response=llm_response,
        )
        self.session.add(completed)
        return completed

    async def get_last_completed_for_chat(
        self,
        chat_id: int,
    ) -> Optional[CompletedCode]:
        result = await self.session.execute(
            select(CompletedCode)
            .where(CompletedCode.chat_id == chat_id)
            .order_by(CompletedCode.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()


# =========================
# SchedulerState (/health)
# =========================

class SchedulerRepository:
    """Состояние планировщика для /health."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_state(self) -> SchedulerState:
        """
        Всегда возвращаем объект.
        Если его нет – создаём с дефолтами.
        """
        result = await self.session.execute(
            select(SchedulerState).where(SchedulerState.id == 1)
        )
        state = result.scalar_one_or_none()
        if state is None:
            now = datetime.now()
            state = SchedulerState(
                id=1,
                next_run_at=now,
                uptime_started_at=now,
                active_jobs={},
            )
            self.session.add(state)
        return state

    async def update_next_run(self, next_run_at: datetime) -> None:
        state = await self.get_state()
        state.next_run_at = next_run_at

    async def set_active_jobs(self, jobs: dict) -> None:
        state = await self.get_state()
        state.active_jobs = jobs


# =========================
# Logs (/logs, /alllogs)
# =========================

class LogsRepository:
    """Работа с логами, если они пишутся в БД."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add_log(
        self,
        level: str,
        message: str,
        context: Optional[dict] = None,
    ) -> Logs:
        log = Logs(
            created_at=datetime.now(),
            level=level,
            message=message,
            context=context or {},
        )
        self.session.add(log)
        return log

    async def get_last_logs(
        self,
        limit: int = 100,
    ) -> list[Logs]:
        result = await self.session.execute(
            select(Logs)
            .order_by(Logs.id.desc())
            .limit(limit)
        )
        # возвращаем в нормальном порядке (старые → новые)
        logs = list(reversed(result.scalars().all()))
        return logs

    async def get_all_logs(self, limit: Optional[int] = None) -> list[Logs]:
        stmt = select(Logs).order_by(Logs.id.asc())
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()
