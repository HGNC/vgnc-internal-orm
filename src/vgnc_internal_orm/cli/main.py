"""Command-line interface for VGNC ORM.

This module provides CLI commands for querying genes, families,
and related data with proper parameter handling and output formatting.
"""

import csv
import io
import json
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

import click
import defusedxml.ElementTree as ET
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import Session, sessionmaker

from vgnc_internal_orm.config.settings import DatabaseConfig
from vgnc_internal_orm.models.assembly import Assembly
from vgnc_internal_orm.models.chromosomes import Chromosomes
from vgnc_internal_orm.models.genefam import Genefam
from vgnc_internal_orm.models.species import Species

if TYPE_CHECKING:
    pass


@click.group()
@click.option(
    "--database-url", "-d", help="Database connection URL (overrides config file)"
)
@click.option(
    "--config", "-c", type=click.Path(exists=True), help="Path to configuration file"
)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.pass_context
def cli(
    ctx: click.Context,
    database_url: str | None,
    config: str | None,
    verbose: bool,
) -> None:
    """VGNC ORM Command-line Interface.

    A powerful CLI for querying gene families, species, and orthology data
    from the VGNC database with support for multiple output formats.
    """
    # Add src to path for imports when running as script
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root / "src"))

    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["database_url"] = database_url
    ctx.obj["config_file"] = config

    # Defer configuration loading until we actually need it
    # This prevents configuration errors when just displaying help
    ctx.obj["db_config"] = None
    ctx.obj["config_loaded"] = False


def ensure_config_loaded(ctx: click.Context) -> None:
    """Load configuration if not already loaded."""
    if ctx.obj.get("config_loaded", False):
        return

    try:
        if ctx.obj.get("config_file"):
            os.environ["VGNC_CONFIG_FILE"] = ctx.obj["config_file"]

        # Set minimal database config if database URL is provided directly
        if ctx.obj.get("database_url"):
            # Create minimal config when database URL is provided
            os.environ["DB_DATABASE"] = "cli_database"  # Minimal required field
            os.environ["DB_DRIVER"] = (
                "sqlite"  # Set SQLite driver to avoid auth requirements
            )
            db_config = DatabaseConfig(database="cli_database")
            # Override the database_url property by storing it separately
            ctx.obj["database_url"] = ctx.obj["database_url"]
        else:
            db_config = DatabaseConfig(database="cli_database")
            ctx.obj["database_url"] = None

        ctx.obj["db_config"] = db_config
        ctx.obj["config_loaded"] = True

    except Exception as e:
        # Fallback to minimal config if configuration loading fails
        if ctx.obj.get("database_url"):
            try:
                os.environ["DB_DATABASE"] = "cli_database"
                os.environ["DB_DRIVER"] = (
                    "sqlite"  # Set SQLite driver to avoid auth requirements
                )
                db_config = DatabaseConfig(database="cli_database")
                ctx.obj["database_url"] = ctx.obj["database_url"]
                ctx.obj["db_config"] = db_config
                ctx.obj["config_loaded"] = True
                if ctx.obj.get("verbose"):
                    click.echo(
                        "Using database URL with minimal configuration", err=True
                    )
            except Exception as fallback_error:
                click.echo(
                    f"Error setting up minimal configuration: {fallback_error}",
                    err=True,
                )
                ctx.exit(1)
        else:
            click.echo(f"Error loading configuration: {e}", err=True)
            click.echo(
                "Please provide --database-url or ensure proper configuration", err=True
            )
            ctx.exit(1)


