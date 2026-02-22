import asyncpg
import logging
import os
from config import DATABASE_URL

log = logging.getLogger(__name__)

class DatabaseSchema:
    @staticmethod
    async def create_tables(pool):
        # Read the schema file
        schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
        with open(schema_path, "r", encoding="utf-8") as f:
            schema = f.read()
        await pool.execute(schema)
        
        # Initialize default boss if not exists
        boss_exists = await pool.fetchval("SELECT COUNT(*) FROM boss")
        if boss_exists == 0:
            await pool.execute(
                "INSERT INTO boss (boss_name, hp, max_hp) VALUES ($1, $2, $3)", 
                "Great Dragon", 10000, 10000
            )

class Database:
    def __init__(self):
        self.pool = None

    async def connect(self):
        try:
            self.pool = await asyncpg.create_pool(DATABASE_URL)
            await DatabaseSchema.create_tables(self.pool)
            log.info("Connected to PostgreSQL database and ensured schema exists.")
        except Exception as e:
            log.error(f"Failed to connect to database: {e}")

    async def get_user(self, user_id: int):
        query = "SELECT * FROM users WHERE user_id = $1"
        return await self.pool.fetchrow(query, user_id)

    async def create_user(self, user_id: int):
        query = "INSERT INTO users (user_id) VALUES ($1) ON CONFLICT (user_id) DO NOTHING"
        await self.pool.execute(query, user_id)

    async def update_user(self, user_id: int, **kwargs):
        if not kwargs:
            return
        set_clause = ", ".join([f"{key} = ${i+2}" for i, key in enumerate(kwargs.keys())])
        values = list(kwargs.values())
        query = f"UPDATE users SET {set_clause} WHERE user_id = $1"
        await self.pool.execute(query, user_id, *values)

    async def process_message_rewards(self, user_id: int, xp_gain: int, coin_gain: int):
        query = """
            INSERT INTO users (user_id, xp, coins, message_count) 
            VALUES ($1, $2, $3, 1) 
            ON CONFLICT (user_id) DO UPDATE 
            SET xp = users.xp + $2, 
                coins = users.coins + $3, 
                message_count = users.message_count + 1
            RETURNING xp, level, coins, message_count
        """
        return await self.pool.fetchrow(query, user_id, xp_gain, coin_gain)

db = Database()
