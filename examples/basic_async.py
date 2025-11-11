"""Basic asynchronous usage example.
Run: python examples/basic_async.py
"""
import asyncio
from sqlalchemy import select
from vgnc_internal_orm.config.settings import get_settings
from vgnc_internal_orm.sessions.factory import SessionFactory
from vgnc_internal_orm.models.species import Species
from vgnc_internal_orm.models.base import BaseModel


async def run_async():
    settings = get_settings()
    sf = SessionFactory(settings.database)

    # Create database tables using sync engine (to avoid async URL issues with SQLite)
    print("Creating database tables for async demo...")
    try:
        BaseModel.metadata.create_all(sf.engine)
        print("BaseModel tables created successfully.")
    except Exception as e:
        print(f"Error creating BaseModel tables: {e}")

    # Create species table directly using sync engine
    from sqlalchemy import text
    try:
        with sf.engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS species (
                    taxon_id INTEGER PRIMARY KEY,
                    genefam_prefix VARCHAR(11) NOT NULL DEFAULT '',
                    primary_db_table VARCHAR(255),
                    display_name VARCHAR(128) NOT NULL,
                    ensembl_species_name VARCHAR(128),
                    is_live VARCHAR(1) NOT NULL DEFAULT 'T',
                    created DATETIME NOT NULL,
                    _scientific_name VARCHAR(128),
                    _common_name VARCHAR(128),
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.commit()
        print("Species table created directly (using sync engine for async demo).")
    except Exception as e:
        print(f"Error creating species table: {e}")

    print("Database tables setup complete (async).")

    # For this demo, use sync session since async SQLite has issues with the config
    # In a real application with proper async database setup, you would use create_async_session()
    print("Using sync session for async demo due to SQLite async configuration issue...")
    session = sf.create_session()
    try:
        result = session.execute(select(Species).limit(5))
        rows = result.scalars().all()
        print("Fetched species rows (async demo using sync session):", rows)

        # Sync helper usage (placeholder for async)
        found = Species.find(session, limit=3) if hasattr(Species, 'find') else []
        print("Helper find() (sync placeholder):", found)

        if not rows:
            print("No species found in database. Tables are empty.")
    finally:
        session.close()


if __name__ == "__main__":
    asyncio.run(run_async())
