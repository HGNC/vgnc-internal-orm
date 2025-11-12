"""Comprehensive database-integrated tests for Supporting models functionality."""

import pytest
from datetime import datetime, timezone
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from src.vgnc_internal_orm.models.supporting import (
    GeneStatus,
    Editor,
    AltName,
    AltSymbol,
    NomenclatureType,
    Comment,
    GeneFlag,
    FlagClass,
    FamilyNew
)
from src.vgnc_internal_orm.sessions.factory import DatabaseFactory
from src.vgnc_internal_orm.config.settings import DatabaseConfig, DatabaseDriver


class TestGeneStatusComprehensive:
    """Comprehensive tests for GeneStatus model."""

    def setup_method(self):
        """Set up test database and session."""
        self.config = DatabaseConfig(
            driver=DatabaseDriver.SQLITE,
            database=":memory:",
            _env_file=None
        )
        self.factory = DatabaseFactory(self.config)
        self.engine = self.factory.create_engine()
        self.SessionLocal = sessionmaker(bind=self.engine)

        # Create tables for all models
        from src.vgnc_internal_orm.models.base import BaseModel
        BaseModel.metadata.create_all(bind=self.engine)
        self.session = self.SessionLocal()

    def teardown_method(self):
        """Clean up test database."""
        self.session.close()
        self.engine.dispose()

    def test_gene_status_crud_operations(self):
        """Test complete CRUD operations for GeneStatus."""
        # Create
        status = GeneStatus(
            status="approved",
            display="Approved Status"
        )

        self.session.add(status)
        self.session.commit()

        # Verify creation
        assert status.id is not None
        assert status.status == "approved"
        assert status.display == "Approved Status"

        # Read
        retrieved = self.session.query(GeneStatus).filter_by(status="approved").first()
        assert retrieved is not None
        assert retrieved.display == "Approved Status"

        # Update
        retrieved.display = "Fully Approved"
        self.session.commit()

        # Verify update
        updated = self.session.query(GeneStatus).filter_by(status="approved").first()
        assert updated.display == "Fully Approved"

        # Delete
        self.session.delete(updated)
        self.session.commit()

        # Verify deletion
        deleted = self.session.query(GeneStatus).filter_by(status="approved").first()
        assert deleted is None

    def test_gene_status_all_status_types(self):
        """Test GeneStatus with various status types."""
        status_types = [
            ("approved", "Approved Gene Family"),
            ("pending", "Pending Review"),
            ("rejected", "Rejected Submission"),
            ("draft", "Draft Status"),
            ("deprecated", "Deprecated Status"),
            ("experimental", "Experimental Evidence"),
        ]

        for status_name, display_name in status_types:
            status = GeneStatus(status=status_name, display=display_name)
            self.session.add(status)

        self.session.commit()

        # Verify all status types were saved
        for status_name, display_name in status_types:
            retrieved = self.session.query(GeneStatus).filter_by(status=status_name).first()
            assert retrieved is not None
            assert retrieved.display == display_name

    def test_gene_status_edge_cases(self):
        """Test GeneStatus edge cases."""
        # Test with None display name
        status_no_display = GeneStatus(status="no_display")
        self.session.add(status_no_display)
        self.session.commit()
        assert status_no_display.display is None

        # Test with empty string display name
        status_empty_display = GeneStatus(status="empty_display", display="")
        self.session.add(status_empty_display)
        self.session.commit()
        assert status_empty_display.display == ""

        # Test with maximum length status
        max_status = GeneStatus(
            status="x" * 45,  # Maximum length
            display="y" * 128  # Maximum length
        )
        self.session.add(max_status)
        self.session.commit()
        assert len(max_status.status) == 45
        assert len(max_status.display) == 128

    def test_gene_status_repr_method(self):
        """Test GeneStatus __repr__ method."""
        status = GeneStatus(status="test_repr", display="Test Repr")
        repr_str = repr(status)
        assert "GeneStatus" in repr_str
        assert "status='test_repr'" in repr_str

    def test_gene_status_field_utilities(self):
        """Test BaseModel field utilities with GeneStatus."""
        status = GeneStatus(status="utilities_test", display="Utilities Test")

        # Test get_field_value
        assert status.get_field_value("status") == "utilities_test"
        assert status.get_field_value("display") == "Utilities Test"
        assert status.get_field_value("nonexistent") is None

        # Test set_field_value
        status.set_field_value("display", "Updated Display")
        assert status.display == "Updated Display"

        # Test has_field
        assert status.has_field("id") is True
        assert status.has_field("status") is True
        assert status.has_field("display") is True
        assert status.has_field("nonexistent") is False

        # Test get_field_type
        assert status.get_field_type("id") == int
        assert status.get_field_type("status") == str
        assert status.get_field_type("display") == str


