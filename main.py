import asyncio
from utils.config import BOT_TOKEN
from bot.database import DatabaseManager
from bot.bot_highlights import MyBot
from utils.logger import Logger


async def start_bot():
    # logger = Logger(filename='bot_collect_clients.log').get_logger()
    logger = Logger().get_logger()
    db_manager = DatabaseManager(logger)
    await db_manager.create_pool()
    my_bot = MyBot(BOT_TOKEN, db_manager, logger)
    await my_bot.start_bot()

if __name__ == '__main__':
    asyncio.run(start_bot())