# Export utility functions
def format_species_as_xml(species_list: list[Species]) -> str:
    """Format species data as XML with proper UTF8MB4 encoding support."""
    root = ET.Element("species")

    for species in species_list:
        species_elem = ET.SubElement(root, "species")
        species_elem.set("taxon_id", str(species.taxon_id))

        # Add elements with proper text content
        elem = ET.SubElement(species_elem, "genefam_prefix")
        elem.text = species.genefam_prefix or ""

        elem = ET.SubElement(species_elem, "display_name")
        elem.text = species.display_name or ""

        elem = ET.SubElement(species_elem, "is_live")
        elem.text = species.is_live.value if species.is_live else ""

        elem = ET.SubElement(species_elem, "primary_db_table")
        elem.text = species.primary_db_table or ""

        elem = ET.SubElement(species_elem, "ensembl_species_name")
        elem.text = species.ensembl_species_name or ""

        if species.created and hasattr(species.created, "isoformat"):
            elem = ET.SubElement(species_elem, "created")
            elem.text = species.created.isoformat()

    # Pretty print XML
    ET.indent(root, space="  ")
    return str(ET.tostring(root, encoding="unicode"))


def format_genefam_as_xml(genefam_list: list[Genefam]) -> str:
    """Format genefam data as XML with proper UTF8MB4 encoding support."""
    root = ET.Element("genefams")

    for genefam in genefam_list:
        genefam_elem = ET.SubElement(root, "genefam")
        genefam_elem.set("genefam_id", str(genefam.genefam_id))
        genefam_elem.set("taxon_id", str(genefam.taxon_id))

        # Add elements with proper text content
        elem = ET.SubElement(genefam_elem, "assigned_id")
        elem.text = genefam.assigned_id or ""

        elem = ET.SubElement(genefam_elem, "assigned_symbol")
        elem.text = genefam.assigned_symbol or ""

        elem = ET.SubElement(genefam_elem, "assigned_name")
        elem.text = genefam.assigned_name or ""

        elem = ET.SubElement(genefam_elem, "status_id")
        elem.text = str(genefam.status_id) if genefam.status_id else ""

        elem = ET.SubElement(genefam_elem, "editor_id")
        elem.text = str(genefam.editor_id) if genefam.editor_id else ""

    # Pretty print XML
    ET.indent(root, space="  ")
    return str(ET.tostring(root, encoding="unicode"))


def format_assembly_as_xml(assembly_list: list[Assembly]) -> str:
    """Format assembly data as XML with proper UTF8MB4 encoding support."""
    root = ET.Element("assemblies")

    for assembly in assembly_list:
        assembly_elem = ET.SubElement(root, "assembly")
        assembly_elem.set("id", str(assembly.id))
        assembly_elem.set("taxon_id", str(assembly.taxon_id))

        # Add elements with proper text content
        elem = ET.SubElement(assembly_elem, "source")
        elem.text = assembly.source or ""

        elem = ET.SubElement(assembly_elem, "name")
        elem.text = assembly.name or ""

        elem = ET.SubElement(assembly_elem, "genbank_assembly_accession")
        elem.text = assembly.genbank_assembly_accession or ""

        elem = ET.SubElement(assembly_elem, "refseq_assembly_accession")
        elem.text = assembly.refseq_assembly_accession or ""

        elem = ET.SubElement(assembly_elem, "is_current")
        elem.text = str(assembly.is_current)

        elem = ET.SubElement(assembly_elem, "is_vgnc_default")
        elem.text = str(assembly.is_vgnc_default)

    # Pretty print XML
    ET.indent(root, space="  ")
    return str(ET.tostring(root, encoding="unicode"))


def format_chromosomes_as_xml(chromosomes_list: list[Chromosomes]) -> str:
    """Format chromosomes data as XML with proper UTF8MB4 encoding support."""
    root = ET.Element("chromosomes")

    for chromosomes in chromosomes_list:
        chromosomes_elem = ET.SubElement(root, "chromosome")
        chromosomes_elem.set("chr_id", str(chromosomes.chr_id))
        chromosomes_elem.set("taxon_id", str(chromosomes.taxon_id))

        # Add elements with proper text content
        elem = ET.SubElement(chromosomes_elem, "display_name")
        elem.text = chromosomes.display_name or ""

        elem = ET.SubElement(chromosomes_elem, "coord_system")
        elem.text = chromosomes.coord_system or ""

        elem = ET.SubElement(chromosomes_elem, "refseq_accession")
        elem.text = chromosomes.refseq_accession or ""

        elem = ET.SubElement(chromosomes_elem, "genbank_accession")
        elem.text = chromosomes.genbank_accession or ""

        elem = ET.SubElement(chromosomes_elem, "ensembl_accession")
        elem.text = chromosomes.ensembl_accession or ""

        # Note: ucsc_name field doesn't exist in Chromosomes model
        # elem = ET.SubElement(chromosomes_elem, "ucsc_name")
        # elem.text = chromosomes.ucsc_name or ""

    # Pretty print XML
    ET.indent(root, space="  ")
    return str(ET.tostring(root, encoding="unicode"))