class TestEditorComprehensive:
    """Comprehensive tests for Editor model."""

    def setup_method(self):
        """Set up test database and session."""
        self.config = DatabaseConfig(
            driver=DatabaseDriver.SQLITE,
            database=":memory:",
            _env_file=None
        )
        self.factory = DatabaseFactory(self.config)
        self.engine = self.factory.create_engine()
        self.SessionLocal = sessionmaker(bind=self.engine)

        # Create tables for all models
        from src.vgnc_internal_orm.models.base import BaseModel
        BaseModel.metadata.create_all(bind=self.engine)
        self.session = self.SessionLocal()

    def teardown_method(self):
        """Clean up test database."""
        self.session.close()
        self.engine.dispose()

    def test_editor_crud_operations(self):
        """Test complete CRUD operations for Editor."""
        # Create
        editor = Editor(
            display_name="Dr. John Smith",
            first_name="John",
            last_name="Smith",
            email="john.smith@example.com",
            current=True,
            connected=True
        )

        self.session.add(editor)
        self.session.commit()

        # Verify creation
        assert editor.id is not None
        assert editor.display_name == "Dr. John Smith"
        assert editor.first_name == "John"
        assert editor.last_name == "Smith"
        assert editor.email == "john.smith@example.com"
        assert editor.current is True
        assert editor.connected is True

        # Read
        retrieved = self.session.query(Editor).filter_by(display_name="Dr. John Smith").first()
        assert retrieved is not None
        assert retrieved.email == "john.smith@example.com"

        # Update
        retrieved.connected = False
        retrieved.email = "john.smith@newdomain.com"
        self.session.commit()

        # Verify update
        updated = self.session.query(Editor).filter_by(display_name="Dr. John Smith").first()
        assert updated.connected is False
        assert updated.email == "john.smith@newdomain.com"

        # Delete
        self.session.delete(updated)
        self.session.commit()

        # Verify deletion
        deleted = self.session.query(Editor).filter_by(display_name="Dr. John Smith").first()
        assert deleted is None

    def test_editor_all_boolean_combinations(self):
        """Test Editor with all boolean field combinations."""
        boolean_combinations = [
            (True, True),   # current, connected
            (True, False),  # current, not connected
            (False, True),  # not current, connected
            (False, False), # not current, not connected
        ]

        for current, connected in boolean_combinations:
            editor = Editor(
                display_name=f"Editor {current}_{connected}",
                current=current,
                connected=connected
            )
            self.session.add(editor)

        self.session.commit()

        # Verify all combinations were saved
        for current, connected in boolean_combinations:
            retrieved = self.session.query(Editor).filter_by(
                display_name=f"Editor {current}_{connected}"
            ).first()
            assert retrieved is not None
            assert retrieved.current == current
            assert retrieved.connected == connected

    def test_editor_edge_cases(self):
        """Test Editor edge cases."""
        # Test with minimal required fields
        minimal_editor = Editor(display_name="Minimal Editor")
        self.session.add(minimal_editor)
        self.session.commit()
        assert minimal_editor.first_name is None
        assert minimal_editor.last_name is None
        assert minimal_editor.email is None
        assert minimal_editor.password is None

        # Test with all fields populated
        full_editor = Editor(
            display_name="Full Editor",
            first_name="Jane",
            last_name="Doe",
            email="jane.doe@example.com",
            password="hashed_password_123",
            current=False,
            connected=False
        )
        self.session.add(full_editor)
        self.session.commit()
        assert full_editor.password == "hashed_password_123"

        # Test with maximum length strings
        max_editor = Editor(
            display_name="x" * 128,  # max length
            first_name="y" * 128,   # max length
            last_name="z" * 128,    # max length
            email="a" * 124 + "@example.com",  # near max email length
            password="p" * 255      # max length
        )
        self.session.add(max_editor)
        self.session.commit()
        assert len(max_editor.display_name) == 128

    def test_editor_repr_method(self):
        """Test Editor __repr__ method."""
        editor = Editor(display_name="Test Editor")
        repr_str = repr(editor)
        assert "Editor" in repr_str
        assert "display_name='Test Editor'" in repr_str

    def test_editor_query_operations(self):
        """Test Editor query operations."""
        # Create test editors
        editors = [
            Editor(display_name="Current Editor", current=True, connected=True),
            Editor(display_name="Former Editor", current=False, connected=False),
            Editor(display_name="Disconnected Editor", current=True, connected=False),
        ]

        for editor in editors:
            self.session.add(editor)
        self.session.commit()

        # Test query by boolean fields
        current_editors = self.session.query(Editor).filter_by(current=True).all()
        assert len(current_editors) == 2

        connected_editors = self.session.query(Editor).filter_by(connected=True).all()
        assert len(connected_editors) == 1

        # Test complex query
        active_editors = self.session.query(Editor).filter(
            Editor.current == True,
            Editor.connected == True
        ).all()
        assert len(active_editors) == 1
        assert active_editors[0].display_name == "Current Editor"


