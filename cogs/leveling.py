import discord
from discord.ext import commands
from database import db

class Leveling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        user_id = message.author.id
        # Process message for XP and coins: 15 XP and 5 Coins per message
        row = await db.process_message_rewards(user_id, xp_gain=15, coin_gain=5)
        
        if not row:
            return

        current_xp = row['xp']
        current_level = row['level']
        
        # Level formula: level = xp // 100
        calculated_level = current_xp // 100
        
        if calculated_level > current_level:
            await db.update_user(user_id, level=calculated_level)
            await message.channel.send(f"🎉 Congratulations {message.author.mention}, you leveled up to level **{calculated_level}**!")
            
            # NOTE: You can add role assignment logic here by doing:
            # role = discord.utils.get(message.guild.roles, name=f"Level {calculated_level}")
            # if role: await message.author.add_roles(role)

async def setup(bot):
    await bot.add_cog(Leveling(bot))