@cli.command()
@click.option("--limit", "-l", default=10, help="Maximum number of results to return")
@click.option("--offset", "-o", default=0, help="Number of results to skip")
@click.option(
    "--format",
    "-f",
    type=click.Choice(["table", "json", "csv", "xml"]),
    default="table",
    help="Output format",
)
@click.option(
    "--sort-by",
    "-s",
    type=click.Choice(["display_name", "genefam_prefix", "taxon_id", "is_live"]),
    default="display_name",
    help="Sort field",
)
@click.option(
    "--order", type=click.Choice(["asc", "desc"]), default="asc", help="Sort order"
)
@click.pass_context
def query_species(
    ctx: click.Context, limit: int, offset: int, format: str, sort_by: str, order: str
) -> None:
    """Query species information from the database."""
    try:
        ensure_config_loaded(ctx)
        session = get_session(ctx.obj["db_config"], ctx.obj.get("database_url"))

        # Build query
        stmt = select(Species)

        # Add sorting
        if hasattr(Species, sort_by):
            sort_column = getattr(Species, sort_by)
            if order == "desc":
                stmt = stmt.order_by(sort_column.desc())
            else:
                stmt = stmt.order_by(sort_column.asc())

        # Add pagination
        stmt = stmt.offset(offset).limit(limit)

        # Execute query
        species_list = session.execute(stmt).scalars().all()

        # Format and display results
        species_list_fixed = list(species_list)  # Convert Sequence to list
        if format == "table":
            display_species_table(species_list_fixed)
        elif format == "json":
            display_species_json(species_list_fixed)
        elif format == "csv":
            display_species_csv(species_list_fixed)
        elif format == "xml":
            click.echo(format_species_as_xml(species_list_fixed))

        session.close()

    except Exception as e:
        click.echo(f"Error querying species: {e}", err=True)
        ctx.exit(1)


@cli.command()
@click.option("--name", "-n", help="Search by gene family name (supports wildcards)")
@click.option("--symbol", "-s", help="Filter by gene symbol")
@click.option("--status", help="Filter by status")
@click.option("--limit", "-l", default=10, help="Maximum number of results")
@click.option(
    "--format",
    "-f",
    type=click.Choice(["table", "json", "csv", "xml"]),
    default="table",
    help="Output format",
)
@click.pass_context
def query_genefams(
    ctx: click.Context,
    name: str | None,
    symbol: str | None,
    status: str | None,
    limit: int,
    format: str,
) -> None:
    """Query gene family information from the database."""
    try:
        ensure_config_loaded(ctx)
        session = get_session(ctx.obj["db_config"], ctx.obj.get("database_url"))

        # Build query
        stmt = select(Genefam)

        # Add filters
        if name:
            if "*" in name or "%" in name:
                # Pattern matching
                pattern = name.replace("*", "%")
                stmt = stmt.where(Genefam.assigned_id.like(pattern))
            else:
                # Exact match
                stmt = stmt.where(Genefam.assigned_id == name)

        if symbol:
            stmt = stmt.where(Genefam.assigned_symbol == symbol)

        if status:
            # Since relationships are disabled, we can't filter by status relationship
            # This would require joining with the gene_status table
            pass

        # Add limit
        stmt = stmt.limit(limit)

        # Execute query
        genefams = session.execute(stmt).scalars().all()

        # Format and display results
        genefams_fixed = list(genefams)  # Convert Sequence to list
        if format == "table":
            display_genefams_table(genefams_fixed)
        elif format == "json":
            display_genefams_json(genefams_fixed)
        elif format == "csv":
            display_genefams_csv(genefams_fixed)
        elif format == "xml":
            click.echo(format_genefam_as_xml(genefams_fixed))

        session.close()

    except Exception as e:
        click.echo(f"Error querying gene families: {e}", err=True)
        ctx.exit(1)


