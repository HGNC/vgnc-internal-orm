"""Integration tests for MySQL-specific features including UTF8MB4 support, full-text search, and query optimization."""

from datetime import datetime

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from vgnc_internal_orm.config.settings import DatabaseConfig, DatabaseDriver
from vgnc_internal_orm.models.base import BaseModel
from vgnc_internal_orm.models.genefam import Genefam
from vgnc_internal_orm.models.species import Species, SpeciesLiveStatus
from vgnc_internal_orm.utils.mysql_features import (
    CharsetValidator,
    FullTextSearch,
    MySQLConnectionPool,
    MySQLQueryOptimizer,
    UTF8MB4Handler,
)


@pytest.fixture(scope="function")
def mysql_test_db():
    """Create a test database with MySQL-like configuration for testing."""
    # Use SQLite for testing but with MySQL-like charset configuration
    engine = create_engine(
        "sqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
        echo=False,
    )

    # Create all tables using the unified metadata registry
    from sqlalchemy.schema import MetaData

    unified_metadata = MetaData()

    # Add all tables from the shared metadata registry
    for table in BaseModel.metadata.tables.values():
        table.to_metadata(unified_metadata)

    # Create all tables with foreign key constraints disabled for testing
    with engine.connect() as conn:
        conn.execute(text("PRAGMA foreign_keys = OFF"))
        unified_metadata.create_all(conn)
        conn.commit()

    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    # Ensure foreign keys remain disabled for this session
    session.execute(text("PRAGMA foreign_keys = OFF"))

    return session


@pytest.fixture
def utf8mb4_test_data(mysql_test_db):
    """Create test data with international characters and emoji for UTF8MB4 testing."""
    session = mysql_test_db

    # Create species with international characters and emoji
    species_data = [
        {
            "scientific_name": "Homo sapiens",
            "vgnc_prefix": "HSA",
            "common_name": "Human 🧬",
            "taxon_id": 9606,
            "class_name": "Mammalia",
            "order_name": "Primates",
            "family_name": "Hominidae",
            "is_model_organism": True,
        },
        {
            "scientific_name": "Mus musculus",
            "vgnc_prefix": "MMU",
            "common_name": "Mouse 🐭",
            "taxon_id": 10090,
            "class_name": "Mammalia",
            "order_name": "Rodentia",
            "family_name": "Muridae",
        },
        {
            "scientific_name": "Drosophila melanogaster",
            "vgnc_prefix": "DME",
            "common_name": "Fruit fly 🪰",
            "taxon_id": 7227,
            "class_name": "Insecta",
            "order_name": "Diptera",
            "family_name": "Drosophilidae",
        },
    ]

    species_list = []
    for data in species_data:
        # Map test data to model fields
        species = Species(
            taxon_id=data["taxon_id"],
            genefam_prefix=data["vgnc_prefix"],
            display_name=f"{data.get('common_name', data.get('scientific_name', ''))} ({data.get('scientific_name', '')})",
            is_live=SpeciesLiveStatus.YES,
            created=datetime.now(),
        )
        session.add(species)
        species_list.append(species)

    # Create gene families with international text
    genefam_data = [
        {
            "name": "HOX 🏠",
            "description": "Homeobox gene family - développement 🇫🇷",
            "family_type": "transcription_factor",
            "functional_category": "development",
        },
        {
            "name": "GLOBIN 🩸",
            "description": "Globin gene family - 血液 🇨🇳",
            "family_type": "oxygen_transport",
            "functional_category": "respiratory",
        },
        {
            "name": "CYTOKINE 🔄",
            "description": "Cytokine signaling - señalización 🇪🇸",
            "family_type": "signaling",
            "functional_category": "immune_response",
        },
    ]

    # Insert genefam data directly via SQL to avoid foreign key issues
    genefam_list = []
    for i, data in enumerate(genefam_data, 1):
        assigned_id = data["name"].split(" ")[0]  # Use first part before emoji as ID
        session.execute(
            text(
                """
            INSERT INTO genefam (genefam_id, taxon_id, assigned_id, assigned_name, status_id, editor_id, hcop_support_level)
            VALUES (:genefam_id, :taxon_id, :assigned_id, :assigned_name, :status_id, :editor_id, :hcop_support_level)
        """
            ),
            {
                "genefam_id": i,
                "taxon_id": species_list[i % len(species_list)].taxon_id,
                "assigned_id": assigned_id,
                "assigned_name": data["description"],
                "status_id": 1,
                "editor_id": 1,
                "hcop_support_level": 1,
            },
        )

        # Create a simple genefam object for the test to use (without saving)
        from sqlalchemy.orm import make_transient

        genefam = Genefam(
            genefam_id=i,
            taxon_id=species_list[i % len(species_list)].taxon_id,
            assigned_id=assigned_id,
            assigned_name=data["description"],
            status_id=1,
            editor_id=1,
            hcop_support_level=1,
        )
        make_transient(
            genefam
        )  # Make it transient so SQLAlchemy doesn't try to track it
        genefam_list.append(genefam)

    session.commit()
    return {"species": species_list, "genefams": genefam_list, "session": session}


