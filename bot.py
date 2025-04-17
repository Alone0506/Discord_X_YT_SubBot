import asyncio
import logging
from logging.handlers import TimedRotatingFileHandler
import os
from pathlib import Path
import shutil

import discord
from discord.ext import commands

BOT_TOKEN = os.getenv("BOT_TOKEN", "")


bot = commands.Bot(command_prefix = '&', intents = discord.Intents.all())

    
def setting_log():
    log_folder_path = Path(__file__).parent / "log"
    if log_folder_path.exists():
        shutil.rmtree(log_folder_path)
    log_folder_path.mkdir(exist_ok=True)

    for x in ['bot', 'api']:
        handler = TimedRotatingFileHandler(
            filename=log_folder_path / f"{x}.log",
            when='midnight', 
            interval=1, 
            backupCount=14, 
            encoding='utf-8'
        )
        handler.suffix = "%Y-%m-%d_%H-%M-%S.log"
        handler.setFormatter(logging.Formatter('[%(asctime)s] [%(levelname)-8s] %(name)s: %(message)s', "%Y-%m-%d %H:%M:%S"))

        logger = logging.getLogger(x)
        logger.setLevel(logging.INFO)
        logger.addHandler(handler)

async def main():
    setting_log()
    async with bot:
        await bot.load_extension(f"cogs.main")
        await bot.load_extension(f"cogs.x")
        await bot.load_extension(f"cogs.yt")
        await bot.start(BOT_TOKEN)

# load, unload是全體guild一起load, unload cog
if __name__ == "__main__":
    asyncio.run(main())