@cli.command()
@click.argument("genefam_id")
@click.option(
    "--format",
    "-f",
    type=click.Choice(["table", "json", "csv", "xml"]),
    default="table",
    help="Output format",
)
@click.pass_context
def query_genefam_species(ctx: click.Context, genefam_id: str, format: str) -> None:
    """Query species associated with a specific gene family."""
    try:
        ensure_config_loaded(ctx)
        session = get_session(ctx.obj["db_config"], ctx.obj.get("database_url"))

        # Find the gene family by ID or assigned_id
        try:
            genefam_id_int = int(genefam_id)
            genefam_stmt = select(Genefam).where(Genefam.genefam_id == genefam_id_int)
        except ValueError:
            # Search by assigned_id instead
            genefam_stmt = select(Genefam).where(Genefam.assigned_id == genefam_id)

        genefam = session.execute(genefam_stmt).scalar_one_or_none()

        if not genefam:
            click.echo(f"Gene family '{genefam_id}' not found", err=True)
            ctx.exit(1)

        # Get the species for this gene family (query directly since relationships disabled)
        species_stmt = select(Species).where(Species.taxon_id == genefam.taxon_id)
        species = session.execute(species_stmt).scalar_one_or_none()

        # Format and display results
        if format == "table":
            display_genefam_species_table(genefam, [species] if species else [])
        elif format == "json":
            display_genefam_species_json(genefam, species)
        elif format == "csv":
            display_genefam_species_csv(genefam, species)
        elif format == "xml":
            # Create XML for both genefam and species
            root = ET.Element("genefam_species")

            # Add genefam information
            genefam_elem = ET.SubElement(root, "genefam")
            genefam_elem.set("genefam_id", str(genefam.genefam_id))

            elem = ET.SubElement(genefam_elem, "assigned_id")
            elem.text = genefam.assigned_id or ""

            elem = ET.SubElement(genefam_elem, "assigned_symbol")
            elem.text = genefam.assigned_symbol or ""

            elem = ET.SubElement(genefam_elem, "assigned_name")
            elem.text = genefam.assigned_name or ""

            # Add species information if found
            if species:
                species_elem = ET.SubElement(root, "species")
                species_elem.set("taxon_id", str(species.taxon_id))

                elem = ET.SubElement(species_elem, "genefam_prefix")
                elem.text = species.genefam_prefix or ""

                elem = ET.SubElement(species_elem, "display_name")
                elem.text = species.display_name or ""

                elem = ET.SubElement(species_elem, "is_live")
                elem.text = species.is_live.value if species.is_live else ""
            else:
                ET.SubElement(root, "species").text = "Not found"

            # Pretty print XML
            ET.indent(root, space="  ")
            click.echo(ET.tostring(root, encoding="unicode"))

        session.close()

    except Exception as e:
        click.echo(f"Error querying gene family species: {e}", err=True)
        ctx.exit(1)


def get_session(db_config: DatabaseConfig, database_url: str | None = None) -> Session:
    """Create database session from configuration."""
    # Use provided database URL or fall back to config
    url = database_url if database_url else db_config.database_url.get_secret_value()

    engine = create_engine(url, echo=db_config.echo, pool_pre_ping=True)

    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


def display_species_table(species_list: list[Species]) -> None:
    """Display species information in table format."""
    if not species_list:
        click.echo("No species found.")
        return

    click.echo(
        f"{'Taxon ID':<10} {'Display Name':<30} {'Genefam Prefix':<15} {'Live Status':<10}"
    )
    click.echo("-" * 75)

    for species in species_list:
        click.echo(
            f"{species.taxon_id:<10} {species.display_name:<30} "
            f"{species.genefam_prefix:<15} {species.is_live.value:<10}"
        )