class TestNomenclatureTypeComprehensive:
    """Comprehensive tests for NomenclatureType model."""

    def setup_method(self):
        """Set up test database and session."""
        self.config = DatabaseConfig(
            driver=DatabaseDriver.SQLITE,
            database=":memory:",
            _env_file=None
        )
        self.factory = DatabaseFactory(self.config)
        self.engine = self.factory.create_engine()
        self.SessionLocal = sessionmaker(bind=self.engine)

        # Create tables for all models
        from src.vgnc_internal_orm.models.base import BaseModel
        BaseModel.metadata.create_all(bind=self.engine)
        self.session = self.SessionLocal()

    def teardown_method(self):
        """Clean up test database."""
        self.session.close()
        self.engine.dispose()

    def test_nomenclature_type_crud_operations(self):
        """Test complete CRUD operations for NomenclatureType."""
        # Create
        nom_type = NomenclatureType(type="HGNC-approved")
        self.session.add(nom_type)
        self.session.commit()

        # Verify creation
        assert nom_type.id is not None
        assert nom_type.type == "HGNC-approved"

        # Read
        retrieved = self.session.query(NomenclatureType).filter_by(type="HGNC-approved").first()
        assert retrieved is not None
        assert retrieved.type == "HGNC-approved"

        # Update
        retrieved.type = "HGNC-updated"
        self.session.commit()

        # Verify update
        updated = self.session.query(NomenclatureType).filter_by(id=retrieved.id).first()
        assert updated.type == "HGNC-updated"

        # Delete
        self.session.delete(updated)
        self.session.commit()

        # Verify deletion
        deleted = self.session.query(NomenclatureType).filter_by(type="HGNC-updated").first()
        assert deleted is None

    def test_nomenclature_type_all_types(self):
        """Test NomenclatureType with various types."""
        nomenclature_types = [
            "HGNC-approved",
            "Unofficial",
            "Obsolete",
            "Alias",
            "Synonym",
            "Previous symbol",
            "Ortholog symbol"
        ]

        for nom_type in nomenclature_types:
            nomenclature = NomenclatureType(type=nom_type)
            self.session.add(nomenclature)

        self.session.commit()

        # Verify all types were saved
        for nom_type in nomenclature_types:
            retrieved = self.session.query(NomenclatureType).filter_by(type=nom_type).first()
            assert retrieved is not None
            assert retrieved.type == nom_type

    def test_nomenclature_type_edge_cases(self):
        """Test NomenclatureType edge cases."""
        # Test with maximum length type
        max_type = NomenclatureType(type="x" * 255)  # Maximum length
        self.session.add(max_type)
        self.session.commit()
        assert len(max_type.type) == 255

        # Test with special characters
        special_type = NomenclatureType(type="Special-Type_123#$%")
        self.session.add(special_type)
        self.session.commit()
        assert special_type.type == "Special-Type_123#$%"

    def test_nomenclature_type_repr_method(self):
        """Test NomenclatureType __repr__ method."""
        nom_type = NomenclatureType(type="test_type")
        repr_str = repr(nom_type)
        assert "NomenclatureType" in repr_str
        assert "type='test_type'" in repr_str


