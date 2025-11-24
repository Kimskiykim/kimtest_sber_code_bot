from aiogram import types, Router, BaseMiddleware
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext

from typing import Callable, Awaitable, Dict, Any
from app.keyboards import get_keyboard_for_role
from app.polls import PollManager
from app.utils import get_user_role, RolesEnum
from app.enums import RolesEnum, CommandsEnum


class RoleMiddleware(BaseMiddleware):
    async def __call__(self, handler: Callable, event, data: Dict[str, Any]) -> Any:
        user_id = event.from_user.id
        data["role"] = await get_user_role(user_id, event)
        return await handler(event, data)

router = Router()
router.message.middleware(RoleMiddleware())
poll_manager = PollManager()


@router.message(Command("restart"))
async def restart_handler(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("🔄 Бот перезапущен логически. Начинаем сначала.")
    await message.answer("Привет! Это как новый запуск бота.")


@router.poll()
async def on_poll_finished(poll: types.Poll):
    if poll.is_closed:
        poll_id = poll.id
        bot = poll.bot
        
        data = poll_manager.pop(poll_id)
        if not data:
            print("Неизвестный poll_id")
            return

        winner = PollManager.extract_winner(poll)

        await bot.send_message(
            data["chat_id"],
            f"Победившая строка:\n```\n{winner}\n```",
            parse_mode="Markdown"
        )



@router.message(CommandStart())
async def cmd_start(message: types.Message, role: RolesEnum, state: FSMContext):
    await state.clear()
    if role in (RolesEnum.ADMIN, RolesEnum.OWNER, RolesEnum.GROUP_ADMIN):
        options = ["line1", "line2", "line3", "line4"]
        question = "Выберите следующую строку кода:"
        await message.reply("История очищена, отправляю первый опрос.")
        sent_poll = await message.answer_poll(
        question="Какой язык лучше?",
        options=["Python", "Go", "Rust"],
        is_anonymous=True,
        type="regular",
        allows_multiple_answers=False
    )
        poll_id = sent_poll.poll.id
        poll_manager.register_poll(
            poll_id=poll_id,
            chat_id=message.chat.id,
            message_id=sent_poll.message_id,
            options=options,
            payload={"history": ["previous line 1", "previous line 2"]}
    )
    return await message.reply("Только админ.")     


@router.message(Command(CommandsEnum.HELP.value))
async def cmd_help(message: types.Message):
    await message.answer("Вы нажали кнопку помощи.")


@router.message(Command(CommandsEnum.CODE.value))
async def cmd_code(message: types.Message):
    await message.answer("Вы нажали кнопку CODE.")


@router.message(Command(CommandsEnum.CODE_COMPLETED.value))
async def cmd_code_completed(message: types.Message):
    await message.answer("Вы нажали кнопку CODE_COMPLETED.")


@router.message(Command(CommandsEnum.SEND_NOW.value))
async def cmd_send_now(message: types.Message, role: RolesEnum):
    if role in (RolesEnum.ADMIN, RolesEnum.OWNER, RolesEnum.GROUP_ADMIN):
        last_poll_id = poll_manager.get_last_poll_id_by_chat_id(message.chat.id)
        closed_poll = await poll_manager.close_poll(message.bot, last_poll_id)
        
        if not closed_poll:
            await message.answer("Не удалось закрыть.")
        else:
            await message.reply("Опрос завершен, отправляю новый.")
            options = ["line1", "line2", "line3", "line4"]
            question = "Выберите следующую строку кода:"

            sent = await message.answer_poll(
                question=question,
                options=options,
                is_anonymous=True,
                type="regular",
                allows_multiple_answers=False
            )

            poll_id = sent.poll.id

            poll_manager.register_poll(
                poll_id=poll_id,
                chat_id=message.chat.id,
                message_id=sent.message_id,
                options=options,
                payload={"history": ["previous line 1", "previous line 2"]}
        )


@router.message(Command(CommandsEnum.HEALTH.value))
async def cmd_health(message: types.Message):
    await message.answer("Вы нажали кнопку HEALTH.")


@router.message(Command(CommandsEnum.LOGS.value))
async def cmd_logs(message: types.Message):
    await message.answer("Вы нажали кнопку LOGS.")


@router.message(Command(CommandsEnum.ALLOGS.value))
async def cmd_alllogs(message: types.Message):
    await message.answer("Вы нажали кнопку ALLOGS.")


@router.message()
async def show_keyboard(message: types.Message, role: RolesEnum):
    if message.new_chat_members:
        bot = message.bot
        me = await bot.get_me()

        for member in message.new_chat_members:
            if member.id == me.id:
                await message.answer("Привет! Я успешно добавлен в чат 👋", reply_markup=get_keyboard_for_role(role))
    else:
        # TODO обработать случай, когда пользователь просто пишет сообщение в группе
        await message.answer(text="Вот что я имею (взгляни в меню)", reply_markup=get_keyboard_for_role(role))
