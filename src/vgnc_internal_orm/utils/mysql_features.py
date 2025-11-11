"""
MySQL-specific features implementation including UTF8MB4 charset support,
full-text search capabilities, and query optimization utilities.
"""

import re
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from sqlalchemy import Index, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import TextClause

from vgnc_internal_orm.config.settings import DatabaseConfig


class UTF8MB4Handler:
    """
    Handles UTF8MB4 charset operations for MySQL connections and data validation.

    Provides utilities for proper UTF8MB4 charset handling including emoji support,
    international characters, and encoding conversion validation.
    """

    # Characters that require UTF8MB4 (beyond basic UTF8)
    UTF8MB4_REQUIRED_CHARS = [
        "\U0001f600",  # 😀 grinning face emoji
        "\U0001f300",  # 🎰 slot machine emoji
        "\U0001f170",  # 🅰️ A button emoji
        "\U00002600",  # ♠️ black spade suit
        "\U00002700",  # ✂️ black scissors
    ]

    # Common UTF8MB4 character ranges
    EMOJI_RANGES = [
        (0x1F300, 0x1F5FF),  # Misc Symbols & Pictographs
        (0x1F600, 0x1F64F),  # Emoticons
        (0x1F680, 0x1F6FF),  # Transport & Map
        (0x1F700, 0x1F77F),  # Alchemical Symbols
        (0x1F780, 0x1F7FF),  # Geometric Shapes
        (0x1F800, 0x1F8FF),  # Supplemental Arrows-C
        (0x1F900, 0x1F9FF),  # Supplemental Symbols & Pictographs
        (0x2600, 0x26FF),  # Misc Symbols
        (0x2700, 0x27BF),  # Dingbats
    ]

    @classmethod
    def requires_utf8mb4(cls, text: str) -> bool:
        """
        Check if text contains characters that require UTF8MB4 encoding.

        Args:
            text: String to check

        Returns:
            True if text contains characters requiring UTF8MB4
        """
        if not text:
            return False

        for char in text:
            char_code = ord(char)

            # Check if character is in emoji ranges
            for start, end in cls.EMOJI_RANGES:
                if start <= char_code <= end:
                    return True

            # Check for other 4-byte characters
            if char_code > 0xFFFF:
                return True

        return False

    @classmethod
    def validate_utf8mb4_support(cls, engine: Engine) -> dict[str, Any]:
        """
        Validate that the MySQL connection supports UTF8MB4.

        Args:
            engine: SQLAlchemy engine

        Returns:
            Dictionary with validation results
        """
        result: dict[str, Any] = {
            "supported": False,
            "charset": None,
            "collation": None,
            "connection_support": False,
            "server_support": False,
            "errors": [],
        }

        with engine.connect() as conn:
            try:
                # Check connection charset
                charset_result = conn.execute(
                    text("SELECT VARIABLES('character_set_connection')")
                ).scalar()
                result["charset"] = charset_result

                # Check connection collation
                collation_result = conn.execute(
                    text("SELECT VARIABLES('collation_connection')")
                ).scalar()
                result["collation"] = collation_result

                # Check if connection uses UTF8MB4
                result["connection_support"] = (
                    charset_result and "utf8mb4" in charset_result.lower()
                )

                # Check server UTF8MB4 support
                server_charset = conn.execute(
                    text("SELECT VARIABLES('character_set_server')")
                ).scalar()
                result["server_support"] = (
                    server_charset and "utf8mb4" in server_charset.lower()
                )

                result["supported"] = (
                    result["connection_support"] and result["server_support"]
                )

                if not result["supported"]:
                    if not result["connection_support"]:
                        result["errors"].append(
                            f"Connection does not use UTF8MB4: {charset_result}"
                        )
                    if not result["server_support"]:
                        result["errors"].append(
                            f"Server does not support UTF8MB4: {server_charset}"
                        )

            except Exception as e:
                result["errors"].append(f"Validation failed: {str(e)}")

        return result

    @classmethod
    def build_connection_string(cls, config: DatabaseConfig) -> str:
        """
        Build MySQL connection string with proper UTF8MB4 charset parameters.

        Args:
            config: Database configuration

        Returns:
            Modified connection string with UTF8MB4 charset
        """
        base_url = config.database_url.get_secret_value()

        if not base_url.startswith("mysql"):
            return base_url

        # Parse existing URL
        parsed = urlparse(base_url)

        # Get existing query parameters
        query_params = parse_qs(parsed.query)

        # Add UTF8MB4 charset parameters
        query_params.update(
            {
                "charset": ["utf8mb4"],
                "collation": ["utf8mb4_unicode_ci"],
                "use_unicode": ["1"],
                "autocommit": ["true"],
            }
        )

        # Build new query string
        new_query = urlencode(query_params, doseq=True)

        # Reconstruct URL
        new_parsed = parsed._replace(query=new_query)
        return urlunparse(new_parsed)

    @classmethod
    def convert_text_field(cls, text: str, target_encoding: str = "utf-8") -> bytes:
        """
        Convert text to bytes with proper UTF8MB4 encoding validation.

        Args:
            text: Text to convert
            target_encoding: Target encoding (default: utf-8)

        Returns:
            Encoded bytes

        Raises:
            UnicodeEncodeError: If text contains characters that can't be encoded
        """
        try:
            return text.encode(target_encoding)
        except UnicodeEncodeError as e:
            # Provide detailed error message
            problematic_chars = []
            for i, char in enumerate(text):
                try:
                    char.encode(target_encoding)
                except UnicodeEncodeError:
                    problematic_chars.append(f"pos {i}: '{char}' (U+{ord(char):04X})")

            error_msg = (
                f"Text contains {len(problematic_chars)} characters "
                f"that can't be encoded in {target_encoding}: "
                f"{', '.join(problematic_chars[:5])}"
                f"{'...' if len(problematic_chars) > 5 else ''}"
            )

            raise UnicodeEncodeError(
                e.encoding, e.object, e.start, e.end, error_msg
            ) from e

    @classmethod
    def sanitize_for_basic_utf8(cls, text: str, replacement: str = "?") -> str:
        """
        Sanitize text by removing or replacing characters that require UTF8MB4.

        Useful for legacy systems that don't support UTF8MB4.

        Args:
            text: Text to sanitize
            replacement: Character to replace unsupported characters

        Returns:
            Sanitized text
        """
        if not text:
            return text

        result_chars = []
        for char in text:
            char_code = ord(char)

            # Check if character requires UTF8MB4
            requires_mb4 = False
            for start, end in cls.EMOJI_RANGES:
                if start <= char_code <= end:
                    requires_mb4 = True
                    break

            if char_code > 0xFFFF or requires_mb4:
                result_chars.append(replacement)
            else:
                result_chars.append(char)

        return "".join(result_chars)

    @classmethod
    def get_charset_info(cls, session: Session) -> dict[str, str]:
        """
        Get comprehensive charset information from MySQL session.

        Args:
            session: SQLAlchemy session

        Returns:
            Dictionary with charset information
        """
        charset_vars = [
            "character_set_client",
            "character_set_connection",
            "character_set_database",
            "character_set_results",
            "character_set_server",
            "character_set_system",
            "collation_connection",
            "collation_database",
            "collation_server",
        ]

        info = {}
        for var in charset_vars:
            try:
                value = session.execute(text(f"SELECT VARIABLES('{var}')")).scalar()
                info[var] = value or "unknown"
            except Exception:
                info[var] = "error"

        return info