class TestAltNameComprehensive:
    """Comprehensive tests for AltName model."""

    def setup_method(self):
        """Set up test database and session."""
        self.config = DatabaseConfig(
            driver=DatabaseDriver.SQLITE,
            database=":memory:",
            _env_file=None
        )
        self.factory = DatabaseFactory(self.config)
        self.engine = self.factory.create_engine()
        self.SessionLocal = sessionmaker(bind=self.engine)

        # Create tables for all models
        from src.vgnc_internal_orm.models.base import BaseModel
        BaseModel.metadata.create_all(bind=self.engine)
        self.session = self.SessionLocal()

        # Create nomenclature type
        self.nom_type = NomenclatureType(type="HGNC-approved")
        self.session.add(self.nom_type)
        self.session.commit()

    def teardown_method(self):
        """Clean up test database."""
        self.session.close()
        self.engine.dispose()

    def test_alt_name_crud_operations(self):
        """Test complete CRUD operations for AltName."""
        # Create
        alt_name = AltName(
            name="Alternative Gene Name",
            nomenclature_type_id=self.nom_type.id
        )

        self.session.add(alt_name)
        self.session.commit()

        # Verify creation
        assert alt_name.id is not None
        assert alt_name.name == "Alternative Gene Name"
        assert alt_name.nomenclature_type_id == self.nom_type.id

        # Read
        retrieved = self.session.query(AltName).filter_by(name="Alternative Gene Name").first()
        assert retrieved is not None
        assert retrieved.nomenclature_type_id == self.nom_type.id

        # Update
        retrieved.name = "Updated Alternative Name"
        self.session.commit()

        # Verify update
        updated = self.session.query(AltName).filter_by(id=retrieved.id).first()
        assert updated.name == "Updated Alternative Name"

        # Delete
        self.session.delete(updated)
        self.session.commit()

        # Verify deletion
        deleted = self.session.query(AltName).filter_by(name="Updated Alternative Name").first()
        assert deleted is None

    def test_alt_name_relationship_with_nomenclature_type(self):
        """Test AltName relationship with NomenclatureType."""
        alt_name = AltName(
            name="Test Alt Name",
            nomenclature_type_id=self.nom_type.id
        )

        self.session.add(alt_name)
        self.session.commit()

        # Test relationship access
        assert alt_name.nomenclature_type is not None
        assert alt_name.nomenclature_type.type == "HGNC-approved"

        # Test reverse relationship
        self.session.refresh(self.nom_type)
        assert len(self.nom_type.alt_names) == 1
        assert self.nom_type.alt_names[0].name == "Test Alt Name"

    def test_alt_name_edge_cases(self):
        """Test AltName edge cases."""
        # Test with maximum length name
        max_name = AltName(
            name="x" * 255,  # Maximum length
            nomenclature_type_id=self.nom_type.id
        )
        self.session.add(max_name)
        self.session.commit()
        assert len(max_name.name) == 255

        # Test with special characters
        special_name = AltName(
            name="Special-Name_123 with spaces & symbols!",
            nomenclature_type_id=self.nom_type.id
        )
        self.session.add(special_name)
        self.session.commit()
        assert "& symbols!" in special_name.name

    def test_alt_name_repr_method(self):
        """Test AltName __repr__ method."""
        alt_name = AltName(name="Test Name", nomenclature_type_id=self.nom_type.id)
        repr_str = repr(alt_name)
        assert "AltName" in repr_str
        assert "name='Test Name'" in repr_str


