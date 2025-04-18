import asyncio
import logging
from logging.handlers import TimedRotatingFileHandler
import os
from pathlib import Path

import discord
from discord.ext import commands

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
bot = commands.Bot(command_prefix = '&', intents = discord.Intents.all())


def setting_log():
    # Clean up old log files
    log_folder_path = Path(__file__).parent / "log"
    for item in log_folder_path.iterdir():
        if item.is_file() or item.is_symlink():
            item.unlink()

    handler = TimedRotatingFileHandler(
        filename=log_folder_path / "discord.log",
        when='midnight', # 每天午夜時自動建立新日誌檔案
        interval=1, 
        backupCount=14, # 最多保留舊日誌數量。超過這個數量後，最舊的檔案會被自動刪除
        encoding='utf-8'
    )
    handler.suffix = "%Y-%m-%d_%H-%M-%S.log"
    handler.setFormatter(logging.Formatter('[%(asctime)s] [%(levelname)-8s] %(name)s: %(message)s', "%Y-%m-%d %H:%M:%S"))

    logger = logging.getLogger('discord')
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)


async def main():
    setting_log()
    async with bot:
        await bot.load_extension(f"cogs.main")
        await bot.load_extension(f"cogs.x")
        await bot.load_extension(f"cogs.yt")
        await bot.start(BOT_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
