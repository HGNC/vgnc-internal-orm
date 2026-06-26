"""Unit tests for the pure query-building methods of FullTextSearch.

These methods construct SQL fragments / parse search strings and have no
database dependency, so they are exercised here directly to cover the
formatting, escaping, and parsing branches.
"""

from vgnc_internal_orm.utils.mysql_features import FullTextSearch

NATURAL = "IN NATURAL LANGUAGE MODE"
BOOLEAN = "IN BOOLEAN MODE"


class TestFullTextSearchQueryBuilders:
    def test_build_match_query_basic(self):
        clause = FullTextSearch.build_match_query(["c1", "c2"], "query", mode=NATURAL)
        rendered = str(clause)
        assert "MATCH(c1, c2)" in rendered
        assert "AGAINST(:search_query" in rendered
        assert NATURAL in rendered

    def test_build_match_query_with_threshold(self):
        clause = FullTextSearch.build_match_query(
            ["c1"], "query", mode=NATURAL, relevance_threshold=0.5
        )
        rendered = str(clause)
        assert "> 0.5" in rendered

    def test_build_relevance_query(self):
        clause = FullTextSearch.build_relevance_query(["a", "b"], "q", mode=BOOLEAN)
        rendered = str(clause)
        assert "MATCH(a, b)" in rendered
        assert "as relevance_score" in rendered


class TestFullTextSearchBooleanQuery:
    def test_required_and_excluded_terms(self):
        result = FullTextSearch.build_boolean_search_query(["+alpha", "-beta"])
        assert "+alpha" in result
        assert "-beta" in result

    def test_exact_phrase(self):
        result = FullTextSearch.build_boolean_search_query(['"a phrase"'])
        assert '"a phrase"' in result

    def test_optional_term(self):
        result = FullTextSearch.build_boolean_search_query(["gamma"])
        assert "gamma" in result

    def test_empty_terms_ignored(self):
        result = FullTextSearch.build_boolean_search_query(["", "   ", "keep"])
        assert "keep" in result
        # Whitespace-only / empty entries contribute nothing
        assert result.strip() == "keep"


class TestFullTextSearchParse:
    def test_parse_simple_terms(self):
        parsed = FullTextSearch.parse_search_query("alpha beta")
        assert parsed["terms"] == ["alpha", "beta"]
        assert parsed["word_count"] == 2
        assert parsed["length"] == len("alpha beta")
        assert parsed["boolean_operators"] is False

    def test_parse_boolean_operators(self):
        parsed = FullTextSearch.parse_search_query("+need -avoid optional")
        assert parsed["required_terms"] == ["need"]
        assert parsed["excluded_terms"] == ["avoid"]
        assert parsed["boolean_operators"] is True
        assert "optional" in parsed["terms"]

    def test_parse_phrases(self):
        parsed = FullTextSearch.parse_search_query('"exact phrase" word')
        assert parsed["phrases"] == ["exact phrase"]
        assert "word" in parsed["terms"]

    def test_parse_special_chars(self):
        parsed = FullTextSearch.parse_search_query("+term")
        # '+' is a special char marker
        assert parsed["special_chars"]


class TestFullTextSearchOptimize:
    def test_optimize_normal_query(self):
        optimized = FullTextSearch.optimize_search_query("+required loose")
        assert "+required" in optimized
        assert "loose" in optimized

    def test_optimize_empty_returns_empty(self):
        assert FullTextSearch.optimize_search_query("") == ""
        assert FullTextSearch.optimize_search_query("   ") == ""

    def test_optimize_drops_short_terms(self):
        # Terms shorter than the thresholds are filtered out
        optimized = FullTextSearch.optimize_search_query("ab +x")
        # 'ab' (<3 chars) dropped from optional, 'x' (<2) dropped from required
        assert optimized == ""

    def test_optimize_includes_phrase(self):
        optimized = FullTextSearch.optimize_search_query('"a nice phrase"')
        assert '"a nice phrase"' in optimized


class TestFullTextSearchEscaping:
    def test_escape_search_query_quotes_and_backslash(self):
        assert FullTextSearch._escape_search_query("a'b") == "a\\'b"
        assert FullTextSearch._escape_search_query('a"b') == 'a\\"b'
        assert FullTextSearch._escape_search_query("a\\b") == "a\\\\b"

    def test_escape_search_query_empty(self):
        assert FullTextSearch._escape_search_query("") == ""

    def test_escape_term_returns_string(self):
        assert isinstance(FullTextSearch._escape_term("term"), str)
        assert FullTextSearch._escape_term("") == ""
