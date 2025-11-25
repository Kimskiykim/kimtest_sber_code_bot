from typing import Dict, Any, List, Optional
from aiogram import Bot, types
from app.db.uow import UoWFactory
from app.utils import to_markdown


class DataManager:
    def __init__(self, uow: UoWFactory):
        # Внутреннее хранилище активных опросов:
        # poll_id → metadata
        self._polls: Dict[str, Dict[str, Any]] = {}
        self._chats = {}
        self.uow = uow

    async def clear_chat_history(self, chat_id: int) -> None:
        """
        Clear chat Hist
        """
        assert isinstance(chat_id, int) #TODO rcheck
        async with self.uow() as uow:
            chat_dbt = await uow.chats.get_or_create_chat(chat_id)
            
            if chat_dbt.last_poll_id:
                # ставим статус опроса если он активен в rejected чтобы далее с ним не работать
                await uow.polls.reject_poll_if_active_by_poll_id(chat_dbt.last_poll_id)
            # по чатайди получим чат
            await uow.chats.reset_history(chat_id)
            # фиксация изменений
            await uow.commit()
        return None

    async def register_poll(
        self,
        tg_poll_id: str,
        chat_id: int,
        message_id: int,
        options: List[str],
        timeout_at = None
    ):
        """
        Сохраняем данные опроса
        """
        async with self.uow() as uow:
            chat_dbt = await uow.chats.get_chat(chat_id=chat_id)
            await uow.polls.create_poll(chat=chat_dbt, options=options, tg_poll_id=tg_poll_id, tg_message_id=message_id, timeout_at=timeout_at)
        return None

    async def get_current_code(self, chat_id: int, markdown: bool = True):
        lines = None
        async with self.uow() as uow:
            chat = await uow.chats.get_chat(chat_id)
            if not chat:
                return False, "В этом чате нет истории кода."

            lines = await uow.code.get_current_code(chat)

        if not lines:
            return False, "Код пока не создан — ещё не завершено ни одного опроса ⏳"

        code_text = "\n".join(lines)
        if markdown:
            code_text = to_markdown(code_text)
        return True, code_text
    
    async def close_poll(self, tg_poll_id: str):
        poll = None
        if tg_poll_id:
            async with self.uow() as uow:
                poll = await uow.polls.get_poll_by_tg_id(tg_poll_id)
                # фиксируем статус закрытия
                await uow.polls.close_poll(poll)
        return poll

    async def get_last_poll_tg_id_by_chat_id(self, chat_id: int):
        res = None
        async with self.uow() as uow:
            chat = await uow.chats.get_chat(chat_id)
            if chat and chat.last_poll_id:
                poll = await uow.polls.get_poll_by_id(chat.last_poll_id)
                if poll and poll.tg_poll_id:
                    res = poll.tg_poll_id
        return res


    async def save_complete_code(self, chat_id: int, base_code_text: str, completed_code_text: str) -> tuple[bool, str]:
        msg = "Нет истории кода."
        is_ok = False
        async with self.uow() as uow:
            chat = await uow.chats.get_chat(chat_id)
            if chat:
                # сохраняем
                await uow.completed.save_completed_code(
                    chat=chat,
                    code_text=completed_code_text,
                    llm_request={"base_code": base_code_text},
                    llm_response={"completed": completed_code_text})
                
                msg = "Готово! Код успешно дополнён. Отправляю файл..."
                is_ok = True
        return is_ok, msg
    
    async def get_poll_by_tg_poll_id(self, tg_poll_id: str):
        async with self.uow() as uow:
            poll = await uow.polls.get_poll_by_tg_id(tg_poll_id)

        return poll
    
    async def finishing_poll_process(self, tg_poll_id: str):
        winner = None
        async with self.uow() as uow:
            poll = await uow.polls.get_poll_by_tg_id(tg_poll_id)

            if not poll:
                return None

            # фиксируем статус закрытия
            await uow.polls.close_poll(poll)
            
            # считаем голоса
            await uow.polls.recalc_votes_for_poll(poll.id)

            # выбираем победивший вариант
            winner = await uow.polls.get_winner(poll.id)

            # добавляем строку в код
            chat = await uow.chats.get_chat(poll.chat_id)
            await uow.code.append_code_line_from_poll(
                chat=chat,
                poll=poll,
                winning_option_index=winner.index,
            )
            
            await uow.commit()
        return winner
    
    async def register_poll_answer(self, tg_poll_id: str, user_id, option_index):
        async with self.uow() as uow:
            poll = await uow.polls.get_poll_by_tg_id(tg_poll_id)
            await uow.polls.add_or_update_vote(poll.id, user_id, option_index)