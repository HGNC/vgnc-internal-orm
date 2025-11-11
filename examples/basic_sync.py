"""Basic synchronous usage example.
Run: python examples/basic_sync.py
"""
from sqlalchemy import select
from vgnc_internal_orm.config.settings import get_settings
from vgnc_internal_orm.sessions.factory import SessionFactory
from vgnc_internal_orm.models import Species  # Import from models module to ensure all models are registered
from vgnc_internal_orm.models.base import BaseModel, BaseCustomModel


def main():
    settings = get_settings()
    sf = SessionFactory(settings.database)

    # For demo purposes, create tables without foreign key constraints
    # In a real application, you would use proper migrations (Alembic)
    print("Creating database tables without foreign key constraints for demo...")

    # Create BaseModel tables first
    try:
        BaseModel.metadata.create_all(sf.engine)
        print("BaseModel tables created successfully.")
    except Exception as e:
        print(f"Error creating BaseModel tables: {e}")

    # Create individual tables from BaseCustomModel that we need
    try:
        # Just create the species table directly for this demo
        from sqlalchemy import Table, MetaData, text
        species_table = Table('species', MetaData(), autoload_with=sf.engine)
        print("Species table already exists or found.")
    except Exception:
        # Create species table using direct SQL
        from sqlalchemy import text
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
        print("Species table created directly.")

    print("Database tables setup complete.")

    session = sf.create_session()
    try:
        # Create or fetch some species (demo assumes existing data or empty result)
        rows = session.execute(select(Species).limit(5)).scalars().all()
        print("Fetched species rows:", rows)

        if rows:
            # Use helper find
            found = Species.find(session, limit=3)
            print("Helper find():", found)
        else:
            print("No species found in database. Tables are empty.")
    finally:
        session.close()


if __name__ == "__main__":
    main()
