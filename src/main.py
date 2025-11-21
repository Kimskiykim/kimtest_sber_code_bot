import asyncio
from aiogram import Bot, Dispatcher
# ---
from app.handlers import router

from app.settings import AppCTXSettings

appctx = AppCTXSettings()


async def main():
    bot = Bot(token=appctx.TG_BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    await dp.start_polling(bot, polling_timeout=15)


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