class MySQLConnectionPool:
    """
    MySQL-specific connection pool configuration with UTF8MB4 support.
    """

    @staticmethod
    def get_pool_config(
        pool_size: int = 5,
        max_overflow: int = 10,
        pool_timeout: int = 30,
        pool_recycle: int = 3600,
        pool_pre_ping: bool = True,
    ) -> dict[str, Any]:
        """
        Get optimized connection pool configuration for MySQL.

        Args:
            pool_size: Number of connections to maintain
            max_overflow: Additional connections beyond pool_size
            pool_timeout: Seconds to wait for connection
            pool_recycle: Seconds before recycling connection
            pool_pre_ping: Validate connections before use

        Returns:
            Dictionary with pool configuration
        """
        return {
            "pool_size": pool_size,
            "max_overflow": max_overflow,
            "pool_timeout": pool_timeout,
            "pool_recycle": pool_recycle,
            "pool_pre_ping": pool_pre_ping,
            "pool_reset_on_return": "commit",
        }

    @staticmethod
    def create_engine_with_utf8mb4(config: DatabaseConfig) -> Engine:
        """
        Create SQLAlchemy engine with UTF8MB4 charset and optimized pool settings.

        Args:
            config: Database configuration

        Returns:
            Configured SQLAlchemy engine
        """
        from sqlalchemy import create_engine

        # Build connection string with UTF8MB4
        connection_string = UTF8MB4Handler.build_connection_string(config)

        # Get pool configuration
        pool_config = MySQLConnectionPool.get_pool_config()

        # Create engine with MySQL-specific settings
        engine = create_engine(
            connection_string,
            echo=config.echo,
            future=True,
            **pool_config,
            # MySQL-specific options
            connect_args={
                "charset": "utf8mb4",
                "collation": "utf8mb4_unicode_ci",
                "use_unicode": True,
                "autocommit": True,
                "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
            },
        )

        return engine


