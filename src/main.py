import asyncio
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
# ---
from app.handlers import router

from app.settings import appctx
from app.db.utils import create_all
from app.db.base import get_async_engine


async def on_startup(bot: Bot):
    # TODO Заменить
    await create_all(get_async_engine(url=appctx.DB_PREFIX + appctx.DB_CONNECTION_STRING))
    # добавление стартовой команды
    await bot.set_my_commands((
        BotCommand(command="start", description="Начать работу/рестарт"),
        BotCommand(command="code", description="Показать код"),
        BotCommand(command="send_now", description="Следующий опрос"),
        BotCommand(command="code_completed", description="Создать код из результатов")))


async def main():
    bot = Bot(token=appctx.TG_BOT_TOKEN)
    await on_startup(bot)
    
    dp = Dispatcher()
    dp.include_router(router)
    await dp.start_polling(bot, polling_timeout=15, 
                        #    allowed_updates=["message"]
                           )


if __name__ == "__main__":
    try:
        print("\n--------------------"
              "\n--- Starting BOT ---"
              "\n--------------------"
              "\n--------------------"
              )
        asyncio.run(main())
        
    except (KeyboardInterrupt, SystemExit):
        print("Bot stopped!")
