from app.db.base import BaseDBT


async def create_all(async_engine):
    async with async_engine.begin() as conn:
        await conn.run_sync(BaseDBT.metadata.create_all)
