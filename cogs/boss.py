import discord
from discord.ext import commands, tasks
from database import db
import random
from datetime import datetime, timezone, timedelta

class Boss(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.boss_idle_heal.start()

    def cog_unload(self):
        self.boss_idle_heal.cancel()

    async def get_or_create_boss(self):
        boss = await db.pool.fetchrow("SELECT * FROM boss LIMIT 1")
        if not boss:
            await db.pool.execute(
                "INSERT INTO boss (boss_name, hp, max_hp, shield_active, rage_mode, defense_mode, phase) VALUES ($1, $2, $3, $4, $5, $6, $7)",
                "Great Dragon", 2000, 2000, False, False, 'Normal', 1
            )
            boss = await db.pool.fetchrow("SELECT * FROM boss LIMIT 1")
        return boss

    async def update_boss_phase(self, ctx, boss):
        hp_percent = boss['hp'] / boss['max_hp']
        new_phase = boss['phase']
        rage_mode = boss['rage_mode']

        if hp_percent <= 0.30 and boss['phase'] < 3:
            new_phase = 3
            rage_mode = True
            await ctx.send("🚨 **WARNING! THE BOSS HAS ENTERED RAGE MODE!** (Damage reduced by 25%, counterattacks doubled!)")
        elif hp_percent <= 0.60 and boss['phase'] < 2:
            new_phase = 2
            await ctx.send("⚠️ The boss enters **Phase 2!** Its defense patterns will change more frequently.")
            
        if new_phase != boss['phase'] or rage_mode != boss['rage_mode']:
            await db.pool.execute("UPDATE boss SET phase = $1, rage_mode = $2 WHERE boss_id = $3", new_phase, rage_mode, boss['boss_id'])
            
    async def process_boss_ability(self, ctx, boss):
        attacks_taken = boss['attacks_taken'] + 1
        await db.pool.execute("UPDATE boss SET attacks_taken = $1 WHERE boss_id = $2", attacks_taken, boss['boss_id'])
        
        # Trigger an ability every 5 attacks
        if attacks_taken % 5 == 0:
            abilities = ['Coin Drain', 'Regeneration']
            
            # Additional abilities based on phase
            if boss['phase'] >= 2:
                defense_modes = ['Shield Mode', 'Evasion Mode', 'Shadow Mode', 'Normal Mode']
                new_defense = random.choice(defense_modes)
                await db.pool.execute("UPDATE boss SET defense_mode = $1 WHERE boss_id = $2", new_defense, boss['boss_id'])
                await ctx.send(f"🌌 The boss shifted its stance to **{new_defense}**!")
                
            ability = random.choice(abilities)
            
            if ability == 'Coin Drain':
                # Take 5% from random active users? Or just the current attacker
                user = await db.get_user(ctx.author.id)
                lost_coins = int(user['coins'] * 0.05) if user['coins'] > 0 else 0
                if lost_coins > 0:
                    await db.update_user(ctx.author.id, coins=user['coins'] - lost_coins)
                    await ctx.send(f"🦇 **Coin Drain!** The boss stole {lost_coins} coins from {ctx.author.mention}!")
            
            elif ability == 'Regeneration':
                heal_amount = int(boss['max_hp'] * 0.05)
                new_hp = min(boss['max_hp'], boss['hp'] + heal_amount)
                await db.pool.execute("UPDATE boss SET hp = $1 WHERE boss_id = $2", new_hp, boss['boss_id'])
                await ctx.send(f"⚕️ **Regeneration!** The boss healed for {heal_amount} HP!")

    async def log_attack(self, user_id, attack_type, damage):
        await db.pool.execute(
            "INSERT INTO boss_logs (user_id, attack_type, damage, timestamp) VALUES ($1, $2, $3, $4)",
            user_id, attack_type, damage, datetime.now(timezone.utc).replace(tzinfo=None)
        )

    @commands.group(name="attack", invoke_without_command=True)
    async def attack(self, ctx):
        await ctx.send("Available attacks: `!attack normal`, `!attack heavy`, `!attack crit`")

    @attack.command(name="normal")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def attack_normal(self, ctx):
        await self._process_attack(ctx, "normal", 50, 100, miss_chance=0.0)

    @attack.command(name="heavy")
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def attack_heavy(self, ctx):
        await self._process_attack(ctx, "heavy", 100, 200, miss_chance=0.3)

    @attack.command(name="crit")
    @commands.cooldown(1, 300, commands.BucketType.user) # 5 mins
    async def attack_crit(self, ctx):
        await self._process_attack(ctx, "crit", 250, 400, miss_chance=0.0)

    async def _process_attack(self, ctx, attack_type, min_dmg, max_dmg, miss_chance):
        boss = await self.get_or_create_boss()
        
        if boss['hp'] <= 0:
            ctx.command.reset_cooldown(ctx)
            return await ctx.send("💀 The boss is already defeated! Waiting for spawn.")

        # Miss logic
        if random.random() < miss_chance:
            return await ctx.send(f"💨 {ctx.author.mention}'s {attack_type} attack missed the boss completely!")

        # Defense mode augmentations
        if boss['defense_mode'] == 'Evasion Mode' and attack_type == 'heavy':
            if random.random() < 0.5: # 50% extra miss
                return await ctx.send(f"💨 The boss evaded {ctx.author.mention}'s heavy attack! (Evade Mode)")
                
        # Base damage calculation
        damage = random.randint(min_dmg, max_dmg)
        
        # User special power modifiers
        user = await db.get_user(ctx.author.id)
        if not user:
            await db.create_user(ctx.author.id)
            user = await db.get_user(ctx.author.id)
            
        if user['active_power'] == 'doubledamage':
            damage *= 2
            await db.update_user(ctx.author.id, active_power=None)
            await ctx.send("💥 Double Damage triggered!")

        # Boss modifiers
        if boss['defense_mode'] == 'Shield Mode' or boss['shield_active']:
            damage = int(damage * 0.5)
            
        if boss['defense_mode'] == 'Shadow Mode' and attack_type != 'crit':
            damage = int(damage * 0.2) # Shadow mode reduces everything except crit heavily
            
        if boss['rage_mode']:
            damage = int(damage * 0.75)

        # Ensure min damage
        damage = max(1, damage)
        new_hp = max(0, boss['hp'] - damage)
        
        await db.pool.execute("UPDATE boss SET hp = $1, last_activity = $2 WHERE boss_id = $3", 
                              new_hp, datetime.now(timezone.utc).replace(tzinfo=None), boss['boss_id'])
        await self.log_attack(ctx.author.id, attack_type, damage)

        # Counters and Abilities
        await self.process_boss_ability(ctx, boss)
        
        # Reward
        coins_reward = damage // 3
        await db.update_user(ctx.author.id, coins=user['coins'] + coins_reward, last_attack=datetime.now(timezone.utc).replace(tzinfo=None))
        
        embed = discord.Embed(description=f"⚔️ {ctx.author.mention} used **{attack_type}** and dealt **{damage}** damage!", color=discord.Color.orange())
        
        # Boss Defeated Logic
        if new_hp == 0:
            await self._handle_boss_death(ctx, boss)
        else:
            # Check Phase progression
            await self.update_boss_phase(ctx, boss)
            
            # Counterattack logic
            counter_chance = 0.2 if boss['rage_mode'] else 0.1
            if random.random() < counter_chance:
                counter_dmg = random.randint(5, 50)
                lost_coins = min(user['coins'] + coins_reward, counter_dmg)
                await db.update_user(ctx.author.id, coins=(user['coins'] + coins_reward) - lost_coins)
                embed.add_field(name="⚠️ Counterattack!", value=f"The boss struck back, causing you to drop **{lost_coins} coins**!", inline=False)
            
            embed.set_footer(text=f"Boss HP: {new_hp}/{boss['max_hp']}")
            await ctx.send(embed=embed)

    async def _handle_boss_death(self, ctx, old_boss):
        # Fetch Top Attackers from boss_logs
        records = await db.pool.fetch("""
            SELECT user_id, SUM(damage) as total_damage 
            FROM boss_logs 
            GROUP BY user_id 
            ORDER BY total_damage DESC LIMIT 5
        """)
        
        embed = discord.Embed(title="🏆 THE BOSS HAS BEEN DEFEATED!", color=discord.Color.gold())
        embed.description = "The raid was successful! Distributing rewards..."
        
        for idx, rec in enumerate(records):
            bonus = 0
            if idx == 0: bonus = 5000
            elif idx == 1: bonus = 3000
            elif idx == 2: bonus = 1000
            else: bonus = 500
            
            u = await db.get_user(rec['user_id'])
            if u:
                await db.update_user(rec['user_id'], coins=u['coins'] + bonus)
            embed.add_field(name=f"Rank {idx+1}", value=f"<@{rec['user_id']}>\nDmg: {rec['total_damage']} | Bonus: {bonus}🪙", inline=False)
            
        await ctx.send(embed=embed)
        
        # Scale next boss based on active attackers in 24h
        active_users = await db.pool.fetchval("""
            SELECT COUNT(DISTINCT user_id) FROM boss_logs 
            WHERE timestamp > NOW() - INTERVAL '24 hours'
        """)
        
        new_max_hp = 2000 + (active_users * 150)
        
        # Reset and Cleanup
        await db.pool.execute("DELETE FROM boss_logs")
        await db.pool.execute("""
            UPDATE boss 
            SET hp = $1, max_hp = $1, shield_active = False, 
                rage_mode = False, defense_mode = 'Normal', phase = 1, attacks_taken = 0
        """, new_max_hp)
        await ctx.send(f"A new, stronger boss emerges from the shadows... (HP: {new_max_hp})")

    @commands.group(name="power", invoke_without_command=True)
    async def power(self, ctx):
        await ctx.send("Available powers: `!power shieldbreaker`, `!power doubledamage`\n*(Note: 10m global cooldown on powers)*")

    @power.command(name="shieldbreaker")
    async def power_sb(self, ctx):
        await self._use_power(ctx, "shieldbreaker")

    @power.command(name="doubledamage")
    async def power_dd(self, ctx):
        await self._use_power(ctx, "doubledamage")

    async def _use_power(self, ctx, power_type):
        user = await db.get_user(ctx.author.id)
        if not user:
            await db.create_user(ctx.author.id)
            user = await db.get_user(ctx.author.id)

        now = datetime.now(timezone.utc)
        if user['special_power_cooldown']:
            cd = user['special_power_cooldown'].replace(tzinfo=timezone.utc) if user['special_power_cooldown'].tzinfo is None else user['special_power_cooldown']
            if now - cd < timedelta(minutes=10):
                left_mins = 10 - int((now - cd).total_seconds() // 60)
                return await ctx.send(f"⏳ Special powers are on cooldown. Try again in {left_mins}m.")

        boss = await self.get_or_create_boss()
        
        if power_type == "shieldbreaker":
            if not boss['shield_active'] and boss['defense_mode'] != 'Shield Mode':
                return await ctx.send("❌ Boss does not currently have a shield active.")
            await db.pool.execute("UPDATE boss SET shield_active = False, defense_mode = 'Normal' WHERE boss_id = $1", boss['boss_id'])
            await ctx.send("🛡️🔨 You shattered the boss's shield!")
            
        elif power_type == "doubledamage":
            await db.update_user(ctx.author.id, active_power='doubledamage')
            await ctx.send("🔥 Your next attack will deal DOUBLE damage!")

        await db.update_user(ctx.author.id, special_power_cooldown=now.replace(tzinfo=None))


    @tasks.loop(minutes=5.0)
    async def boss_idle_heal(self):
        boss = await db.pool.fetchrow("SELECT hp, max_hp, last_activity, boss_id FROM boss LIMIT 1")
        if not boss or not boss['last_activity']: return
        
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        if (now - boss['last_activity']).total_seconds() > 1800: # 30 mins
            if boss['hp'] > 0 and boss['hp'] < boss['max_hp']:
                heal = int(boss['max_hp'] * 0.05)
                new_hp = min(boss['max_hp'], boss['hp'] + heal)
                await db.pool.execute("UPDATE boss SET hp = $1 WHERE boss_id = $2", new_hp, boss['boss_id'])

    @boss_idle_heal.before_loop
    async def before_idle_heal(self):
        await self.bot.wait_until_ready()

    @commands.command(name="boss")
    async def boss_info(self, ctx):
        boss = await self.get_or_create_boss()
        if not boss: return await ctx.send("❌ No boss currently active.")

        embed = discord.Embed(title=f"👹 Boss: {boss['boss_name']} (Phase {boss['phase']})", color=discord.Color.red())
        hp_bar_length = 20
        fill = int((boss['hp'] / boss['max_hp']) * hp_bar_length)
        bar = "█" * fill + "░" * (hp_bar_length - fill)
        
        status = boss['defense_mode']
        if boss['rage_mode']: status += " | RAGE MODE 😡"
        
        embed.add_field(name="HP", value=f"`{bar}`\n**{boss['hp']} / {boss['max_hp']}**", inline=False)
        embed.add_field(name="Stance", value=f"🛡️ {status}", inline=False)
        await ctx.send(embed=embed)

    @attack_normal.error
    @attack_heavy.error
    @attack_crit.error
    async def attack_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            # Format time beautifully
            seconds = int(error.retry_after)
            if seconds > 60:
                mins, secs = divmod(seconds, 60)
                await ctx.send(f"⏳ Skill on cooldown! Try again in {mins}m {secs}s.")
            else:
                await ctx.send(f"⏳ Skill on cooldown! Try again in {seconds}s.")

async def setup(bot):
    await bot.add_cog(Boss(bot))
