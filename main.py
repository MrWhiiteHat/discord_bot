import discord
from discord.ext import commands
import logging
from config import DISCORD_TOKEN, COMMAND_PREFIX
from database import db

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log = logging.getLogger("bot")

class RPGDiscordBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix=COMMAND_PREFIX, intents=intents)

    async def setup_hook(self):
        # Connect to Database
        await db.connect()
        
        # Load Cogs
        cogs = [
            "cogs.economy",
            "cogs.leveling",
            "cogs.boss",
            "cogs.shop",
            "cogs.faction",
            "cogs.events"
        ]
        for cog in cogs:
            try:
                await self.load_extension(cog)
                log.info(f"Loaded {cog}")
            except Exception as e:
                log.error(f"Failed to load {cog}: {e}")

    async def on_ready(self):
        log.info(f"Logged in as {self.user} (ID: {self.user.id})")
        log.info("Bot is ready for action!")

if __name__ == "__main__":
    if not DISCORD_TOKEN:
        log.error("DISCORD_TOKEN is missing. Please set it in your .env file.")
    else:
        bot = RPGDiscordBot()
        bot.run(DISCORD_TOKEN)