class CharsetValidator:
    """
    Validates and handles charset conversions for text data.
    """

    @staticmethod
    def validate_text_encoding(text: str, encoding: str = "utf-8") -> dict[str, Any]:
        """
        Validate text encoding and provide detailed analysis.

        Args:
            text: Text to validate
            encoding: Target encoding

        Returns:
            Validation result with analysis
        """
        result: dict[str, Any] = {
            "valid": True,
            "encoding": encoding,
            "length": len(text),
            "bytes_length": 0,
            "requires_utf8mb4": False,
            "problematic_chars": [],
            "emoji_count": 0,
            "errors": [],
        }

        if not text:
            return result

        try:
            # Try to encode
            encoded = text.encode(encoding)
            result["bytes_length"] = len(encoded)

            # Analyze characters
            for i, char in enumerate(text):
                char_code = ord(char)

                # Check for emoji/UTF8MB4 characters
                if UTF8MB4Handler.requires_utf8mb4(char):
                    result["requires_utf8mb4"] = True
                    result["problematic_chars"].append(
                        {
                            "position": i,
                            "character": char,
                            "code": f"U+{char_code:04X}",
                            "description": CharsetValidator._get_char_description(
                                char_code
                            ),
                        }
                    )

                # Count emoji
                for start, end in UTF8MB4Handler.EMOJI_RANGES:
                    if start <= char_code <= end:
                        result["emoji_count"] += 1
                        break

        except UnicodeEncodeError as e:
            result["valid"] = False
            result["errors"].append(str(e))

        return result

    @staticmethod
    def _get_char_description(char_code: int) -> str:
        """Get human-readable description of character."""
        if char_code == 0x1F600:
            return "Grinning Face Emoji"
        elif char_code == 0x1F603:
            return "Smiling Face with Open Mouth"
        elif 0x1F300 <= char_code <= 0x1F5FF:
            return "Misc Symbol/Pictograph"
        elif 0x1F600 <= char_code <= 0x1F64F:
            return "Emoticon"
        elif 0x1F680 <= char_code <= 0x1F6FF:
            return "Transport/Map Symbol"
        elif char_code > 0xFFFF:
            return "4-byte Unicode Character"
        else:
            return "Unicode Character"


