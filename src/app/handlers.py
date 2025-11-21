from aiogram import types, Router, BaseMiddleware
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext

from typing import Callable, Awaitable, Dict, Any
from app.keyboards import get_keyboard_for_role
from app.utils import get_user_role, RolesEnum
from app.enums import RolesEnum, CommandsEnum

class RoleMiddleware(BaseMiddleware):
    async def __call__(self, handler: Callable, event, data: Dict[str, Any]) -> Any:
        user_id = event.from_user.id
        data["role"] = await get_user_role(user_id, event)
        return await handler(event, data)

router = Router()
router.message.middleware(RoleMiddleware())


@router.message(Command("restart"))
async def restart_handler(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("🔄 Бот перезапущен логически. Начинаем сначала.")
    await message.answer("Привет! Это как новый запуск бота.")


@router.message(CommandStart())
async def handle_start(message: types.Message, role: RolesEnum):
    if role in (RolesEnum.ADMIN, RolesEnum.OWNER, RolesEnum.GROUP_ADMIN):
       return await message.reply("История очищена, отправляю первый опрос.")
    return await message.reply("Только админ.")     



@router.message(Command(CommandsEnum.HELP.value))
async def handle_help(message: types.Message):
    await message.answer("Вы нажали кнопку помощи.")


@router.message(Command(CommandsEnum.CODE.value))
async def handle_code(message: types.Message):
    await message.answer("Вы нажали кнопку CODE.")


@router.message(Command(CommandsEnum.CODE_COMPLETED.value))
async def handle_code_completed(message: types.Message):
    await message.answer("Вы нажали кнопку CODE_COMPLETED.")


@router.message(Command(CommandsEnum.SEND_NOW.value))
async def handle_send_now(message: types.Message):
    await message.answer("Вы нажали кнопку SEND_NOW.")


@router.message(Command(CommandsEnum.HEALTH.value))
async def handle_health(message: types.Message):
    await message.answer("Вы нажали кнопку HEALTH.")


@router.message(Command(CommandsEnum.LOGS.value))
async def handle_logs(message: types.Message):
    await message.answer("Вы нажали кнопку LOGS.")


@router.message(Command(CommandsEnum.ALLOGS.value))
async def handle_alllogs(message: types.Message):
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