class TestAltSymbolComprehensive:
    """Comprehensive tests for AltSymbol model."""

    def setup_method(self):
        """Set up test database and session."""
        self.config = DatabaseConfig(
            driver=DatabaseDriver.SQLITE,
            database=":memory:",
            _env_file=None
        )
        self.factory = DatabaseFactory(self.config)
        self.engine = self.factory.create_engine()
        self.SessionLocal = sessionmaker(bind=self.engine)

        # Create tables for all models
        from src.vgnc_internal_orm.models.base import BaseModel
        BaseModel.metadata.create_all(bind=self.engine)
        self.session = self.SessionLocal()

        # Create nomenclature type
        self.nom_type = NomenclatureType(type="Symbol")
        self.session.add(self.nom_type)
        self.session.commit()

    def teardown_method(self):
        """Clean up test database."""
        self.session.close()
        self.engine.dispose()

    def test_alt_symbol_crud_operations(self):
        """Test complete CRUD operations for AltSymbol."""
        # Create
        alt_symbol = AltSymbol(
            symbol="ALTERNATE1",
            nomenclature_type_id=self.nom_type.id
        )

        self.session.add(alt_symbol)
        self.session.commit()

        # Verify creation
        assert alt_symbol.id is not None
        assert alt_symbol.symbol == "ALTERNATE1"
        assert alt_symbol.nomenclature_type_id == self.nom_type.id

        # Read
        retrieved = self.session.query(AltSymbol).filter_by(symbol="ALTERNATE1").first()
        assert retrieved is not None
        assert retrieved.nomenclature_type_id == self.nom_type.id

        # Update
        retrieved.symbol = "ALTERNATE2"
        self.session.commit()

        # Verify update
        updated = self.session.query(AltSymbol).filter_by(id=retrieved.id).first()
        assert updated.symbol == "ALTERNATE2"

        # Delete
        self.session.delete(updated)
        self.session.commit()

        # Verify deletion
        deleted = self.session.query(AltSymbol).filter_by(symbol="ALTERNATE2").first()
        assert deleted is None

    def test_alt_symbol_relationship_with_nomenclature_type(self):
        """Test AltSymbol relationship with NomenclatureType."""
        alt_symbol = AltSymbol(
            symbol="TESTSYM",
            nomenclature_type_id=self.nom_type.id
        )

        self.session.add(alt_symbol)
        self.session.commit()

        # Test relationship access
        assert alt_symbol.nomenclature_type is not None
        assert alt_symbol.nomenclature_type.type == "Symbol"

        # Test reverse relationship
        self.session.refresh(self.nom_type)
        assert len(self.nom_type.alt_symbols) == 1
        assert self.nom_type.alt_symbols[0].symbol == "TESTSYM"

    def test_alt_symbol_edge_cases(self):
        """Test AltSymbol edge cases."""
        # Test with maximum length symbol
        max_symbol = AltSymbol(
            symbol="x" * 45,  # Maximum length
            nomenclature_type_id=self.nom_type.id
        )
        self.session.add(max_symbol)
        self.session.commit()
        assert len(max_symbol.symbol) == 45

        # Test with gene family naming patterns
        symbol_patterns = [
            "GENE1",
            "GENEFAM1",
            "HGNC:12345",
            "ENTREZ:6789",
            "uniprot_id"
        ]

        for pattern in symbol_patterns:
            alt_symbol = AltSymbol(symbol=pattern, nomenclature_type_id=self.nom_type.id)
            self.session.add(alt_symbol)

        self.session.commit()

        # Verify all patterns were saved
        for pattern in symbol_patterns:
            retrieved = self.session.query(AltSymbol).filter_by(symbol=pattern).first()
            assert retrieved is not None
            assert retrieved.symbol == pattern

    def test_alt_symbol_repr_method(self):
        """Test AltSymbol __repr__ method."""
        alt_symbol = AltSymbol(symbol="TESTSYMBOL", nomenclature_type_id=self.nom_type.id)
        repr_str = repr(alt_symbol)
        assert "AltSymbol" in repr_str
        assert "symbol='TESTSYMBOL'" in repr_str