def display_species_json(species_list: list[Species]) -> None:
    """Display species information in JSON format."""
    data = []
    for species in species_list:
        data.append(
            {
                "taxon_id": species.taxon_id,
                "display_name": species.display_name,
                "genefam_prefix": species.genefam_prefix,
                "ensembl_species_name": species.ensembl_species_name,
                "scientific_name": species.scientific_name,
                "vgnc_prefix": species.vgnc_prefix,
                "is_live": species.is_live.value,
                "created": (
                    species.created.isoformat()
                    if species.created and hasattr(species.created, "isoformat")
                    else None
                ),
                "is_active": species.is_active,
            }
        )

    click.echo(json.dumps(data, indent=2))


def display_species_csv(species_list: list[Species]) -> None:
    """Display species information in CSV format."""
    if not species_list:
        return

    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow(
        [
            "Taxon ID",
            "Display Name",
            "Genefam Prefix",
            "Ensembl Species Name",
            "Scientific Name",
            "VGNC Prefix",
            "Live Status",
            "Created",
            "Is Active",
        ]
    )

    # Data rows
    for species in species_list:
        writer.writerow(
            [
                species.taxon_id,
                species.display_name,
                species.genefam_prefix,
                species.ensembl_species_name,
                species.scientific_name,
                species.vgnc_prefix,
                species.is_live.value,
                (
                    species.created.isoformat()
                    if species.created and hasattr(species.created, "isoformat")
                    else None
                ),
                species.is_active,
            ]
        )

    click.echo(output.getvalue().strip())


def display_genefams_table(genefams: list[Genefam]) -> None:
    """Display gene families in table format."""
    if not genefams:
        click.echo("No gene families found.")
        return

    click.echo(
        f"{'ID':<10} {'Assigned ID':<20} {'Symbol':<15} {'Status ID':<10} {'Editor ID':<10}"
    )
    click.echo("-" * 80)

    for genefam in genefams:
        click.echo(
            f"{genefam.genefam_id:<10} {genefam.assigned_id:<20} "
            f"{genefam.assigned_symbol or 'N/A':<15} "
            f"{str(genefam.status_id):<10} {str(genefam.editor_id):<10}"
        )


def display_genefams_json(genefams: list[Genefam]) -> None:
    """Display gene families in JSON format."""
    data = []
    for genefam in genefams:
        data.append(
            {
                "genefam_id": genefam.genefam_id,
                "taxon_id": genefam.taxon_id,
                "assigned_id": genefam.assigned_id,
                "assigned_symbol": genefam.assigned_symbol,
                "assigned_name": genefam.assigned_name,
                "status_id": genefam.status_id,
                "editor_id": genefam.editor_id,
                "hcop_support_level": genefam.hcop_support_level,
            }
        )

    click.echo(json.dumps(data, indent=2))


def display_genefams_csv(genefams: list[Genefam]) -> None:
    """Display gene families in CSV format."""
    if not genefams:
        return

    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow(
        [
            "GeneFamily ID",
            "Taxon ID",
            "Assigned ID",
            "Symbol",
            "Name",
            "Status ID",
            "Editor ID",
        ]
    )

    # Data rows
    for genefam in genefams:
        writer.writerow(
            [
                genefam.genefam_id,
                genefam.taxon_id,
                genefam.assigned_id,
                genefam.assigned_symbol,
                genefam.assigned_name,
                str(genefam.status_id),
                str(genefam.editor_id),
            ]
        )

    click.echo(output.getvalue().strip())


