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
    with sf.get_session() as session:
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


if __name__ == "__main__":
    main()
