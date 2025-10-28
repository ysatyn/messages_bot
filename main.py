import asyncio
from telebot.async_telebot import AsyncTeleBot
from telebot import types
from config import BOT_TOKEN
from db.database import init_models
from bot.handlers import register_handlers


from global_logger import logger

async def main():
    logger.info("Started the bot launch")
    await init_models()
    await create_admin_panel(0, 0)
    bot = AsyncTeleBot(BOT_TOKEN, parse_mode='HTML')
    logger.info("Registration of handlers started")
    register_handlers(bot)
    logger.info("Success!")
    commands = [
        types.BotCommand("start", "🏠 Главное меню"),
        types.BotCommand("note", "✍️ Написать послание"),
        types.BotCommand("mynotes", "📒 Мои послания"),
        types.BotCommand("myref", "🔗 Моя ссылка"),
        types.BotCommand("help", "❓ Помощь"),
        types.BotCommand("buy_unread", "🛒 Купить отмену прочтения")
    ]
    await bot.set_my_commands(commands)
    logger.info("Set the commands")
    
    logger.info("Bot started successfully! ")
    await bot.polling()

async def create_admin_panel(total_earnings: int = 0, total_read_cancels_sold: int = 0):
    from db.database import AsyncSessionLocal
    from db.crud import initiate_creation_of_admin_panel
    from config import ADMIN_ID

    async with AsyncSessionLocal() as session:
        await initiate_creation_of_admin_panel(session, ADMIN_ID, total_earnings, total_read_cancels_sold)

if __name__ == "__main__":
    asyncio.run(main())
