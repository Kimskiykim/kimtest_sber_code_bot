from typing import Dict, Any, List, Optional
from aiogram import Bot, types


class PollManager:
    def __init__(self):
        # Внутреннее хранилище активных опросов:
        # poll_id → metadata
        self._polls: Dict[str, Dict[str, Any]] = {}
        self._chats = {}

    def register_poll(
        self,
        poll_id: str,
        chat_id: int,
        message_id: int,
        options: List[str],
        payload: Optional[dict] = None,
    ):
        """
        Сохраняем данные опроса.
        payload — необязательные данные (например история кода)
        """
        self._polls[poll_id] = {
            "chat_id": chat_id,
            "message_id": message_id,
            "options": options,
            "payload": payload or {},
        }
        self._chats[chat_id] = poll_id

    def get(self, poll_id: str) -> Optional[dict]:
        return self._polls.get(poll_id)
    
    def get_last_poll_id_by_chat_id(self, chat_id: int) -> Optional[dict]:
        poll_id = self._chats.get(chat_id)
        return poll_id

    def pop(self, poll_id: str) -> Optional[dict]:
        return self._polls.pop(poll_id, None)

    async def close_poll(self, bot: Bot, poll_id: str):
        """
        Закрывает опрос через stop_poll
        """
        poll = self._polls.get(poll_id)
        if not poll:
            return None

        closed_poll = await bot.stop_poll(
            chat_id=poll["chat_id"],
            message_id=poll["message_id"]
        )

        return closed_poll

    @staticmethod
    def extract_winner(poll: types.Poll) -> str:
        """
        Находит вариант-победитель по количеству голосов
        """
        best_option_index = max(
            range(len(poll.options)),
            key=lambda i: poll.options[i].voter_count,
        )
        return poll.options[best_option_index].text
