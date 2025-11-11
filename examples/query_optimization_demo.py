"""Query optimization demonstration.
Run: python examples/query_optimization_demo.py
"""
from sqlalchemy import select
from vgnc_internal_orm.config.settings import get_settings
from vgnc_internal_orm.sessions.factory import SessionFactory
from vgnc_internal_orm.models.genefam import Genefam
from vgnc_internal_orm.models.species import Species
from vgnc_internal_orm.utils.query_optimizer import (
    QueryOptimizer,
    LoadingStrategy,
    QueryOptimization,
    QueryProfiler,
)


def main():
    settings = get_settings()
    sf = SessionFactory(settings.database)

    # Create database tables (same approach as basic examples)
    print("Creating database tables for query optimization demo...")
    try:
        from vgnc_internal_orm.models.base import BaseModel
        BaseModel.metadata.create_all(sf.engine)
        print("BaseModel tables created successfully.")
    except Exception as e:
        print(f"Error creating BaseModel tables: {e}")

    # Create species and genefam tables directly
    from sqlalchemy import text
    try:
        with sf.engine.connect() as conn:
            # Species table
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

            # Genefam table (simplified version without foreign key constraints)
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS genefam (
                    genefam_id INTEGER PRIMARY KEY,
                    taxon_id INTEGER NOT NULL,
                    assigned_id VARCHAR(50),
                    assigned_symbol VARCHAR(255),
                    assigned_name VARCHAR(255),
                    status_id INTEGER,
                    editor_id INTEGER,
                    hcop_support_level VARCHAR(20),
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.commit()
        print("Species and Genefam tables created directly.")
    except Exception as e:
        print(f"Error creating tables: {e}")

    print("Database tables setup complete.")

    session = sf.create_session()
    try:
        optimizer = QueryOptimizer(session)
        optimizations = [
            QueryOptimization(
                model=Genefam,
                loading_strategy=LoadingStrategy.SELECTIN,
                relationships=["species"],
            )
        ]
        query = optimizer.get_optimized_query(Genefam, optimizations, filter_conditions=None)
        profiler = QueryProfiler(session)
        with profiler.profile_query():
            rows = optimizer.execute_optimized_query(query)
        stats = profiler.get_stats()
        print(f"Rows fetched: {len(rows)} | Stats: {stats}")

        # Direct eager loading example
        direct = session.execute(
            select(Species).options()
        ).scalars().all()
        print("Fetched species count (direct):", len(direct))

        if len(direct) == 0:
            print("No data found - tables are empty.")
    finally:
        session.close()


if __name__ == "__main__":
    main()
