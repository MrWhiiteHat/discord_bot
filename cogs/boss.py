import discord
from discord.ext import commands
from database import db
import random

class Boss(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="boss")
    async def boss(self, ctx):
        boss = await db.pool.fetchrow("SELECT * FROM boss LIMIT 1")
        if not boss:
            return await ctx.send("❌ No boss currently active.")

        embed = discord.Embed(title=f"👹 Boss: {boss['boss_name']}", color=discord.Color.red())
        
        hp_bar_length = 20
        fill = int((boss['hp'] / boss['max_hp']) * hp_bar_length)
        bar = "█" * fill + "░" * (hp_bar_length - fill)
        
        embed.add_field(name="HP", value=f"`{bar}`\n**{boss['hp']} / {boss['max_hp']}**", inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="attack")
    @commands.cooldown(1, 60, commands.BucketType.user) # 60 seconds cooldown
    async def attack(self, ctx):
        boss = await db.pool.fetchrow("SELECT * FROM boss LIMIT 1")
        if not boss:
            return await ctx.send("❌ No boss currently active.")
            
        if boss['hp'] <= 0:
            return await ctx.send("💀 The boss is already defeated!")

        damage = random.randint(50, 300)
        new_hp = max(0, boss['hp'] - damage)
        
        await db.pool.execute("UPDATE boss SET hp = $1 WHERE boss_id = $2", new_hp, boss['boss_id'])
        
        user = await db.get_user(ctx.author.id)
        if not user:
            await db.create_user(ctx.author.id)
            user = await db.get_user(ctx.author.id)

        coins_reward = damage // 2
        await db.update_user(ctx.author.id, coins=user['coins'] + coins_reward)
        
        msg = f"⚔️ You attacked **{boss['boss_name']}** for **{damage}** damage!\n🪙 You earned **{coins_reward}** coins."
        
        if new_hp == 0:
            bonus = 5000
            await db.update_user(ctx.author.id, coins=user['coins'] + coins_reward + bonus)
            msg += f"\n🏆 **YOU DEFEATED THE BOSS!** You earned a bonus of **{bonus}** coins!"
            
            # Reset boss with full HP
            await db.pool.execute("UPDATE boss SET hp = max_hp WHERE boss_id = $1", boss['boss_id'])
            msg += "\n*A new boss has suddenly appeared...*"
            
        await ctx.send(msg)

    @attack.error
    async def attack_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏳ Your weapon is on cooldown! Try again in {error.retry_after:.1f}s.")

async def setup(bot):
    await bot.add_cog(Boss(bot))
