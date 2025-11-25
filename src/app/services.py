from __future__ import annotations
from datetime import datetime

from app.db.uow import UoWFactory


async def cmd_health(uow_factory: UoWFactory, chat_id: int) -> str:
    """
    Возвращает:
    - uptime
    - время следующего запуска планировщика
    - активные job-ы
    - наличие активного опроса в этом чате
    """
    async with uow_factory() as uow:
        scheduler = await uow.scheduler.get_state()

        chat = await uow.chats.get_or_create_chat(chat_id)
        active_poll = await uow.polls.get_active_poll_for_chat(chat_id)

    uptime_sec = int((datetime.now() - scheduler.uptime_started_at).total_seconds())
    next_run = scheduler.next_run_at.strftime("%H:%M:%S")

    msg = [
        f"🟢 Бот работает {uptime_sec} сек.",
        f"Следующий запуск планировщика в {next_run}.",
        f"Активные задания: {scheduler.active_jobs}",
    ]

    if active_poll:
        msg.append("⚠ В этом чате есть активный опрос.")
    else:
        msg.append("Нет активного опроса.")

    return "\n".join(msg)

# =====================================
# LOGS
# =====================================

async def cmd_logs(uow_factory: UoWFactory, limit: int = 50) -> str:
    """
    Возвращает последние N строк логов.
    """
    async with uow_factory() as uow:
        logs = await uow.logs.get_last_logs(limit)

    if not logs:
        return "Логи пусты."

    lines = []
    for log in logs:
        line = f"[{log.created_at}][{log.level}] {log.message}"
        lines.append(line)

    return "\n".join(lines[-limit:])



async def cmd_all_logs(uow_factory: UoWFactory) -> str:
    async with uow_factory() as uow:
        logs = await uow.logs.get_all_logs()

    if not logs:
        return "Логи пусты."

    return "\n".join(
        f"[{l.created_at}][{l.level}] {l.message}" for l in logs
    )