def display_genefam_species_table(genefam: Genefam, species_list: list[Any]) -> None:
    """Display gene family-species associations in table format."""
    click.echo(f"Gene Family: {genefam.assigned_id}")
    if genefam.assigned_name:
        click.echo(f"Name: {genefam.assigned_name}")
    click.echo()

    if not species_list:
        click.echo("No species associations found.")
        return

    click.echo(
        f"{'Taxon ID':<10} {'Display Name':<30} {'Genefam Prefix':<15} {'Live Status':<10}"
    )
    click.echo("-" * 75)

    for species in species_list:
        click.echo(
            f"{species.taxon_id:<10} {species.display_name:<30} "
            f"{species.genefam_prefix:<15} {species.is_live.value:<10}"
        )


def display_genefam_species_json(genefam: Genefam, species: Any) -> None:
    """Display gene family-species associations in JSON format."""
    data = {
        "genefam": {
            "genefam_id": genefam.genefam_id,
            "assigned_id": genefam.assigned_id,
            "assigned_name": genefam.assigned_name,
            "status": genefam.status_text,
        }
    }

    if species:
        data["species"] = {
            "taxon_id": species.taxon_id,
            "display_name": species.display_name,
            "genefam_prefix": species.genefam_prefix,
            "ensembl_species_name": species.ensembl_species_name,
            "is_live": species.is_live.value,
            "is_active": species.is_active,
        }
    else:
        data["species"] = {}  # Empty dict instead of None for consistent typing

    click.echo(json.dumps(data, indent=2))


def display_genefam_species_csv(genefam: Genefam, species: Any) -> None:
    """Display gene family-species associations in CSV format."""
    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow(
        [
            "GeneFamily ID",
            "Assigned ID",
            "Assigned Name",
            "Species Taxon ID",
            "Display Name",
            "Genefam Prefix",
            "Live Status",
        ]
    )

    # Data row
    if species:
        writer.writerow(
            [
                genefam.genefam_id,
                genefam.assigned_id,
                genefam.assigned_name,
                species.taxon_id,
                species.display_name,
                species.genefam_prefix,
                species.is_live.value,
            ]
        )
    else:
        writer.writerow(
            [
                genefam.genefam_id,
                genefam.assigned_id,
                genefam.assigned_name,
                "N/A",
                "N/A",
                "N/A",
                "N/A",
            ]
        )

    click.echo(output.getvalue().strip())


# Dedicated export commands
@cli.command()
@click.option(
    "--entity",
    "-e",
    type=click.Choice(["species", "genefams", "assemblies", "chromosomes"]),
    required=True,
    help="Entity type to export",
)
@click.option(
    "--format",
    "-f",
    type=click.Choice(["csv", "json", "xml"]),
    required=True,
    help="Export format",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output file path (if not specified, prints to stdout)",
)
@click.option(
    "--batch-size", "-b", default=1000, help="Number of records to process at a time"
)
@click.option(
    "--progress", "-p", is_flag=True, help="Show progress bar for large exports"
)
@click.pass_context
def export(
    ctx: click.Context,
    entity: str,
    format: str,
    output: str | None,
    batch_size: int,
    progress: bool,
) -> None:
    """Export data in various formats with progress indicators and UTF8MB4 encoding support."""
    try:
        ensure_config_loaded(ctx)
        session = get_session(ctx.obj["db_config"], ctx.obj.get("database_url"))

        # Map entity to model class and formatter
        entity_map = {
            "species": (Species, format_species_as_xml if format == "xml" else None),
            "genefams": (Genefam, format_genefam_as_xml if format == "xml" else None),
            "assemblies": (
                Assembly,
                format_assembly_as_xml if format == "xml" else None,
            ),
            "chromosomes": (
                Chromosomes,
                format_chromosomes_as_xml if format == "xml" else None,
            ),
        }

        if entity not in entity_map:
            click.echo(f"Error: Unknown entity '{entity}'", err=True)
            ctx.exit(1)

        model_class, xml_formatter = entity_map[entity]

        # Count total records for progress tracking
        if progress:
            count_stmt = select(func.count()).select_from(model_class)
            total_records = session.execute(count_stmt).scalar()
            click.echo(f"Exporting {total_records} {entity} records...")

        # Query all records
        stmt = select(model_class).order_by(
            getattr(
                model_class,
                next(
                    col.name for col in model_class.__table__.columns if col.primary_key
                ),
            )
        )

        if progress:
            # Process with progress bar
            records = []
            bar: Any = click.progressbar(
                length=total_records, label=f"Exporting {entity}"
            )
            with bar:
                for record in session.execute(stmt):
                    records.append(record[0])
                    bar.update(1)
        else:
            # Process without progress bar
            records = [record[0] for record in session.execute(stmt)]

        # Format output
        if format == "json":
            output_data = []
            for record in records:
                output_data.append(record.to_dict())
            formatted_output = json.dumps(
                output_data, indent=2, ensure_ascii=False, default=str
            )

        elif format == "csv":
            output_stream = io.StringIO()

            # Get column headers
            headers = [col.name for col in model_class.__table__.columns]
            writer = csv.DictWriter(output_stream, fieldnames=headers)
            writer.writeheader()

            # Write data rows
            for record in records:
                row_data = {}
                for col in model_class.__table__.columns:
                    value = getattr(record, col.name)
                    if hasattr(value, "value"):  # Handle enums
                        value = value.value
                    row_data[col.name] = value
                writer.writerow(row_data)

            formatted_output = output_stream.getvalue()

        elif format == "xml":
            if xml_formatter:
                formatted_output = xml_formatter(records)
            else:
                click.echo(
                    f"Error: XML formatter not implemented for {entity}", err=True
                )
                ctx.exit(1)

        # Write to file or stdout
        if output:
            with open(output, "w", encoding="utf-8") as f:
                f.write(formatted_output)
            click.echo(f"✓ Exported {len(records)} {entity} records to {output}")
        else:
            click.echo(formatted_output)

        session.close()

        if progress:
            click.echo(
                f"✓ Successfully exported {len(records)} {entity} records in {format} format"
            )

    except Exception as e:
        click.echo(f"Error exporting {entity}: {e}", err=True)
        ctx.exit(1)


