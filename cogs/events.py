import discord
from discord.ext import commands
from database import db
from datetime import datetime, timezone, timedelta

class Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="daily")
    async def daily(self, ctx):
        user = await db.get_user(ctx.author.id)
        if not user:
            await db.create_user(ctx.author.id)
            user = await db.get_user(ctx.author.id)

        now = datetime.now(timezone.utc)
        if user['last_daily']:
            last_daily = user['last_daily']
            if last_daily.tzinfo is None:
                last_daily = last_daily.replace(tzinfo=timezone.utc)
                
            if now - last_daily < timedelta(hours=24):
                time_left = timedelta(hours=24) - (now - last_daily)
                hours, remainder = divmod(int(time_left.total_seconds()), 3600)
                minutes, _ = divmod(remainder, 60)
                return await ctx.send(f"⏳ You have already claimed your daily reward! Try again in **{hours}h {minutes}m**.")

        reward = 500
        await db.update_user(ctx.author.id, coins=user['coins'] + reward, last_daily=now.replace(tzinfo=None))
        await ctx.send(f"🎁 You claimed your daily reward of **{reward}** coins!")

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if hasattr(ctx.command, 'on_error'):
            return
            
        if isinstance(error, commands.CommandNotFound):
            return
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Missing argument: `{error.param.name}`")
        elif isinstance(error, commands.CommandInvokeError):
            print(f"Error in command {ctx.command}: {error.original}")
            await ctx.send("⚠️ An error occurred while executing the command.")

async def setup(bot):
    await bot.add_cog(Events(bot))
