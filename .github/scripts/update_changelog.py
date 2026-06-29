#!/usr/bin/env python3
"""
Update CHANGELOG.md file with new release notes.
Maintains proper changelog format and preserves existing entries.
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path


class ChangelogUpdater:
    """Handles updating CHANGELOG.md files."""

    def __init__(self, changelog_file: str):
        self.changelog_path = Path(changelog_file)
        self.changelog_content = ""

    def load_changelog(self):
        """Load existing changelog content."""
        if self.changelog_path.exists():
            self.changelog_content = self.changelog_path.read_text(encoding="utf-8")
        else:
            # Create new changelog with header
            self.changelog_content = self._create_new_changelog_header()

    def _create_new_changelog_header(self) -> str:
        """Create header for a new changelog file."""
        today = datetime.now().strftime("%Y-%m-%d")
        header = f"""# CHANGELOG

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Started on {today}.

"""
        return header

    def add_release_entry(self, version: str, release_notes: str):
        """
        Add a new release entry to the changelog.

        Args:
            version: Version number (e.g., "1.2.3")
            release_notes: Formatted release notes content
        """
        # Find where to insert the new release (after header, before other releases)
        header_end_marker = "## ["
        if header_end_marker in self.changelog_content:
            # Insert before the first existing release
            insert_pos = self.changelog_content.find(header_end_marker)
            if insert_pos == -1:
                # Fallback: add at the end
                insert_pos = len(self.changelog_content)
        else:
            # Add after the header
            lines = self.changelog_content.split("\n")
            insert_pos = 0
            # Skip empty lines at the end
            for i, line in enumerate(lines):
                if line.strip() == "" and i < len(lines) - 1:
                    insert_pos = i + 1
                elif line.strip() != "":
                    break
            # Convert to character position
            if insert_pos < len(lines):
                insert_pos = len("\n".join(lines[:insert_pos])) + 1
            else:
                insert_pos = len(self.changelog_content)

        # Prepare new release entry
        # Ensure the release notes start with the version header
        if not release_notes.startswith(
            f"# Release v{version}"
        ) and not release_notes.startswith("## ["):
            # Add version header if not present
            release_header = f"## [{version}]\n\n"
            release_notes = release_header + release_notes

        # Insert the new release
        before = self.changelog_content[:insert_pos]
        after = self.changelog_content[insert_pos:]

        # Ensure proper spacing
        if before and not before.endswith("\n\n"):
            if before.endswith("\n"):
                before += "\n"
            else:
                before += "\n\n"

        if after and not after.startswith("\n"):
            after = "\n" + after

        self.changelog_content = before + release_notes + after

    def save_changelog(self):
        """Save the updated changelog to file."""
        # Ensure the file ends with a newline
        if self.changelog_content and not self.changelog_content.endswith("\n"):
            self.changelog_content += "\n"

        self.changelog_path.write_text(self.changelog_content, encoding="utf-8")

    def validate_changelog_format(self) -> bool:
        """Validate that the changelog follows proper format."""
        if not self.changelog_content.strip():
            print("Error: Changelog is empty", file=sys.stderr)
            return False

        # Check for basic structure
        if not self.changelog_content.startswith("# CHANGELOG"):
            print(
                "Warning: Changelog doesn't start with '# CHANGELOG' header",
                file=sys.stderr,
            )

        # Check for at least one release section
        if "## [" not in self.changelog_content:
            print("Warning: No release sections found in changelog", file=sys.stderr)

        return True

    def get_existing_versions(self) -> list:
        """Get list of existing versions in changelog."""
        import re

        version_pattern = r"## \[([0-9]+\.[0-9]+\.[0-9]+)\]"
        matches = re.findall(version_pattern, self.changelog_content)
        return matches

    def version_exists(self, version: str) -> bool:
        """Check if version already exists in changelog."""
        return f"[{version}]" in self.changelog_content


def main():
    parser = argparse.ArgumentParser(description="Update CHANGELOG.md with new release")
    parser.add_argument(
        "--changelog-file", default="CHANGELOG.md", help="Path to CHANGELOG.md file"
    )
    parser.add_argument(
        "--release-notes-file",
        required=True,
        help="File containing release notes content",
    )
    parser.add_argument(
        "--version", required=True, help="Version number for the release"
    )
    parser.add_argument(
        "--backup", action="store_true", help="Create backup of existing changelog"
    )
    parser.add_argument(
        "--force", action="store_true", help="Overwrite existing version entry"
    )

    args = parser.parse_args()

    try:
        # Load release notes
        release_notes_path = Path(args.release_notes_file)
        if not release_notes_path.exists():
            print(
                f"Error: Release notes file not found: {args.release_notes_file}",
                file=sys.stderr,
            )
            return 1

        release_notes = release_notes_path.read_text(encoding="utf-8").strip()
        if not release_notes:
            print("Error: Release notes file is empty", file=sys.stderr)
            return 1

        # Initialize changelog updater
        updater = ChangelogUpdater(args.changelog_file)

        # Load existing changelog
        updater.load_changelog()

        # Create backup if requested
        if args.backup and updater.changelog_path.exists():
            backup_path = updater.changelog_path.with_suffix(".md.backup")
            updater.changelog_path.rename(backup_path)
            print(f"📋 Created backup: {backup_path}")
            # Reload (since we moved the original)
            updater.load_changelog()

        # Check if version already exists
        if updater.version_exists(args.version) and not args.force:
            print(
                f"Error: Version {args.version} already exists in changelog",
                file=sys.stderr,
            )
            print("Use --force to overwrite existing entry", file=sys.stderr)
            return 1

        # Add the new release entry
        updater.add_release_entry(args.version, release_notes)

        # Validate the format
        if not updater.validate_changelog_format():
            print("Warning: Changelog format validation failed", file=sys.stderr)

        # Save the updated changelog
        updater.save_changelog()

        print(f"✅ Updated {args.changelog_file} with release v{args.version}")

        # Show summary
        existing_versions = updater.get_existing_versions()
        print(f"📝 Changelog now contains {len(existing_versions)} release(s)")

        if args.version in existing_versions:
            print(f"📄 Added release entry for v{args.version}")
        else:
            print(
                f"⚠️  Warning: Version v{args.version} may not have been added correctly"
            )

    except Exception as e:
        print(f"Error updating changelog: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
