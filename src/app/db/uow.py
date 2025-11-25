from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from contextlib import asynccontextmanager

from app.db.repositories import (
    ChatsRepository,
    PollsRepository,
    CodeRepository,
    CompletedCodeRepository,
    SchedulerRepository,
    LogsRepository,
)


class UnitOfWork:
    """
    UnitOfWork создаёт единую транзакцию, внутри которой работают все репозитории.
    Используется через async with.

    Пример:
        async with uow_factory() as uow:
            chat = await uow.chats.get_or_create_chat(chat_id)
            ...
            await uow.commit()
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self._session_factory = session_factory
        self.session: AsyncSession | None = None

        # Репозитории
        self.chats: ChatsRepository | None = None
        self.polls: PollsRepository | None = None
        self.code: CodeRepository | None = None
        self.completed: CompletedCodeRepository | None = None
        self.scheduler: SchedulerRepository | None = None
        self.logs: LogsRepository | None = None

    async def __aenter__(self) -> "UnitOfWork":
        self.session = self._session_factory()
        # явно открываем транзакцию
        await self.session.begin()

        # Инициализируем репозитории
        self.chats = ChatsRepository(self.session)
        self.polls = PollsRepository(self.session)
        self.code = CodeRepository(self.session)
        self.completed = CompletedCodeRepository(self.session)
        self.scheduler = SchedulerRepository(self.session)
        self.logs = LogsRepository(self.session)

        return self

    async def __aexit__(self, exc_type, exc, tb):
        if exc is None:
            try:
                await self.session.commit()
            except Exception:
                await self.session.rollback()
                raise
        else:
            await self.session.rollback()

        await self.session.close()

    async def commit(self):
        await self.session.commit()

    async def rollback(self):
        await self.session.rollback()


class UoWFactory:
    """
    Создаёт UnitOfWork через sessionmaker.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self._session_factory = session_factory

    @asynccontextmanager
    async def __call__(self):
        uow = UnitOfWork(self._session_factory)
        async with uow as uow_instance:
            yield uow_instance
