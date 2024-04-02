import aiopg
from utils.config import DB_CONFIG


class DatabaseManager:
    def __init__(self, logger):
        self.pool = None
        self.logger = logger

    async def create_pool(self):
        self.pool = await aiopg.create_pool(**DB_CONFIG)
        self.logger.info("Database pool created")
        return self.pool

    async def save_user_to_db(self, user_id, full_name, phone, user_name):
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("INSERT INTO users (id, full_name, phone, user_name) VALUES (%s, %s, %s, %s)",
                                     (user_id, full_name, str(phone), user_name))
                self.logger.info("User data saved to the database")

    async def get_user_timing_from_db(self, user_id):
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT selected_date, selected_time FROM user_schedule WHERE user_id = %s",
                                     (user_id,))
                user_timing = await cursor.fetchall()
                self.logger.info("User timing data retrieved from the database")
                return user_timing

    async def check_user_in_db(self, user_id):
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
                user_exists = await cursor.fetchone()
                self.logger.info("Checked user existence in the database")
                return user_exists

    async def get_user_dates_from_db(self, user_id):
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT DISTINCT selected_date FROM user_schedule WHERE user_id = %s", (user_id,))
                user_dates = [row[0] for row in await cursor.fetchall()]
                return user_dates

    async def get_available_hours_from_db(self, selected_date):
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT DISTINCT selected_time FROM user_schedule WHERE selected_date = %s",
                                     (selected_date,))
                available_hours = {row[0] for row in await cursor.fetchall()}
                return sorted(available_hours)

    async def delete_all_schedule_from_db(self, user_id):
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "DELETE FROM user_schedule WHERE user_id = %s",
                    (user_id,))

    async def delete_selected_schedule_from_db(self, user_id, selected_date_for_del, hour_selected):
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "DELETE FROM user_schedule WHERE user_id = %s AND selected_date = %s AND selected_time IN %s",
                    (user_id, selected_date_for_del, tuple(hour_selected)))

    async def insert_selected_schedule_in_db(self, user_id, selected_date_for_del, hour_selected):
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                for hour in hour_selected:
                    await cursor.execute(
                        "INSERT INTO user_schedule (user_id, selected_date, selected_time) VALUES (%s, %s, %s)",
                        (user_id, selected_date_for_del, hour))

    async def get_busy_hours(self, selected_date):
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT selected_time FROM user_schedule WHERE selected_date = %s",
                                     (selected_date,))
                busy_hours = await cursor.fetchall()
                busy_hours_flat = [item for sublist in busy_hours for item in sublist]
                return set(busy_hours_flat)