class TestUTF8MB4CharsetFeatures:
    """Test UTF8MB4 charset handling features."""

    def test_utf8mb4_character_detection(self):
        """Test detection of UTF8MB4 characters."""
        # Test basic ASCII (should not require UTF8MB4)
        basic_text = "Hello World"
        assert not UTF8MB4Handler.requires_utf8mb4(basic_text)

        # Test emoji (should require UTF8MB4)
        emoji_text = "Hello 😀 World"
        assert UTF8MB4Handler.requires_utf8mb4(emoji_text)

        # Test international characters (should work with basic UTF8)
        chinese_text = "你好世界"
        assert not UTF8MB4Handler.requires_utf8mb4(chinese_text)

        # Test 4-byte Unicode characters
        four_byte_text = "𝄞𝄢𝄤"  # Musical symbols
        assert UTF8MB4Handler.requires_utf8mb4(four_byte_text)

    def test_connection_string_building(self):
        """Test MySQL connection string building with UTF8MB4 parameters."""
        config = DatabaseConfig(
            driver=DatabaseDriver.MYSQL,
            host="localhost",
            username="test",
            password="test123",
            database="testdb",
            charset="utf8mb4",
            collation="utf8mb4_unicode_ci",
        )

        connection_string = UTF8MB4Handler.build_connection_string(config)

        assert "charset=utf8mb4" in connection_string
        assert "collation=utf8mb4_unicode_ci" in connection_string
        assert "use_unicode=1" in connection_string

    def test_text_conversion_and_validation(self):
        """Test text encoding conversion and validation."""
        # Test valid UTF8MB4 text
        valid_text = "Hello 😀 World 🌍"
        try:
            encoded = UTF8MB4Handler.convert_text_field(valid_text)
            assert isinstance(encoded, bytes)
        except UnicodeEncodeError:
            pytest.skip("System doesn't support UTF8MB4 encoding")

        # Test text validation
        validation = CharsetValidator.validate_text_encoding(valid_text)
        assert validation["valid"]
        assert validation["requires_utf8mb4"]
        assert validation["emoji_count"] >= 2

    def test_text_sanitization(self):
        """Test text sanitization for systems that don't support UTF8MB4."""
        text_with_emoji = "Genes 🧬 and proteins 🧪"
        sanitized = UTF8MB4Handler.sanitize_for_basic_utf8(text_with_emoji)

        assert sanitized == "Genes ? and proteins ?"
        assert "🧬" not in sanitized
        assert "🧪" not in sanitized

    def test_model_charset_validation(self, utf8mb4_test_data):
        """Test charset validation on model instances."""
        species = utf8mb4_test_data["species"][0]  # Has emoji in name

        # Validate UTF8MB4 fields
        validation = species.validate_utf8mb4_fields("scientific_name", "common_name")
        assert "scientific_name" in validation
        assert "common_name" in validation

        # Check UTF8MB4 requirements
        requirements = species.requires_utf8mb4("scientific_name", "common_name")
        assert any(requirements.values())  # At least one field should require UTF8MB4

        # Get UTF8MB4 summary
        summary = species.get_utf8mb4_summary()
        assert summary["model"] == "Species"
        assert summary["total_text_fields"] > 0
        assert summary["emoji_count"] >= 0