class TestFlagClassComprehensive:
    """Comprehensive tests for FlagClass model."""

    def setup_method(self):
        """Set up test database and session."""
        self.config = DatabaseConfig(
            driver=DatabaseDriver.SQLITE,
            database=":memory:",
            _env_file=None
        )
        self.factory = DatabaseFactory(self.config)
        self.engine = self.factory.create_engine()
        self.SessionLocal = sessionmaker(bind=self.engine)

        # Create tables for all models
        from src.vgnc_internal_orm.models.base import BaseModel
        BaseModel.metadata.create_all(bind=self.engine)
        self.session = self.SessionLocal()

    def teardown_method(self):
        """Clean up test database."""
        self.session.close()
        self.engine.dispose()

    def test_flag_class_crud_operations(self):
        """Test complete CRUD operations for FlagClass."""
        # Create
        flag_class = FlagClass(class_name="Quality Flag")
        self.session.add(flag_class)
        self.session.commit()

        # Verify creation
        assert flag_class.id is not None
        assert flag_class.class_name == "Quality Flag"

        # Read
        retrieved = self.session.query(FlagClass).filter_by(class_name="Quality Flag").first()
        assert retrieved is not None
        assert retrieved.class_name == "Quality Flag"

        # Update
        retrieved.class_name = "Updated Quality Flag"
        self.session.commit()

        # Verify update
        updated = self.session.query(FlagClass).filter_by(id=retrieved.id).first()
        assert updated.class_name == "Updated Quality Flag"

        # Delete
        self.session.delete(updated)
        self.session.commit()

        # Verify deletion
        deleted = self.session.query(FlagClass).filter_by(class_name="Updated Quality Flag").first()
        assert deleted is None

    def test_flag_class_all_classes(self):
        """Test FlagClass with various class names."""
        flag_classes = [
            "Quality Flag",
            "Status Flag",
            "Warning Flag",
            "Deprecated Flag",
            "Experimental Flag",
            "Review Required"
        ]

        for class_name in flag_classes:
            flag_class = FlagClass(class_name=class_name)
            self.session.add(flag_class)

        self.session.commit()

        # Verify all class names were saved
        for class_name in flag_classes:
            retrieved = self.session.query(FlagClass).filter_by(class_name=class_name).first()
            assert retrieved is not None
            assert retrieved.class_name == class_name

    def test_flag_class_edge_cases(self):
        """Test FlagClass edge cases."""
        # Test with maximum length class name
        max_class = FlagClass(class_name="x" * 255)  # Maximum length
        self.session.add(max_class)
        self.session.commit()
        assert len(max_class.class_name) == 255

        # Test with special characters
        special_class = FlagClass(class_name="Special-Class_123#$%")
        self.session.add(special_class)
        self.session.commit()
        assert special_class.class_name == "Special-Class_123#$%"

    def test_flag_class_repr_method(self):
        """Test FlagClass __repr__ method."""
        flag_class = FlagClass(class_name="Test Class")
        repr_str = repr(flag_class)
        assert "FlagClass" in repr_str
        assert "class_name='Test Class'" in repr_str