class FullTextSearch:
    """
    MySQL full-text search query builder with support for different search modes.

    Provides optimized full-text search capabilities for MySQL text fields
    with support for natural language, boolean, and query expansion modes.
    """

    class SearchMode:
        """Search mode constants."""

        NATURAL_LANGUAGE = "IN NATURAL LANGUAGE MODE"
        BOOLEAN_MODE = "IN BOOLEAN MODE"
        QUERY_EXPANSION = "WITH QUERY EXPANSION"
        NATURAL_LANGUAGE_WITH_EXPANSION = (
            "IN NATURAL LANGUAGE MODE WITH QUERY EXPANSION"
        )

    class BooleanOperators:
        """Boolean search operators."""

        AND = "+"
        NOT = "-"
        OR = " "  # Space
        EXACT_PHRASE = '"'

    @staticmethod
    def create_fulltext_index(
        table_name: str, columns: list[str], index_name: str | None = None
    ) -> Index:
        """
        Create a SQLAlchemy Index object for MySQL full-text search.

        Args:
            table_name: Name of the table
            columns: List of column names to index
            index_name: Optional name for the index

        Returns:
            SQLAlchemy Index object configured for full-text search
        """
        if not index_name:
            index_name = f"fti_{table_name}_{'_'.join(columns)}"

        # Create index with MySQL-specific DDL
        index = Index(
            index_name,
            *columns,
            mysql_prefix="FULLTEXT",
            mysql_with_parser="ngram",  # For better tokenization
        )

        return index

    @staticmethod
    def build_match_query(
        columns: list[str],
        search_query: str,
        mode: str = SearchMode.NATURAL_LANGUAGE,
        relevance_threshold: float | None = None,
    ) -> TextClause:
        """
        Build MySQL MATCH() AGAINST() query for full-text search.

        Args:
            columns: List of columns to search
            search_query: Search query string
            mode: Search mode (from SearchMode class)
            relevance_threshold: Optional minimum relevance score

        Returns:
            SQLAlchemy text clause for MATCH() AGAINST()
        """
        # Escape search query to prevent SQL injection
        FullTextSearch._escape_search_query(search_query)

        # Build MATCH clause
        columns_str = ", ".join(columns)
        match_clause = f"MATCH({columns_str}) AGAINST(:search_query {mode})"

        if relevance_threshold is not None:
            match_clause += f" > {relevance_threshold}"

        return text(match_clause)

    @staticmethod
    def build_relevance_query(
        columns: list[str], search_query: str, mode: str = SearchMode.NATURAL_LANGUAGE
    ) -> TextClause:
        """
        Build query to calculate relevance score for full-text search.

        Args:
            columns: List of columns to search
            search_query: Search query string
            mode: Search mode

        Returns:
            SQLAlchemy text clause for relevance scoring
        """
        FullTextSearch._escape_search_query(search_query)
        columns_str = ", ".join(columns)

        return text(
            f"MATCH({columns_str}) AGAINST(:search_query {mode}) as relevance_score"
        )

    @staticmethod
    def build_boolean_search_query(search_terms: list[str]) -> str:
        """
        Build boolean search query from list of terms.

        Args:
            search_terms: List of search terms with optional operators

        Returns:
            Formatted boolean search string
        """
        processed_terms = []

        for term in search_terms:
            term = term.strip()
            if not term:
                continue

            # Handle operators
            if term.startswith("+"):
                # Must include
                processed_terms.append(f"+{FullTextSearch._escape_term(term[1:])}")
            elif term.startswith("-"):
                # Must not include
                processed_terms.append(f"-{FullTextSearch._escape_term(term[1:])}")
            elif term.startswith('"') and term.endswith('"'):
                # Exact phrase
                processed_terms.append(f'"{FullTextSearch._escape_term(term[1:-1])}"')
            else:
                # Optional term
                processed_terms.append(FullTextSearch._escape_term(term))

        return " ".join(processed_terms)

    @staticmethod
    def parse_search_query(query: str) -> dict[str, Any]:
        """
        Parse and analyze a search query.

        Args:
            query: Search query to parse

        Returns:
            Dictionary with parsed components and analysis
        """
        result: dict[str, Any] = {
            "original": query,
            "terms": [],
            "phrases": [],
            "required_terms": [],
            "excluded_terms": [],
            "boolean_operators": False,
            "special_chars": [],
            "length": len(query),
            "word_count": len(query.split()),
        }

        # Parse quoted phrases
        phrase_pattern = r'"([^"]+)"'
        phrases = re.findall(phrase_pattern, query)
        result["phrases"] = phrases

        # Remove phrases from query for further processing
        query_without_phrases = re.sub(phrase_pattern, "", query)

        # Parse individual terms
        for term in query_without_phrases.split():
            term = term.strip()
            if not term:
                continue

            if term.startswith("+"):
                result["required_terms"].append(term[1:])
                result["boolean_operators"] = True
            elif term.startswith("-"):
                result["excluded_terms"].append(term[1:])
                result["boolean_operators"] = True
            else:
                result["terms"].append(term)

            # Check for special characters
            if re.search(r'[+\-*<>()~"]', term):
                result["special_chars"].append(term)

        return result

    @staticmethod
    def optimize_search_query(query: str) -> str:
        """
        Optimize search query for better performance and accuracy.

        Args:
            query: Original search query

        Returns:
            Optimized search query
        """
        if not query or not query.strip():
            return ""

        # Parse the query
        parsed = FullTextSearch.parse_search_query(query)

        optimized_terms = []

        # Add required terms
        for term in parsed["required_terms"]:
            if len(term) >= 2:  # Skip very short terms
                optimized_terms.append(f"+{term}")

        # Add regular terms (limit to avoid performance issues)
        for term in parsed["terms"][:10]:  # Limit to 10 terms
            if len(term) >= 3:  # Skip very short terms
                optimized_terms.append(term)

        # Add phrases (limit length)
        for phrase in parsed["phrases"][:3]:  # Limit to 3 phrases
            if len(phrase) >= 3:
                optimized_terms.append(f'"{phrase}"')

        # Add excluded terms
        for term in parsed["excluded_terms"]:
            if len(term) >= 2:
                optimized_terms.append(f"-{term}")

        return " ".join(optimized_terms) if optimized_terms else ""

    @staticmethod
    def _escape_search_query(query: str) -> str:
        """Escape search query to prevent SQL injection."""
        if not query:
            return ""

        # Escape special characters
        escaped = query.replace("\\", "\\\\")
        escaped = escaped.replace("'", "\\'")
        escaped = escaped.replace('"', '\\"')

        return escaped

    @staticmethod
    def _escape_term(term: str) -> str:
        """Escape individual search term."""
        if not term:
            return ""

        # Remove dangerous characters but keep allowed operators
        escaped = re.sub(r"[<>()~*]", "", term)
        escaped = escaped.replace("\\", "\\\\")
        escaped = escaped.replace("'", "\\'")
        escaped = escaped.replace('"', '\\"')

        return escaped

    @staticmethod
    def get_search_suggestions(
        original_query: str, max_suggestions: int = 5
    ) -> list[str]:
        """
        Generate alternative search suggestions.

        Args:
            original_query: Original search query
            max_suggestions: Maximum number of suggestions

        Returns:
            List of alternative search queries
        """
        suggestions = []

        # Parse original query
        parsed = FullTextSearch.parse_search_query(original_query)

        # Suggestion 1: Add quotes for phrase matching
        if parsed["terms"] and not parsed["phrases"]:
            if len(parsed["terms"]) >= 2:
                phrase_suggestion = f'"{" ".join(parsed["terms"][:2])}"'
                suggestions.append(phrase_suggestion)

        # Suggestion 2: Remove very short terms
        filtered_terms = [t for t in parsed["terms"] if len(t) >= 3]
        if filtered_terms != parsed["terms"]:
            suggestions.append(" ".join(filtered_terms))

        # Suggestion 3: Focus on required terms
        if parsed["required_terms"]:
            required_query = " ".join([f"+{t}" for t in parsed["required_terms"]])
            suggestions.append(required_query)

        # Suggestion 4: Use boolean mode with operators
        if not parsed["boolean_operators"] and parsed["terms"]:
            boolean_query = " ".join(parsed["terms"][:3])  # Limit terms
            suggestions.append(boolean_query)

        # Suggestion 5: Expand phrases
        if parsed["phrases"]:
            for phrase in parsed["phrases"][:1]:
                words = phrase.split()
                if len(words) > 1:
                    expanded = " ".join(words)
                    suggestions.append(expanded)

        return suggestions[:max_suggestions]

    @staticmethod
    def analyze_search_performance(
        session: Session, table_name: str, columns: list[str], test_queries: list[str]
    ) -> dict[str, Any]:
        """
        Analyze full-text search performance for different queries.

        Args:
            session: SQLAlchemy session
            table_name: Table to search
            columns: Columns to search
            test_queries: List of test queries

        Returns:
            Performance analysis results
        """
        results: dict[str, Any] = {
            "table_name": table_name,
            "columns": columns,
            "queries": [],
            "total_time": 0,
            "index_exists": False,
        }

        # Check if full-text index exists
        try:
            index_result = session.execute(
                text(
                    f"""
                SHOW INDEX FROM {table_name}
                WHERE Index_type LIKE '%FULLTEXT%'
            """
                )
            ).fetchall()

            results["index_exists"] = len(index_result) > 0

        except Exception as e:
            results["index_error"] = str(e)

        columns_str = ", ".join(columns)

        for query in test_queries:
            query_result = {
                "query": query,
                "execution_time": 0,
                "result_count": 0,
                "error": None,
            }

            try:
                import time

                start_time = time.time()

                # Execute search query
                search_sql = f"""
                    SELECT COUNT(*) as count
                    FROM {table_name}
                    WHERE MATCH({columns_str}) AGAINST(:query IN NATURAL LANGUAGE MODE)
                """

                count_result = session.execute(
                    text(search_sql), {"query": query}
                ).scalar()

                end_time = time.time()

                query_result["execution_time"] = end_time - start_time
                query_result["result_count"] = count_result or 0

            except Exception as e:
                query_result["error"] = str(e)

            results["queries"].append(query_result)
            results["total_time"] += query_result["execution_time"]

        return results