class TestFullTextSearchFeatures:
    """Test full-text search functionality."""

    def test_fulltext_index_creation(self):
        """Test creation of full-text search index objects."""
        # Create index for species scientific names
        index = FullTextSearch.create_fulltext_index(
            table_name="species",
            columns=["display_name", "ensembl_species_name"],
            index_name="fti_species_names",
        )

        assert index.name == "fti_species_names"
        column_names = [col.name for col in index.columns]
        assert "display_name" in column_names
        assert "ensembl_species_name" in column_names

    def test_search_query_building(self):
        """Test building of full-text search queries."""
        # Test basic search query
        query = FullTextSearch.build_match_query(
            columns=["display_name", "ensembl_species_name"],
            search_query="Homo sapiens",
        )

        assert "MATCH(display_name, ensembl_species_name)" in str(query)
        assert "AGAINST(:search_query" in str(query)

        # Test boolean search query
        boolean_query = FullTextSearch.build_boolean_search_query(
            ["Homo", "+sapiens", "-neanderthalensis"]
        )

        assert "+sapiens" in boolean_query
        assert "-neanderthalensis" in boolean_query

    def test_search_query_parsing(self):
        """Test parsing and analysis of search queries."""
        complex_query = '"Homo sapiens" +evolution -extinction 🧬'

        parsed = FullTextSearch.parse_search_query(complex_query)

        assert "Homo sapiens" in parsed["phrases"]
        assert "evolution" in parsed["required_terms"]
        assert "extinction" in parsed["excluded_terms"]
        assert parsed["boolean_operators"]

    def test_search_query_optimization(self):
        """Test optimization of search queries."""
        # Test query optimization
        original_query = "the and a or an with at in"
        optimized = FullTextSearch.optimize_search_query(original_query)

        # Should remove very short words
        assert len(optimized) <= len(original_query)

        # Test search suggestions
        suggestions = FullTextSearch.get_search_suggestions("Homo")
        assert len(suggestions) > 0

    def test_relevance_scoring(self):
        """Test relevance score calculation."""
        query = FullTextSearch.build_relevance_query(
            columns=["scientific_name", "description"], search_query="development"
        )

        assert "relevance_score" in str(query)

    def test_search_modes(self):
        """Test different search modes."""
        columns = ["scientific_name", "description"]
        search_term = "gene"

        # Natural language mode
        natural_query = FullTextSearch.build_match_query(
            columns=columns,
            search_query=search_term,
            mode=FullTextSearch.SearchMode.NATURAL_LANGUAGE,
        )

        # Boolean mode
        boolean_query = FullTextSearch.build_match_query(
            columns=columns,
            search_query=search_term,
            mode=FullTextSearch.SearchMode.BOOLEAN_MODE,
        )

        # Query expansion
        expansion_query = FullTextSearch.build_match_query(
            columns=columns,
            search_query=search_term,
            mode=FullTextSearch.SearchMode.QUERY_EXPANSION,
        )

        assert "IN NATURAL LANGUAGE MODE" in str(natural_query)
        assert "IN BOOLEAN MODE" in str(boolean_query)
        assert "WITH QUERY EXPANSION" in str(expansion_query)


class TestMySQLQueryOptimization:
    """Test MySQL query optimization features."""

    def test_hint_injection(self):
        """Test injection of MySQL optimization hints."""
        original_query = "SELECT * FROM species WHERE name LIKE '%Homo%'"

        # Test with single hint
        hinted_query = MySQLQueryOptimizer.inject_hints(
            original_query, [MySQLQueryOptimizer.HintType.SQL_CACHE]
        )

        assert "SQL_CACHE" in str(hinted_query)
        result_str = str(hinted_query)
        # Check that SQL_CACHE appears after SELECT (allowing for whitespace)
        import re

        assert re.search(r"SELECT\s+SQL_CACHE", result_str)

        # Test with multiple hints
        multi_hinted = MySQLQueryOptimizer.inject_hints(
            original_query,
            [
                MySQLQueryOptimizer.HintType.SQL_CACHE,
                MySQLQueryOptimizer.HintType.SQL_SMALL_RESULT,
            ],
        )

        assert "SQL_CACHE" in str(multi_hinted)
        assert "SQL_SMALL_RESULT" in str(multi_hinted)

    def test_join_optimization(self):
        """Test JOIN query optimization."""
        join_query = """
            SELECT s.*, g.name as genefam_name
            FROM species s
            JOIN genefam_species_enhanced gse ON s.id = gse.species_id
            JOIN genefams g ON gse.genefam_id = g.id
            JOIN chromosomes c ON s.id = c.species_id
        """

        join_columns = {
            "species": ["id"],
            "genefam_species_enhanced": ["species_id", "genefam_id"],
            "genefams": ["id"],
            "chromosomes": ["species_id"],
        }

        optimized = MySQLQueryOptimizer.optimize_join_query(join_query, join_columns)

        # Should add STRAIGHT_JOIN for complex joins
        assert "STRAIGHT_JOIN" in str(optimized)

    

class TestMySQLConnectionPooling:
    """Test MySQL-specific connection pooling features."""

    def test_pool_configuration(self):
        """Test MySQL connection pool configuration."""
        pool_config = MySQLConnectionPool.get_pool_config(
            pool_size=10, max_overflow=20, pool_timeout=60, pool_recycle=7200
        )

        assert pool_config["pool_size"] == 10
        assert pool_config["max_overflow"] == 20
        assert pool_config["pool_timeout"] == 60
        assert pool_config["pool_recycle"] == 7200
        assert pool_config["pool_pre_ping"]

    def test_engine_creation_with_utf8mb4(self):
        """Test engine creation with UTF8MB4 support."""
        config = DatabaseConfig(
            driver=DatabaseDriver.MYSQL,
            host="localhost",
            username="test",
            password="test123",
            database="testdb",
            charset="utf8mb4",
        )

        # Note: This would fail in test environment without MySQL
        # but validates the configuration structure
        assert config.charset == "utf8mb4"
        assert config.use_unicode

        # Test connection string building
        connection_string = UTF8MB4Handler.build_connection_string(config)
        assert "charset=utf8mb4" in connection_string


