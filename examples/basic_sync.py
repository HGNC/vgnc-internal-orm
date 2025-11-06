"""Basic synchronous usage example.
Run: python examples/basic_sync.py
"""
from sqlalchemy import select
from vgnc_internal_orm.config.settings import get_settings
from vgnc_internal_orm.sessions.factory import SessionFactory
from vgnc_internal_orm.models.species import Species


def main():
    settings = get_settings()
    sf = SessionFactory(settings.database)
    with sf.get_session() as session:
        # Create or fetch some species (demo assumes existing data or empty result)
        rows = session.execute(select(Species).limit(5)).scalars().all()
        print("Fetched species rows:", rows)

        if rows:
            # Use helper find
            found = Species.find(session, limit=3)
            print("Helper find():", found)


if __name__ == "__main__":
    main()
