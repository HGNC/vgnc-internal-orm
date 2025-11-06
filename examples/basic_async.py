"""Basic asynchronous usage example.
Run: python examples/basic_async.py
"""
import asyncio
from sqlalchemy import select
from vgnc_internal_orm.config.settings import get_settings
from vgnc_internal_orm.sessions.factory import SessionFactory
from vgnc_internal_orm.models.species import Species


async def run_async():
    settings = get_settings()
    sf = SessionFactory(settings.database)
    async with sf.get_async_session() as session:
        result = await session.execute(select(Species).limit(5))
        rows = result.scalars().all()
        print("Fetched species rows (async):", rows)

        # Async helper usage if available
        found = await Species.afind(session, limit=3)
        print("Helper afind():", found)


if __name__ == "__main__":
    asyncio.run(run_async())
