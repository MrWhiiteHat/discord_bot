import discord
from discord.ext import commands
from database import db
from datetime import datetime, timezone
import random

PUZZLES = {
    1: {"answer": "01100001", "role": "Investigator"},
    2: {"answer": "c2VjcmV0", "role": "Decryptor"},
    3: {"answer": "khoor", "role": "Inner Circle"},
    4: {"answer": ".../---/...", "role": "Architect"},
}

class ARG(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def get_or_create_user(self, user_id):
        user = await db.pool.fetchrow("SELECT * FROM arg_users WHERE user_id = $1", user_id)
        if not user:
            await db.pool.execute("INSERT INTO arg_users (user_id) VALUES ($1) ON CONFLICT DO NOTHING", user_id)
            user = await db.pool.fetchrow("SELECT * FROM arg_users WHERE user_id = $1", user_id)
        return user

    @commands.group(name="arg", invoke_without_command=True)
    async def arg(self, ctx):
        await ctx.send("🕵️ Welcome to the system. Use `!arg submit <answer>` to proceed.")

    @arg.command(name="submit")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def submit(self, ctx, *, answer: str):
        user = await self.get_or_create_user(ctx.author.id)
        phase = user['current_phase']

        if phase not in PUZZLES:
            return await ctx.send("⬛ You have reached the end of the current sequence. Await further instructions.")

        correct_answer = PUZZLES[phase]['answer']
        
        if answer.lower() == correct_answer.lower():
            new_phase = phase + 1
            await db.pool.execute(
                "UPDATE arg_users SET current_phase = $1, puzzles_solved = puzzles_solved + 1, last_submission = $2 WHERE user_id = $3",
                new_phase, datetime.now(timezone.utc).replace(tzinfo=None), ctx.author.id
            )
            
            role_name = PUZZLES[phase]['role']
            role = discord.utils.get(ctx.guild.roles, name=role_name)
            if role:
                try:
                    await ctx.author.add_roles(role)
                    role_msg = f" You have been granted the **{role_name}** clearance."
                except Exception:
                    role_msg = f" (Bot lacks permissions to assign **{role_name}**.)"
            else:
                role_msg = f" (Please ask an admin to create the **{role_name}** role!)"

            embed = discord.Embed(title="ACCESS GRANTED", color=discord.Color.green())
            embed.description = f"Decryption successful.{role_msg}\n\n*Proceed to the next access tier, {ctx.author.name}.*"
            
            if user['is_traitor']:
                embed.set_footer(text="[ENCRYPTED OVERRIDE] Traitor status active. Continue spreading misinformation.")

            await ctx.send(embed=embed)
        else:
            await db.pool.execute(
                "UPDATE arg_users SET last_submission = $1 WHERE user_id = $2",
                datetime.now(timezone.utc).replace(tzinfo=None), ctx.author.id
            )
            embed = discord.Embed(title="ACCESS DENIED", color=discord.Color.red())
            embed.description = "Incorrect sequence. The system has logged your attempt."
            
            if user['is_traitor']:
                 embed.set_footer(text="[ENCRYPTED] Even the architect must find the key.")
                 
            await ctx.send(embed=embed)

    @submit.error
    async def submit_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⚠️ **LOCKOUT PROTOCOL ACTIVE.** Please wait {error.retry_after:.1f}s before trying again.")

    @commands.command(name="arg_status")
    async def arg_status(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        user = await self.get_or_create_user(member.id)
        
        embed = discord.Embed(title=f"CLASSIFIED DOSSIER: {member.name}", color=discord.Color.dark_gray())
        embed.add_field(name="Current Phase", value=f"Tier {user['current_phase']}", inline=True)
        embed.add_field(name="Puzzles Solved", value=f"{user['puzzles_solved']}", inline=True)
        
        if user['is_traitor'] and ctx.author.id == member.id:
            embed.add_field(name="HIDDEN DIRECTIVE", value="You are a secret Traitor. Your objective is to derail progress without being caught.", inline=False)
            
        await ctx.send(embed=embed)

    @commands.command(name="arg_set_traitor")
    @commands.has_permissions(administrator=True)
    async def arg_set_traitor(self, ctx, member: discord.Member, status: bool):
        await self.get_or_create_user(member.id)
        await db.pool.execute("UPDATE arg_users SET is_traitor = $1 WHERE user_id = $2", status, member.id)
        state_str = "an active Traitor" if status else "no longer a Traitor"
        await ctx.message.delete()
        await ctx.author.send(f"System Overridden. Agent {member.name} is now {state_str}.")

async def setup(bot):
    await bot.add_cog(ARG(bot))
