import discord
from discord.ext import commands
from database import db
import random

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="balance", aliases=["bal", "coins"])
    async def balance(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        user = await db.get_user(member.id)
        coins = user['coins'] if user else 0
        await ctx.send(f"💰 {member.display_name} has **{coins}** coins.")

    @commands.command(name="work")
    @commands.cooldown(1, 3600, commands.BucketType.user)  # 1 hour cooldown
    async def work(self, ctx):
        earned = random.randint(50, 200)
        user = await db.get_user(ctx.author.id)
        if not user:
            await db.create_user(ctx.author.id)
            user = await db.get_user(ctx.author.id)
            
        await db.update_user(ctx.author.id, coins=user['coins'] + earned)
        await ctx.send(f"👷 You worked hard and earned **{earned}** coins!")

    @work.error
    async def work_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏳ You're too tired! Try again in {error.retry_after:.2f} seconds.")

    @commands.command(name="give", aliases=["pay"])
    async def give(self, ctx, member: discord.Member, amount: int):
        if amount <= 0:
            return await ctx.send("❌ Amount must be greater than 0.")
        
        sender = await db.get_user(ctx.author.id)
        if not sender or sender['coins'] < amount:
            return await ctx.send("❌ You don't have enough coins.")
            
        receiver = await db.get_user(member.id)
        if not receiver:
            await db.create_user(member.id)
            receiver = await db.get_user(member.id)
            
        await db.update_user(ctx.author.id, coins=sender['coins'] - amount)
        await db.update_user(member.id, coins=receiver['coins'] + amount)
        
        await ctx.send(f"💸 You gave **{amount}** coins to {member.mention}.")

    @commands.command(name="leaderboard", aliases=["lb"])
    async def leaderboard(self, ctx, lb_type: str = "coins"):
        if lb_type.lower() not in ["coins", "xp"]:
            return await ctx.send("❌ Valid leaderboards are: `coins`, `xp`")
            
        order_by = "coins" if lb_type.lower() == "coins" else "xp"
        query = f"SELECT user_id, {order_by} FROM users ORDER BY {order_by} DESC LIMIT 10"
        records = await db.pool.fetch(query)
        
        if not records:
            return await ctx.send("No users found in the database yet.")
            
        desc = ""
        for i, record in enumerate(records, 1):
            desc += f"**{i}.** <@{record['user_id']}> - {record[order_by]} {order_by}\n"
            
        embed = discord.Embed(title=f"🏆 {lb_type.capitalize()} Leaderboard", description=desc, color=discord.Color.gold())
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Economy(bot))
