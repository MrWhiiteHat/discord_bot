import discord
from discord.ext import commands
from database import db

class Shop(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="shop")
    async def shop(self, ctx):
        items = await db.pool.fetch("SELECT * FROM shop ORDER BY price ASC")
        if not items:
            return await ctx.send("🛒 The shop is currently empty.")

        embed = discord.Embed(title="🛒 Shop", description="Use `!buy <item_id>` to purchase.", color=discord.Color.green())
        for item in items:
            role_mention = f"<@&{item['role_id']}>" if item['role_id'] else "None"
            embed.add_field(
                name=f"ID {item['item_id']} | {item['name']}", 
                value=f"💰 Price: {item['price']} coins\n🛡️ Role: {role_mention}", 
                inline=False
            )
            
        await ctx.send(embed=embed)

    @commands.command(name="buy")
    async def buy(self, ctx, item_id: int):
        item = await db.pool.fetchrow("SELECT * FROM shop WHERE item_id = $1", item_id)
        if not item:
            return await ctx.send("❌ Invalid item ID.")

        user = await db.get_user(ctx.author.id)
        if not user or user['coins'] < item['price']:
            return await ctx.send("❌ You don't have enough coins.")

        # Give role if applicable
        if item['role_id']:
            role = ctx.guild.get_role(item['role_id'])
            if role:
                if role in ctx.author.roles:
                    return await ctx.send("❌ You already have this role!")
                try:
                    await ctx.author.add_roles(role)
                except discord.Forbidden:
                    return await ctx.send("❌ I don't have permission to assign this role.")
            else:
                return await ctx.send("❌ Role not found in this server.")

        await db.update_user(ctx.author.id, coins=user['coins'] - item['price'])
        await ctx.send(f"✅ You successfully bought **{item['name']}** for {item['price']} coins!")

async def setup(bot):
    await bot.add_cog(Shop(bot))
