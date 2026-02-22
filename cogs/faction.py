import discord
from discord.ext import commands
from database import db

class Faction(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group(name="faction", invoke_without_command=True)
    async def faction(self, ctx):
        await ctx.send("Available commands: `!faction join <name>`, `!faction info`, `!faction leaderboard`")

    @faction.command(name="join")
    async def join(self, ctx, *, faction_name: str):
        valid_factions = ["Knights", "Mages", "Rogues"]
        if faction_name.capitalize() not in valid_factions:
            return await ctx.send(f"❌ Valid factions are: {', '.join(valid_factions)}")
            
        user = await db.get_user(ctx.author.id)
        if not user:
            await db.create_user(ctx.author.id)
            user = await db.get_user(ctx.author.id)
            
        if user['faction']:
            return await ctx.send(f"❌ You are already in the **{user['faction']}** faction.")
            
        await db.update_user(ctx.author.id, faction=faction_name.capitalize())
        await ctx.send(f"⚔️ You have successfully joined the **{faction_name.capitalize()}** faction!")

    @faction.command(name="info")
    async def info(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        user = await db.get_user(member.id)
        
        if not user or not user['faction']:
            return await ctx.send(f"❌ {member.display_name} is not in any faction.")
            
        faction_name = user['faction']
        members_count = await db.pool.fetchval("SELECT COUNT(*) FROM users WHERE faction = $1", faction_name)
        
        embed = discord.Embed(title=f"🛡️ Faction: {faction_name}", color=discord.Color.blue())
        embed.add_field(name="Member", value=member.display_name, inline=True)
        embed.add_field(name="Total Members in Faction", value=members_count, inline=True)
        await ctx.send(embed=embed)

    @faction.command(name="leaderboard", aliases=["lb"])
    async def leaderboard(self, ctx):
        query = """
            SELECT faction, SUM(xp) as total_xp, SUM(coins) as total_coins 
            FROM users 
            WHERE faction IS NOT NULL 
            GROUP BY faction 
            ORDER BY total_xp DESC
        """
        records = await db.pool.fetch(query)
        if not records:
            return await ctx.send("No faction data available.")
            
        embed = discord.Embed(title="🏰 Faction Leaderboard", color=discord.Color.purple())
        for i, record in enumerate(records, 1):
            embed.add_field(
                name=f"{i}. {record['faction']}", 
                value=f"**XP:** {record['total_xp']} | **Coins:** {record['total_coins']}", 
                inline=False
            )
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Faction(bot))