class MySQLQueryOptimizer:
    """
    MySQL-specific query optimization utilities and hint injection.

    Provides optimization strategies, index suggestions, and query plan analysis
    specifically for MySQL database performance enhancement.
    """

    class HintType:
        """MySQL optimization hint types."""

        STRAIGHT_JOIN = "STRAIGHT_JOIN"
        USE_INDEX = "USE INDEX"
        FORCE_INDEX = "FORCE INDEX"
        IGNORE_INDEX = "IGNORE INDEX"
        SQL_CACHE = "SQL_CACHE"
        SQL_NO_CACHE = "SQL_NO_CACHE"
        SQL_BUFFER_RESULT = "SQL_BUFFER_RESULT"
        SQL_BIG_RESULT = "SQL_BIG_RESULT"
        SQL_SMALL_RESULT = "SQL_SMALL_RESULT"

    @staticmethod
    def analyze_query_plan(
        session: Session, query: str, use_analyze: bool = True
    ) -> dict[str, Any]:
        """
        Analyze MySQL query execution plan.

        Args:
            session: SQLAlchemy session
            query: SQL query to analyze
            use_analyze: Whether to use EXPLAIN ANALYZE (MySQL 8.0+)

        Returns:
            Query plan analysis results
        """
        explain_type = "EXPLAIN ANALYZE" if use_analyze else "EXPLAIN"

        try:
            # Get query plan
            plan_sql = f"{explain_type} {str(query)}"
            plan_result = session.execute(text(plan_sql)).fetchall()

            # Parse plan results
            plan_details = []
            for row in plan_result:
                plan_row = (
                    dict(row._mapping) if hasattr(row, "_mapping") else row._asdict()
                )
                plan_details.append(plan_row)

            # Analyze plan for optimization opportunities
            analysis = MySQLQueryOptimizer._analyze_plan_for_optimizations(plan_details)

            return {
                "query": str(query),
                "explain_type": explain_type,
                "plan": plan_details,
                "analysis": analysis,
                "warnings": MySQLQueryOptimizer._detect_plan_warnings(plan_details),
            }

        except Exception as e:
            return {
                "query": str(query),
                "error": str(e),
                "plan": [],
                "analysis": {},
                "warnings": [],
            }

    @staticmethod
    def suggest_indexes(
        session: Session, table_name: str, query_patterns: list[str]
    ) -> dict[str, Any]:
        """
        Suggest optimal indexes based on query patterns.

        Args:
            session: SQLAlchemy session
            table_name: Table to analyze
            query_patterns: List of common query patterns

        Returns:
            Index suggestions with analysis
        """
        suggestions: dict[str, Any] = {
            "table": table_name,
            "suggested_indexes": [],
            "existing_indexes": [],
            "query_analysis": [],
            "missing_indexes": [],
        }

        try:
            # Get existing indexes
            existing_indexes_sql = f"SHOW INDEX FROM {table_name}"
            existing_indexes_rows = session.execute(
                text(existing_indexes_sql)
            ).fetchall()

            # Convert rows to dictionaries for both suggestions and analysis
            existing_indexes = []
            for idx in existing_indexes_rows:
                index_info = {
                    "name": idx.Index_name,
                    "columns": [idx.Column_name] if idx.Column_name else [],
                    "unique": idx.Non_unique == 0,
                    "type": idx.Index_type,
                    "cardinality": idx.Cardinality,
                }
                suggestions["existing_indexes"].append(index_info)
                existing_indexes.append(index_info)

            # Analyze each query pattern
            for pattern in query_patterns:
                query_analysis = MySQLQueryOptimizer._analyze_query_for_indexes(
                    pattern, table_name, existing_indexes
                )
                suggestions["query_analysis"].append(query_analysis)

                # Extract index suggestions from query analysis
                for suggestion in query_analysis.get("index_suggestions", []):
                    if suggestion not in suggestions["suggested_indexes"]:
                        suggestions["suggested_indexes"].append(suggestion)

            # Compare with existing indexes to find missing ones
            existing_index_signatures = [
                tuple(sorted(idx["columns"]))
                for idx in suggestions["existing_indexes"]
                if idx["columns"]
            ]

            for suggested in suggestions["suggested_indexes"]:
                suggested_signature = tuple(sorted(suggested["columns"]))
                if suggested_signature not in existing_index_signatures:
                    suggestions["missing_indexes"].append(suggested)

        except Exception as e:
            suggestions["error"] = [str(e)]

        return suggestions

    @staticmethod
    def inject_hints(query: str, hints: list[str]) -> TextClause:
        """
        Inject MySQL optimization hints into a query.

        Args:
            query: Original SQL query
            hints: List of hints to inject

        Returns:
            Query with optimization hints injected
        """
        query_str = str(query).strip()

        if not query_str.upper().startswith("SELECT"):
            return text(query_str)  # Only apply to SELECT queries

        # Find the position after SELECT
        select_upper = query_str.upper()
        select_pos = select_upper.find("SELECT")

        if select_pos == -1:
            return text(query_str)

        # Find the end of SELECT keyword
        after_select = select_pos + 6  # Length of 'SELECT'

        # Find the first non-whitespace character after SELECT
        while after_select < len(query_str) and query_str[after_select].isspace():
            after_select += 1

        # Build hints string
        if hints:
            hints_str = " ".join(hints)
            # Insert hints between SELECT and the first column
            # Remove extra space for better formatting
            modified_query = (
                query_str[:after_select] + " " + hints_str + query_str[after_select:]
            )
        else:
            modified_query = query_str

        return text(modified_query)

    @staticmethod
    def optimize_join_query(
        query: str,
        join_columns: dict[str, list[str]],
        force_index: bool = False,
    ) -> TextClause:
        """
        Optimize JOIN queries with appropriate hints.

        Args:
            query: JOIN query to optimize
            join_columns: Dictionary mapping table names to join columns
            force_index: Whether to use FORCE INDEX instead of USE INDEX

        Returns:
            Optimized JOIN query with hints
        """
        hints = []

        # Add STRAIGHT_JOIN for complex queries with multiple joins
        if "JOIN" in str(query).upper() and str(query).upper().count("JOIN") > 2:
            hints.append(MySQLQueryOptimizer.HintType.STRAIGHT_JOIN)

        # Add index hints for each table in the join
        hint_type = (
            MySQLQueryOptimizer.HintType.FORCE_INDEX
            if force_index
            else MySQLQueryOptimizer.HintType.USE_INDEX
        )

        for table, columns in join_columns.items():
            if columns:
                index_hint = f"{hint_type} ({', '.join(columns)})"
                hints.append(f"{table} {index_hint}")

        return MySQLQueryOptimizer.inject_hints(query, hints)

    @staticmethod
    def get_slow_query_analysis(
        session: Session, min_execution_time: float = 1.0, limit: int = 10
    ) -> dict[str, Any]:
        """
        Analyze slow queries from MySQL slow query log.

        Args:
            session: SQLAlchemy session
            min_execution_time: Minimum execution time in seconds
            limit: Maximum number of queries to analyze

        Returns:
            Slow query analysis results
        """
        analysis: dict[str, Any] = {
            "queries": [],
            "patterns": {},
            "recommendations": [],
            "total_slow_queries": 0,
        }

        try:
            # Check if slow query log is enabled
            log_status = session.execute(
                text("SHOW VARIABLES LIKE 'slow_query_log'")
            ).fetchone()

            if not log_status or log_status.Value != "ON":
                analysis["warning"] = "Slow query log is not enabled"
                return analysis

            # Get slow queries (this is a simplified example)
            # In practice, you might need to parse the slow query log file
            slow_queries_sql = f"""
                SELECT
                    sql_text,
                    exec_count,
                    timer_wait/1000000000 as avg_time_seconds,
                    lock_time/1000000000 as avg_lock_time_seconds
                FROM performance_schema.events_statements_summary_by_digest
                WHERE timer_wait/1000000000 > {min_execution_time}
                ORDER BY timer_wait DESC
                LIMIT {limit}
            """

            slow_queries = session.execute(text(slow_queries_sql)).fetchall()

            for query in slow_queries:
                query_info = {
                    "sql": (
                        query.sql_text[:500] + "..."
                        if len(query.sql_text) > 500
                        else query.sql_text
                    ),
                    "exec_count": query.exec_count,
                    "avg_time": query.avg_time_seconds,
                    "avg_lock_time": query.avg_lock_time_seconds,
                    "optimization_suggestions": MySQLQueryOptimizer._analyze_slow_query(
                        query.sql_text
                    ),
                }
                analysis["queries"].append(query_info)

            analysis["total_slow_queries"] = len(analysis["queries"])

            # Extract common patterns
            MySQLQueryOptimizer._extract_query_patterns(analysis)

        except Exception as e:
            analysis["error"] = str(e)

        return analysis

    @staticmethod
    def _analyze_plan_for_optimizations(
        plan_details: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Analyze query plan for optimization opportunities."""
        analysis: dict[str, Any] = {
            "table_scans": [],
            "filesorts": [],
            "temporary_tables": [],
            "index_usage": [],
            "joins": [],
            "recommendations": [],
        }

        for step in plan_details:
            # Check for table scans (bad)
            if "ALL" in step.get("type", "").upper():
                analysis["table_scans"].append(step.get("table", "unknown"))
                analysis["recommendations"].append(
                    f"Consider adding index for table '{step.get('table')}'"
                )

            # Check for filesort (bad)
            if "filesort" in step.get("Extra", "").lower():
                analysis["filesorts"].append(step.get("table", "unknown"))
                analysis["recommendations"].append(
                    f"Consider optimizing ORDER BY for table '{step.get('table')}'"
                )

            # Check for temporary tables (bad)
            if "temporary" in step.get("Extra", "").lower():
                analysis["temporary_tables"].append(step.get("table", "unknown"))
                analysis["recommendations"].append(
                    f"Consider rewriting query to avoid temporary table for '{step.get('table')}'"
                )

            # Check index usage
            if step.get("key") and step.get("key") != "NULL":
                analysis["index_usage"].append(
                    {
                        "table": step.get("table"),
                        "index": step.get("key"),
                        "type": step.get("type"),
                    }
                )

            # Check join types
            if (
                "ref" in step.get("type", "").lower()
                or "eq_ref" in step.get("type", "").lower()
            ):
                analysis["joins"].append(
                    {
                        "table": step.get("table"),
                        "type": step.get("type"),
                        "key": step.get("key"),
                    }
                )

        return analysis

    @staticmethod
    def _detect_plan_warnings(plan_details: list[dict[str, Any]]) -> list[str]:
        """Detect potential warnings in query plan."""
        warnings = []

        for step in plan_details:
            extra = step.get("Extra", "").lower()
            table_name = step.get("table", "unknown")

            # Performance warnings
            if "using filesort" in extra:
                warnings.append(
                    f"Filesort detected for table '{table_name}' - consider optimizing ORDER BY"
                )

            if "using temporary" in extra:
                warnings.append(
                    f"Temporary table created for '{table_name}' - consider query rewrite"
                )

            if step.get("type") == "ALL":
                warnings.append(f"Full table scan on '{table_name}' - missing index")

            # Cardinality warnings
            rows = step.get("rows", 0)
            if rows > 100000:
                warnings.append(
                    f"Large number of rows ({rows}) estimated for '{table_name}'"
                )

        return warnings

    @staticmethod
    def _analyze_query_for_indexes(
        query_pattern: str, table_name: str, existing_indexes: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Analyze a query pattern for index requirements."""
        analysis: dict[str, Any] = {
            "query": query_pattern,
            "table": table_name,
            "where_columns": [],
            "order_by_columns": [],
            "group_by_columns": [],
            "join_columns": [],
            "index_suggestions": [],
        }

        # Simple regex-based parsing (in practice, you'd use a SQL parser)
        import re

        # Extract WHERE conditions
        where_match = re.search(
            r"WHERE\s+(.+?)(?:\s+ORDER\s+BY|\s+GROUP\s+BY|\s+LIMIT|$)",
            query_pattern,
            re.IGNORECASE | re.DOTALL,
        )
        if where_match:
            where_clause = where_match.group(1)
            # Extract column names from simple conditions
            column_matches = re.findall(r"(\w+)\s*[=<>!]", where_clause)
            analysis["where_columns"] = list(set(column_matches))

        # Extract ORDER BY columns
        order_match = re.search(
            r"ORDER\s+BY\s+(.+?)(?:\s+GROUP\s+BY|\s+LIMIT|$)",
            query_pattern,
            re.IGNORECASE,
        )
        if order_match:
            order_clause = order_match.group(1)
            order_columns = [col.strip().split()[0] for col in order_clause.split(",")]
            analysis["order_by_columns"] = order_columns

        # Extract GROUP BY columns
        group_match = re.search(
            r"GROUP\s+BY\s+(.+?)(?:\s+ORDER\s+BY|\s+LIMIT|$)",
            query_pattern,
            re.IGNORECASE,
        )
        if group_match:
            group_clause = group_match.group(1)
            group_columns = [col.strip().split()[0] for col in group_clause.split(",")]
            analysis["group_by_columns"] = group_columns

        # Extract JOIN columns
        join_matches = re.findall(
            r"JOIN\s+\w+\s+ON\s+(\w+)\.(\w+)\s*=\s*(\w+)\.(\w+)",
            query_pattern,
            re.IGNORECASE,
        )
        for join_match in join_matches:
            if join_match[0] == table_name:
                join_cols = analysis["join_columns"]
                if isinstance(join_cols, list):
                    join_cols.append(join_match[1])
            elif join_match[2] == table_name:
                join_cols = analysis["join_columns"]
                if isinstance(join_cols, list):
                    join_cols.append(join_match[3])

        # Generate index suggestions
        where_cols = analysis["where_columns"]
        order_cols = analysis["order_by_columns"]
        group_cols = analysis["group_by_columns"]
        join_cols = analysis["join_columns"]

        all_columns = set()
        if isinstance(where_cols, list):
            all_columns.update(where_cols)
        if isinstance(order_cols, list):
            all_columns.update(order_cols)
        if isinstance(group_cols, list):
            all_columns.update(group_cols)
        if isinstance(join_cols, list):
            all_columns.update(join_cols)

        if all_columns:
            # Primary suggestion: composite index covering WHERE and ORDER BY
            where_cols = analysis["where_columns"]
            order_cols = analysis["order_by_columns"]
            if isinstance(where_cols, list) and isinstance(order_cols, list):
                primary_columns = where_cols + order_cols
            else:
                primary_columns = []

            if primary_columns:
                index_suggestions = analysis["index_suggestions"]
                if isinstance(index_suggestions, list):
                    index_suggestions.append(
                        {
                            "type": "composite",
                            "columns": primary_columns,
                            "purpose": "where_and_order",
                            "priority": "high",
                        }
                    )

            # Secondary suggestions
            join_cols = analysis["join_columns"]
            if isinstance(join_cols, list) and join_cols:
                index_suggestions = analysis["index_suggestions"]
                if isinstance(index_suggestions, list):
                    index_suggestions.append(
                        {
                            "type": "simple",
                            "columns": join_cols,
                            "purpose": "join",
                            "priority": "high",
                        }
                    )

            group_cols = analysis["group_by_columns"]
            if isinstance(group_cols, list) and group_cols:
                index_suggestions = analysis["index_suggestions"]
                if isinstance(index_suggestions, list):
                    index_suggestions.append(
                        {
                            "type": "composite",
                            "columns": analysis["group_by_columns"],
                            "purpose": "group_by",
                            "priority": "medium",
                        }
                    )

        return analysis

    @staticmethod
    def _analyze_slow_query(sql_text: str) -> list[str]:
        """Analyze slow query and provide optimization suggestions."""
        suggestions = []

        sql_upper = sql_text.upper()

        # Check for missing WHERE clause
        if "WHERE" not in sql_upper and "SELECT" in sql_upper:
            suggestions.append("Consider adding WHERE clause to limit result set")

        # Check for SELECT *
        if "SELECT *" in sql_upper:
            suggestions.append("Avoid SELECT * - specify only needed columns")

        # Check for ORDER BY without index
        if "ORDER BY" in sql_upper and "LIMIT" not in sql_upper:
            suggestions.append("Consider adding LIMIT clause or index for ORDER BY")

        # Check for subqueries
        if "SELECT" in sql_upper and sql_upper.count("SELECT") > 1:
            suggestions.append("Consider rewriting subqueries as JOINs")

        # Check for complex expressions in WHERE
        if re.search(r"WHERE.*\(.*\+.*\)", sql_upper):
            suggestions.append(
                "Avoid calculations in WHERE clause - consider indexed columns"
            )

        return suggestions

    @staticmethod
    def _extract_query_patterns(analysis: dict[str, Any]) -> None:
        """Extract common patterns from slow queries."""
        patterns: dict[str, dict[str, Any]] = {
            "tables_used": {},
            "operations": {},
            "issues": {},
        }

        for query_info in analysis["queries"]:
            sql = query_info["sql"].upper()

            # Count table usage
            table_matches = re.findall(r"FROM\s+(\w+)", sql)
            for table in table_matches:
                patterns["tables_used"][table] = (
                    patterns["tables_used"].get(table, 0) + 1
                )

            # Count operations
            if "JOIN" in sql:
                patterns["operations"]["joins"] = (
                    patterns["operations"].get("joins", 0) + 1
                )
            if "GROUP BY" in sql:
                patterns["operations"]["group_by"] = (
                    patterns["operations"].get("group_by", 0) + 1
                )
            if "ORDER BY" in sql:
                patterns["operations"]["order_by"] = (
                    patterns["operations"].get("order_by", 0) + 1
                )

            # Count common issues
            if "SELECT *" in sql:
                patterns["issues"]["select_star"] = (
                    patterns["issues"].get("select_star", 0) + 1
                )
            if "WHERE" not in sql:
                patterns["issues"]["no_where"] = (
                    patterns["issues"].get("no_where", 0) + 1
                )

        analysis["patterns"] = patterns