@cli.command()
@click.option("--query", "-q", required=True, help="SQL query to execute and export")
@click.option(
    "--format",
    "-f",
    type=click.Choice(["csv", "json", "xml"]),
    required=True,
    help="Export format",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output file path (if not specified, prints to stdout)",
)
@click.pass_context
def export_query(
    ctx: click.Context, query: str, format: str, output: str | None
) -> None:
    """Execute custom SQL query and export results."""
    try:
        ensure_config_loaded(ctx)
        session = get_session(ctx.obj["db_config"], ctx.obj.get("database_url"))

        click.echo(f"Executing query: {query}")

        # Execute custom query
        result = session.execute(text(query))

        # Convert to list of dictionaries
        records = []
        for row in result:
            records.append(dict(row._mapping))

        if not records:
            click.echo("No results found")
            return

        # Format output
        if format == "json":
            formatted_output = json.dumps(
                records, indent=2, ensure_ascii=False, default=str
            )
        elif format == "csv":
            output_stream = io.StringIO()

            if records:
                writer = csv.DictWriter(output_stream, fieldnames=records[0].keys())
                writer.writeheader()
                writer.writerows(records)

            formatted_output = output_stream.getvalue()

        elif format == "xml":
            # Create custom XML from query results
            root = ET.Element("query_results")
            for record in records:
                record_elem = ET.SubElement(root, "record")
                for key, value in record.items():
                    elem = ET.SubElement(record_elem, key)
                    elem.text = str(value) if value is not None else ""

            ET.indent(root, space="  ")
            formatted_output = ET.tostring(root, encoding="unicode")

        # Write to file or stdout
        if output:
            with open(output, "w", encoding="utf-8") as f:
                f.write(formatted_output)
            click.echo(f"✓ Exported {len(records)} query results to {output}")
        else:
            click.echo(formatted_output)

        session.close()
        click.echo(
            f"✓ Successfully exported {len(records)} query results in {format} format"
        )

    except Exception as e:
        click.echo(f"Error executing query: {e}", err=True)
        ctx.exit(1)


if __name__ == "__main__":
    cli()
