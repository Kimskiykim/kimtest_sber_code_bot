from aiogram import types, Router, BaseMiddleware
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext

from typing import Callable, Dict, Any
from app.keyboards import get_keyboard_for_role
from app.crud import DataManager
from app.utils import get_user_role, RolesEnum, send_py_from_memory, to_markdown
from app.enums import RolesEnum, CommandsEnum
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from app.db.base import get_async_engine
from .settings import appctx
from app.db.uow import UoWFactory
from app.llm.llm import LLMGenerator
from app.pmodels import AgentInputModes, LLMInput


class RoleMiddleware(BaseMiddleware):
    async def __call__(self, handler: Callable, event, data: Dict[str, Any]) -> Any:
        user_id = event.from_user.id
        chat_id = event.chat.id
        # ---
        data["role"] = await get_user_role(user_id, event, admin_ids=appctx.TG_BOT_ADMINS)
        # print("ADMINS0", appctx.TG_BOT_ADMINS)
        data["llm_configurable"] = {"configurable": {"thread_id": chat_id}}
        return await handler(event, data)


router = Router()
router.message.middleware(RoleMiddleware())
async_session = async_sessionmaker(
    bind=get_async_engine(url=appctx.DB_PREFIX + appctx.DB_CONNECTION_STRING),
    expire_on_commit=False,  # обязательно для асинхронки
    class_=AsyncSession,
)
data_manager = DataManager(uow=UoWFactory(session_factory=async_session))
llm_agent = LLMGenerator(app_config=appctx).build_graph()


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

        poll_dbt = await data_manager.get_poll_by_tg_poll_id(tg_poll_id=poll_id)
        if poll_dbt:
            winner_poll_option_dbt = await data_manager.finishing_poll_process(tg_poll_id=poll_id)
            if winner_poll_option_dbt and winner_poll_option_dbt.code_line:
                await bot.send_message(
                    poll_dbt.chat_id,
                    f"Победившая строка:\n```\n{winner_poll_option_dbt.code_line}\n```",
                    parse_mode="Markdown"
                )

@router.poll_answer()
async def on_poll_answer(update: types.PollAnswer):
    print("received poll anwer", update)
    tg_poll_id = update.poll_id
    user_id: int | None = update.user.id
    poll_answer_index = None
    if update.option_ids:
        poll_answer_index = update.option_ids[0]
        await data_manager.register_poll_answer(tg_poll_id=tg_poll_id, user_id=user_id, option_index=poll_answer_index)
        # TODO retract vote []
    


@router.message(CommandStart())
async def cmd_start(message: types.Message, role: RolesEnum, llm_configurable: dict, state: FSMContext):
    
    if role in (RolesEnum.ADMIN, RolesEnum.OWNER, RolesEnum.GROUP_ADMIN):
        await message.answer(text="Вот что я имею (взгляни в меню)", reply_markup=get_keyboard_for_role(role))
        # Очищение истории чата (перевод активного опроса чата в rejected на случай если это повторное использование):
        await data_manager.clear_chat_history(chat_id=message.chat.id)
        await state.clear()
        await message.reply("История очищена, отправляю первый опрос.")
        
        # Генерация новой ветки опроса:
        options = (await llm_agent.ainvoke(input=LLMInput(mode=AgentInputModes.ZERO, history=[]), config=llm_configurable)).get("final") or ("1", "2", "3", "4")
        question = "Выберите первую строку кода:"

        sent_poll = await message.answer_poll(
            question=question,
            options=options,
            is_anonymous=False,
            type="regular",
            allows_multiple_answers=False
        )
        tg_poll_id = sent_poll.poll.id
        await data_manager.register_poll(
            tg_poll_id=tg_poll_id,
            chat_id=message.chat.id,
            message_id=sent_poll.message_id,
            options=options)
    else:
        return await message.reply("Права на команду /start только у админа.")     


@router.message(Command(CommandsEnum.HELP.value))
async def cmd_help(message: types.Message):
    await message.answer("Вы нажали кнопку помощи.")


@router.message(Command(CommandsEnum.CODE.value))
async def cmd_code(message: types.Message):
    await message.answer("Показываю текущий код")
    _, result = await data_manager.get_current_code(chat_id=message.chat.id)
    await message.reply(result, parse_mode="Markdown")


@router.message(Command(CommandsEnum.CODE_COMPLETED.value))
async def cmd_code_completed(message: types.Message, role: RolesEnum, llm_configurable: dict,):
    await message.answer("Вы нажали кнопку CODE_COMPLETED.")
    if role in (RolesEnum.ADMIN, RolesEnum.OWNER, RolesEnum.GROUP_ADMIN):
        last_poll_id = await data_manager.get_last_poll_tg_id_by_chat_id(message.chat.id)
        poll_dbt = await data_manager.close_poll(last_poll_id)
        if poll_dbt:
            try:
                await message.bot.stop_poll(chat_id=poll_dbt.chat_id, message_id=poll_dbt.tg_message_id)
            except Exception as e:
                print(e)
        # TODO sync
        is_ok, current_code = await data_manager.get_current_code(chat_id=message.chat.id, markdown=False)
        if is_ok:
            completed_code = (await llm_agent.ainvoke(input=LLMInput(mode=AgentInputModes.COMPLETE, history=[current_code]), config=llm_configurable)).get("completed_code")
            is_ok, dm_scc_msg = await data_manager.save_complete_code(chat_id=message.chat.id, base_code_text=current_code, completed_code_text=completed_code)
            await message.answer(dm_scc_msg)
            if is_ok:
                await message.answer(to_markdown(code_text=completed_code), parse_mode="Markdown")
                await send_py_from_memory(message=message, code_text=completed_code)
    else:
        await message.answer("Выполнение команды ограничено: только для администраторов")


@router.message(Command(CommandsEnum.SEND_NOW.value))
async def cmd_send_now(message: types.Message, role: RolesEnum, llm_configurable):
    if role in (RolesEnum.ADMIN, RolesEnum.OWNER, RolesEnum.GROUP_ADMIN):
        last_poll_id = await data_manager.get_last_poll_tg_id_by_chat_id(message.chat.id)
        poll_dbt = await data_manager.close_poll(last_poll_id)
        if poll_dbt:
            try:
                await message.bot.stop_poll(chat_id=poll_dbt.chat_id, message_id=poll_dbt.tg_message_id)
                await message.reply("Опрос завершен, отправляю новый.")
            except Exception as e:
                print(e)
        # TODO sync
        is_ok, current_code = await data_manager.get_current_code(chat_id=message.chat.id, markdown=False)
        if is_ok:
            options = (await llm_agent.ainvoke(input=LLMInput(mode=AgentInputModes.NEXT, history=[current_code]), config=llm_configurable)).get("final") or ("1", "2", "3", "4")
            question = "Выберите следующую строку кода:"

            sent_poll = await message.answer_poll(
                question=question,
                options=options,
                is_anonymous=False,
                type="regular",
                allows_multiple_answers=False
            )
            tg_poll_id = sent_poll.poll.id
            await data_manager.register_poll(
                tg_poll_id=tg_poll_id,
                chat_id=message.chat.id,
                message_id=sent_poll.message_id,
                options=options)


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