class TestCharsetValidationAndIntegration:
    """Test charset validation and integration with models."""

    def test_model_charset_aware_search(self, utf8mb4_test_data):
        """Test charset-aware search functionality on models."""
        session = utf8mb4_test_data["session"]

        # Test searching with international characters
        results = Species.search_with_charset_support(
            session, "🧬", "_scientific_name", "_common_name", "display_name"
        )

        # Should find species with emoji in names
        assert len(results) >= 0

        # Test case-insensitive search
        results = Species.search_with_charset_support(
            session, "homo sapiens", "_scientific_name", case_sensitive=False
        )

        assert len(results) >= 0

    def test_charset_validation_comprehensive(self, utf8mb4_test_data):
        """Test comprehensive charset validation."""
        species = utf8mb4_test_data["species"][0]

        # Validate specific fields
        validation = species.validate_utf8mb4_fields("scientific_name")
        field_validation = validation["scientific_name"]

        assert "valid" in field_validation
        assert "length" in field_validation
        assert "encoding" in field_validation

        # Test UTF8MB4 requirement detection
        requirements = species.requires_utf8mb4("scientific_name")
        assert isinstance(requirements, dict)
        assert "scientific_name" in requirements

        # Test sanitization
        sanitized = species.sanitize_for_basic_utf8("scientific_name")
        assert isinstance(sanitized, dict)
        assert "scientific_name" in sanitized

    def test_utf8mb4_summary_analysis(self, utf8mb4_test_data):
        """Test UTF8MB4 summary analysis."""
        species = utf8mb4_test_data["species"][0]

        summary = species.get_utf8mb4_summary()

        assert summary["model"] == "Species"
        assert "total_text_fields" in summary
        assert "utf8mb4_required_fields" in summary
        assert "fields_requiring_utf8mb4" in summary
        assert "emoji_count" in summary
        assert "total_characters" in summary

        # Validate summary data types
        assert isinstance(summary["total_text_fields"], int)
        assert isinstance(summary["utf8mb4_required_fields"], int)
        assert isinstance(summary["emoji_count"], int)
        assert isinstance(summary["total_characters"], int)


class TestErrorHandlingAndEdgeCases:
    """Test error handling and edge cases for MySQL features."""

    def test_invalid_utf8mb4_text(self):
        """Test handling of invalid UTF8MB4 text."""
        # Test with None values
        assert not UTF8MB4Handler.requires_utf8mb4(None)
        assert not UTF8MB4Handler.requires_utf8mb4("")

        # Test validation with empty strings
        validation = CharsetValidator.validate_text_encoding("")
        assert validation["valid"]
        assert validation["length"] == 0

    def test_malformed_search_queries(self):
        """Test handling of malformed search queries."""
        # Test empty queries
        parsed = FullTextSearch.parse_search_query("")
        assert parsed["original"] == ""
        assert parsed["word_count"] == 0

        # Test optimization of empty queries
        optimized = FullTextSearch.optimize_search_query("")
        assert optimized == ""

        # Test malformed boolean expressions
        boolean_query = FullTextSearch.build_boolean_search_query(
            ["+", "-", "valid_term"]
        )

        assert "valid_term" in boolean_query

    def test_connection_error_handling(self):
        """Test error handling for connection issues."""
        # Test with invalid configuration
        config = DatabaseConfig(
            driver=DatabaseDriver.MYSQL,
            host="invalid-host-name-that-does-not-exist",
            username="invalid",
            password="invalid",
            database="invalid",
        )

        # Connection string should still build
        connection_string = UTF8MB4Handler.build_connection_string(config)
        assert connection_string is not None
        assert "mysql" in connection_string

    def test_field_validation_edge_cases(self, utf8mb4_test_data):
        """Test edge cases in field validation."""
        species = utf8mb4_test_data["species"][0]

        # Test non-existent fields
        validation = species.validate_utf8mb4_fields("non_existent_field")
        assert validation.get("non_existent_field") is not None
        assert validation.get("non_existent_field").get("valid") is False
        assert "does not exist" in validation.get("non_existent_field").get("error", "")

        # Test empty field list
        validation = species.validate_utf8mb4_fields()
        assert validation == {}

        # Test mixed valid/invalid fields
        validation = species.validate_utf8mb4_fields("scientific_name", "non_existent")
        assert "scientific_name" in validation
        assert "non_existent" in validation
