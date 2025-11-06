"""MySQL full-text search demo (will no-op if not on MySQL).
Run: python examples/full_text_search_demo.py
"""
from sqlalchemy import text
from vgnc_internal_orm.config.settings import get_settings
from vgnc_internal_orm.sessions.factory import SessionFactory
from vgnc_internal_orm.models.genefam import Genefam
from vgnc_internal_orm.utils.mysql_features import FullTextSearch


def main():
    settings = get_settings()
    if settings.database.driver != "mysql":
        print("Skipping demo: not a MySQL driver.")
        return

    sf = SessionFactory(settings.database)
    with sf.get_session() as session:
        match_clause = FullTextSearch.build_match_query(["assigned_name", "assigned_symbol"], "kinase")
        sql = f"SELECT * FROM genefam WHERE {match_clause.text}"  # Using built MATCH() clause
        rows = session.execute(text(sql), {"search_query": "kinase"}).fetchmany(5)
        print("Top 5 full-text results:")
        for r in rows:
            print(r)


if __name__ == "__main__":
    main()
