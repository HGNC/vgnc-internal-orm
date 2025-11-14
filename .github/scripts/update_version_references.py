#!/usr/bin/env python3
"""
Simple version reference updater without complex dependencies.
Updates README.md, documentation files, and other files that contain version numbers.
"""

import argparse
import re
import sys
from pathlib import Path


class VersionReferenceUpdater:
    """Simple version reference updater without dataclasses."""

    def __init__(self):
        # File patterns to exclude from updates
        self.exclude_patterns = [
            r".git/",
            r"node_modules/",
            r".venv/",
            r"venv/",
            r"__pycache__/",
            r".pytest_cache/",
            r"build/",
            r"dist/",
            r".eggs/",
            "CHANGELOG.md",  # Handled separately
            "pyproject.toml",  # Handled separately
            ".github/workflows/",  # Workflow files
            ".github/scripts/",  # Script files
        ]

        # Files that definitely should be checked
        self.priority_files = [
            "README.md",
        ]

    def should_exclude_file(self, file_path: Path) -> bool:
        """Check if file should be excluded from version updates."""
        file_str = str(file_path)

        for pattern in self.exclude_patterns:
            if re.search(pattern, file_str):
                return True

        return False

    def find_files_to_update(self, root_dir: str = ".") -> list:
        """Find all files that might contain version references."""
        root_path = Path(root_dir)
        files_to_check = []

        # Always include priority files
        for priority_file in self.priority_files:
            priority_path = root_path / priority_file
            if priority_path.exists():
                files_to_check.append(priority_path)

        # Find markdown files in docs
        docs_path = root_path / "docs"
        if docs_path.exists():
            for md_file in docs_path.glob("*.md"):
                if not self.should_exclude_file(md_file) and md_file not in files_to_check:
                    files_to_check.append(md_file)

        return sorted(files_to_check)

    def update_file(self, file_path: Path, old_version: str, new_version: str):
        """Update version references in a single file."""
        file_str = str(file_path)
        changes = 0
        errors = []

        try:
            content = file_path.read_text(encoding='utf-8')
            original_content = content

            # Update README.md version line
            if file_path.name == "README.md":
                content = re.sub(
                    r"^\*\*Version:\*\s*[0-9]+\.[0-9]+\.[0-9]+",
                    f"**Version:** {new_version}",
                    content,
                    flags=re.MULTILINE
                )

            # Update documentation version headers
            if str(file_path).startswith("docs/"):
                content = re.sub(
                    r"^\*\*Version:\*\s*[0-9]+\.[0-9]+\.[0-9]+",
                    f"**Version:** {new_version}",
                    content,
                    flags=re.MULTILINE
                )

            # Update project titles
            content = re.sub(
                r"\*\*VGNC Internal ORM v[0-9]+\.[0-9]+\.[0-9]+\*\*",
                f"**VGNC Internal ORM v{new_version}**",
                content
            )

            # Update version tags
            content = re.sub(
                r"v[0-9]+\.[0-9]+\.[0-9]+",
                f"v{new_version}",
                content
            )

            # Update standalone version numbers
            content = re.sub(
                r"(?<!v)[0-9]+\.[0-9]+\.[0-9]+(?=\*\*|\n|`|$|s)",
                f"{new_version}",
                content
            )

            # Update version numbers in code blocks
            content = re.sub(
                r"`[0-9]+\.[0-9]+\.[0-9]+`",
                f"`{new_version}`",
                content
            )

            # Check if content was actually changed
            if content != original_content:
                file_path.write_text(content, encoding='utf-8')
                changes += 1
                return changes

        except Exception as e:
            errors.append(str(e))

        if errors:
            print(f"Error updating {file_path}: {errors[0]}", file=sys.stderr)

        return changes

    def update_all_references(self, old_version: str, new_version: str, root_dir: str = "."):
        """Update version references across all relevant files."""
        files_to_update = self.find_files_to_update(root_dir)

        print(f"🔍 Checking {len(files_to_update)} files for version references...")
        total_changes = 0

        for file_path in files_to_update:
            print(f"  📄 {file_path.relative_to(root_dir)}", end="")

            changes = self.update_file(file_path, old_version, new_version)
            total_changes += changes

            if changes > 0:
                print(f" ✅ ({changes} changes)")
            else:
                print(" ⭕ No changes needed")

        print(f"\n📊 Total changes made: {total_changes}")
        return total_changes

    def get_current_version(self, pyproject_path: str = "pyproject.toml"):
        """Get current version from pyproject.toml."""
        try:
            with open(pyproject_path, 'r') as f:
                content = f.read()
                # Look for version = "x.x.x" pattern
                match = re.search(r'version\s*=\s*"([^"]+)"', content)
                if match:
                    return match.group(1).strip()
        except Exception:
            pass
        return ""


def main():
    parser = argparse.ArgumentParser(description='Update version references in documentation and other files')
    parser.add_argument('--old-version', help='Old version to replace')
    parser.add_argument('--new-version', required=True, help='New version to set')
    parser.add_argument('--root', default='.', help='Root directory to search')
    parser.add_argument('--from-pyproject', action='store_true', help='Get old version from pyproject.toml')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')

    args = parser.parse_args()

    updater = VersionReferenceUpdater()

    # Get old version
    old_version = args.old_version
    if args.from_pyproject or not old_version:
        old_version = updater.get_current_version()
        if not old_version:
            print("❌ Could not determine old version", file=sys.stderr)
            return 1
        if not args.old_version:
            print(f"📖 Detected old version from pyproject.toml: {old_version}")

    if old_version == args.new_version:
        print("ℹ️  No version update needed (versions are identical)")
        return 0

    # Perform actual updates
    try:
        changes = updater.update_all_references(old_version, args.new_version, args.root)

        if changes > 0:
            print(f"\n✅ Successfully updated {changes} version references!")
        else:
            print(f"\n✅ No version references needed updating")

        return 0

    except Exception as e:
        print(f"❌ Error updating version references: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())