class TestGeneFlagComprehensive:
    """Comprehensive tests for GeneFlag model."""

    def setup_method(self):
        """Set up test database and session."""
        self.config = DatabaseConfig(
            driver=DatabaseDriver.SQLITE,
            database=":memory:",
            _env_file=None
        )
        self.factory = DatabaseFactory(self.config)
        self.engine = self.factory.create_engine()
        self.SessionLocal = sessionmaker(bind=self.engine)

        # Create tables for all models
        from src.vgnc_internal_orm.models.base import BaseModel
        BaseModel.metadata.create_all(bind=self.engine)
        self.session = self.SessionLocal()

        # Create flag class
        self.flag_class = FlagClass(class_name="Test Flag Class")
        self.session.add(self.flag_class)
        self.session.commit()

    def teardown_method(self):
        """Clean up test database."""
        self.session.close()
        self.engine.dispose()

    def test_gene_flag_crud_operations(self):
        """Test complete CRUD operations for GeneFlag."""
        # Create
        gene_flag = GeneFlag(
            type="Quality Issue",
            flag_class_id=self.flag_class.id
        )

        self.session.add(gene_flag)
        self.session.commit()

        # Verify creation
        assert gene_flag.id is not None
        assert gene_flag.type == "Quality Issue"
        assert gene_flag.flag_class_id == self.flag_class.id

        # Read
        retrieved = self.session.query(GeneFlag).filter_by(type="Quality Issue").first()
        assert retrieved is not None
        assert retrieved.flag_class_id == self.flag_class.id

        # Update
        retrieved.type = "Updated Quality Issue"
        self.session.commit()

        # Verify update
        updated = self.session.query(GeneFlag).filter_by(id=retrieved.id).first()
        assert updated.type == "Updated Quality Issue"

        # Delete
        self.session.delete(updated)
        self.session.commit()

        # Verify deletion
        deleted = self.session.query(GeneFlag).filter_by(type="Updated Quality Issue").first()
        assert deleted is None

    def test_gene_flag_relationship_with_flag_class(self):
        """Test GeneFlag relationship with FlagClass."""
        gene_flag = GeneFlag(
            type="Test Flag",
            flag_class_id=self.flag_class.id
        )

        self.session.add(gene_flag)
        self.session.commit()

        # Test relationship access
        assert gene_flag.flag_class is not None
        assert gene_flag.flag_class.class_name == "Test Flag Class"

        # Test reverse relationship
        self.session.refresh(self.flag_class)
        assert len(self.flag_class.flags) == 1
        assert self.flag_class.flags[0].type == "Test Flag"

    def test_gene_flag_edge_cases(self):
        """Test GeneFlag edge cases."""
        # Test with maximum length type
        max_type = GeneFlag(
            type="x" * 255,  # Maximum length
            flag_class_id=self.flag_class.id
        )
        self.session.add(max_type)
        self.session.commit()
        assert len(max_type.type) == 255

        # Test with special characters
        special_type = GeneFlag(
            type="Special-Type_123#$%",
            flag_class_id=self.flag_class.id
        )
        self.session.add(special_type)
        self.session.commit()
        assert special_type.type == "Special-Type_123#$%"

    def test_gene_flag_repr_method(self):
        """Test GeneFlag __repr__ method."""
        gene_flag = GeneFlag(type="Test Flag", flag_class_id=self.flag_class.id)
        repr_str = repr(gene_flag)
        assert "GeneFlag" in repr_str
        assert "type='Test Flag'" in repr_str


class TestFamilyNewComprehensive:
    """Comprehensive tests for FamilyNew model."""

    def setup_method(self):
        """Set up test database and session."""
        self.config = DatabaseConfig(
            driver=DatabaseDriver.SQLITE,
            database=":memory:",
            _env_file=None
        )
        self.factory = DatabaseFactory(self.config)
        self.engine = self.factory.create_engine()
        self.SessionLocal = sessionmaker(bind=self.engine)

        # Create tables for all models
        from src.vgnc_internal_orm.models.base import BaseModel
        BaseModel.metadata.create_all(bind=self.engine)
        self.session = self.SessionLocal()

        # Create editor
        self.editor = Editor(
            display_name="Test Editor",
            current=True,
            connected=True
        )
        self.session.add(self.editor)
        self.session.commit()

    def teardown_method(self):
        """Clean up test database."""
        self.session.close()
        self.engine.dispose()

    def test_family_new_crud_operations(self):
        """Test complete CRUD operations for FamilyNew."""
        # Create
        family = FamilyNew(
            abbreviation="TESTFAM",
            name="Test Gene Family",
            curator_comment="Test comment",
            status="active",
            external_note="External note",
            type="protein_coding",
            desc_comment="Description comment",
            desc_label="Description label",
            desc_source="Description source",
            desc_go="GO:0003674",
            typical_gene="GENE1",
            editor_id=self.editor.id
        )

        self.session.add(family)
        self.session.commit()

        # Verify creation
        assert family.id is not None
        assert family.abbreviation == "TESTFAM"
        assert family.name == "Test Gene Family"
        assert family.curator_comment == "Test comment"
        assert family.status == "active"
        assert family.external_note == "External note"
        assert family.type == "protein_coding"
        assert family.desc_comment == "Description comment"
        assert family.desc_label == "Description label"
        assert family.desc_source == "Description source"
        assert family.desc_go == "GO:0003674"
        assert family.typical_gene == "GENE1"
        assert family.editor_id == self.editor.id

        # Read
        retrieved = self.session.query(FamilyNew).filter_by(name="Test Gene Family").first()
        assert retrieved is not None
        assert retrieved.abbreviation == "TESTFAM"

        # Update
        retrieved.status = "inactive"
        retrieved.curator_comment = "Updated comment"
        self.session.commit()

        # Verify update
        updated = self.session.query(FamilyNew).filter_by(name="Test Gene Family").first()
        assert updated.status == "inactive"
        assert updated.curator_comment == "Updated comment"

        # Delete
        self.session.delete(updated)
        self.session.commit()

        # Verify deletion
        deleted = self.session.query(FamilyNew).filter_by(name="Test Gene Family").first()
        assert deleted is None

    def test_family_new_all_fields(self):
        """Test FamilyNew with all field combinations."""
        families = [
            # Minimal required fields
            {
                "name": "Minimal Family",
                "editor_id": self.editor.id
            },
            # All fields populated
            {
                "abbreviation": "FULLFAM",
                "name": "Full Family",
                "curator_comment": "Comprehensive comment",
                "status": "active",
                "external_note": "External documentation",
                "type": "protein_coding",
                "desc_comment": "Detailed description",
                "desc_label": "Functional Description",
                "desc_source": "UniProt",
                "desc_go": "GO:0005524",
                "typical_gene": "TP53",
                "editor_id": self.editor.id
            },
            # Empty strings for default fields
            {
                "abbreviation": "",
                "name": "Empty Fields Family",
                "status": "",
                "type": "",
                "desc_go": "",
                "editor_id": self.editor.id
            }
        ]

        for family_data in families:
            family = FamilyNew(**family_data)
            self.session.add(family)

        self.session.commit()

        # Verify all families were saved
        for family_data in families:
            retrieved = self.session.query(FamilyNew).filter_by(name=family_data["name"]).first()
            assert retrieved is not None

    def test_family_new_edge_cases(self):
        """Test FamilyNew edge cases."""
        # Test with maximum length strings
        max_family = FamilyNew(
            abbreviation="x" * 255,  # max length
            name="y" * 255,       # max length
            curator_comment="z" * 1000,  # Text field - can be long
            external_note="w" * 1000,
            type="v" * 50,       # max length
            desc_comment="u" * 1000,
            desc_label="t" * 255,  # max length
            desc_source="s" * 255,  # max length
            desc_go="r" * 255,    # max length
            typical_gene="q" * 50, # max length
            editor_id=self.editor.id
        )
        self.session.add(max_family)
        self.session.commit()
        assert len(max_family.name) == 255

    def test_family_new_relationship_with_editor(self):
        """Test FamilyNew relationship with Editor."""
        family = FamilyNew(
            name="Test Relationship Family",
            editor_id=self.editor.id
        )

        self.session.add(family)
        self.session.commit()

        # Test relationship access (if relationship is properly defined)
        # Note: This depends on how the relationship is set up in the actual model
        assert family.editor_id == self.editor.id

    def test_family_new_repr_method(self):
        """Test FamilyNew __repr__ method."""
        family = FamilyNew(name="Test Family", editor_id=self.editor.id)
        repr_str = repr(family)
        assert "FamilyNew" in repr_str
        assert "name='Test Family'" in repr_str