#!/usr/bin/env python3
"""
Generate release notes and changelog entries based on commit analysis.
Follows conventional commits specification for structured release notes.
"""

import argparse
import json
import sys
from datetime import datetime
from typing import Any


class ReleaseNotesGenerator:
    """Generates release notes from commit analysis."""

    def __init__(self):
        self.emojis = {
            "breaking": "💥",
            "feat": "✨",
            "fix": "🐛",
            "docs": "📚",
            "style": "💎",
            "refactor": "🔨",
            "perf": "⚡",
            "test": "🧪",
            "build": "📦",
            "ci": "🤖",
            "chore": "🧹",
            "revert": "⏪",
        }

        self.descriptions = {
            "feat": "New Features",
            "fix": "Bug Fixes",
            "breaking": "⚠️ BREAKING CHANGES",
            "docs": "Documentation",
            "style": "Style Changes",
            "refactor": "Code Refactoring",
            "perf": "Performance Improvements",
            "test": "Tests",
            "build": "Build System",
            "ci": "Continuous Integration",
            "chore": "Chores",
            "revert": "Reverts",
        }

    def generate_release_notes(
        self, analysis_data: dict[str, Any], current_version: str, new_version: str
    ) -> str:
        """
        Generate comprehensive release notes.

        Args:
            analysis_data: Commit analysis data
            current_version: Previous version
            new_version: New version being released

        Returns:
            Formatted release notes string
        """
        categorized_commits = analysis_data.get("categorized_commits", {})
        stats = analysis_data.get("stats", {})

        # Generate header
        notes = self._generate_header(new_version, current_version)

        # Add breaking changes section first (most important)
        breaking_changes = categorized_commits.get("breaking_changes", [])
        if breaking_changes:
            notes += self._generate_breaking_changes_section(breaking_changes)

        # Add new features
        features = categorized_commits.get("features", [])
        if features:
            notes += self._generate_features_section(features)

        # Add bug fixes
        fixes = categorized_commits.get("fixes", [])
        if fixes:
            notes += self._generate_fixes_section(fixes)

        # Add other changes
        other_changes = categorized_commits.get("other", [])
        if other_changes:
            notes += self._generate_other_section(other_changes)

        # Add statistics footer
        notes += self._generate_footer(stats, current_version, new_version)

        return notes

    def _generate_header(self, new_version: str, current_version: str) -> str:
        """Generate release notes header."""
        today = datetime.now().strftime("%Y-%m-%d")

        header = f"# Release v{new_version}\n\n"
        header += f"**Released:** {today}\n"

        if current_version != new_version:
            header += f"**From:** v{current_version}\n"

        header += "\n---\n\n"

        return header

    def _generate_breaking_changes_section(self, breaking_changes: list[dict]) -> str:
        """Generate breaking changes section."""
        section = f"## {self.descriptions['breaking']}\n\n"

        for change in breaking_changes:
            commit_hash = change.get("hash", "")
            description = change.get("description", "")
            scope = change.get("scope", "")

            # Handle None values safely
            if description is None:
                description = ""
            if commit_hash is None:
                commit_hash = ""

            if scope:
                line = f"- **({scope})** {description} ({commit_hash})\n"
            else:
                line = f"- {description} ({commit_hash})\n"

            section += line

        section += "\n"
        return section

    def _generate_features_section(self, features: list[dict]) -> str:
        """Generate new features section."""
        section = f"## {self.descriptions['feat']}\n\n"

        # Group features by scope
        features_by_scope = {}
        uncategorized_features = []

        for feature in features:
            scope = feature.get("scope")
            description = feature.get("description", "")
            commit_hash = feature.get("hash", "")

            # Handle None values safely
            if description is None:
                description = ""
            if commit_hash is None:
                commit_hash = ""

            if scope:
                if scope not in features_by_scope:
                    features_by_scope[scope] = []
                features_by_scope[scope].append((description, commit_hash))
            else:
                uncategorized_features.append((description, commit_hash))

        # Add features grouped by scope
        for scope, scope_features in sorted(features_by_scope.items()):
            section += f"### {scope}\n\n"
            for description, commit_hash in scope_features:
                section += f"- {description} ({commit_hash})\n"
            section += "\n"

        # Add uncategorized features
        if uncategorized_features:
            for description, commit_hash in uncategorized_features:
                section += f"- {description} ({commit_hash})\n"
            section += "\n"

        return section

    def _generate_fixes_section(self, fixes: list[dict]) -> str:
        """Generate bug fixes section."""
        section = f"## {self.descriptions['fix']}\n\n"

        # Group fixes by scope
        fixes_by_scope = {}
        uncategorized_fixes = []

        for fix in fixes:
            scope = fix.get("scope")
            description = fix.get("description", "")
            commit_hash = fix.get("hash", "")

            # Handle None values safely
            if description is None:
                description = ""
            if commit_hash is None:
                commit_hash = ""

            if scope:
                if scope not in fixes_by_scope:
                    fixes_by_scope[scope] = []
                fixes_by_scope[scope].append((description, commit_hash))
            else:
                uncategorized_fixes.append((description, commit_hash))

        # Add fixes grouped by scope
        for scope, scope_fixes in sorted(fixes_by_scope.items()):
            section += f"### {scope}\n\n"
            for description, commit_hash in scope_fixes:
                section += f"- {description} ({commit_hash})\n"
            section += "\n"

        # Add uncategorized fixes
        if uncategorized_fixes:
            for description, commit_hash in uncategorized_fixes:
                section += f"- {description} ({commit_hash})\n"
            section += "\n"

        return section

    def _generate_other_section(self, other_changes: list[dict]) -> str:
        """Generate other changes section."""
        # Group other changes by type
        changes_by_type = {}

        for change in other_changes:
            commit_type = change.get("type", "other")
            commit_hash = change.get("hash", "")
            description = change.get("description", "")

            # Handle None values safely
            if description is None:
                description = ""
            if commit_hash is None:
                commit_hash = ""
            if commit_type is None:
                commit_type = "other"

            if commit_type not in changes_by_type:
                changes_by_type[commit_type] = []
            changes_by_type[commit_type].append((description, commit_hash))

        section = ""

        # Sort keys safely, ensuring all are strings
        sorted_keys = sorted([str(k) for k in changes_by_type.keys() if k is not None])
        for commit_type in sorted_keys:
            changes = changes_by_type[commit_type]
            if commit_type in self.descriptions and commit_type not in [
                "feat",
                "fix",
                "breaking",
            ]:
                section += f"## {self.descriptions[commit_type]}\n\n"
                for description, commit_hash in changes:
                    section += f"- {description} ({commit_hash})\n"
                section += "\n"

        return section

    def _generate_footer(
        self, stats: dict[str, Any], current_version: str, new_version: str
    ) -> str:
        """Generate release notes footer with statistics."""
        footer = "---\n\n"
        footer += "## 📊 Release Statistics\n\n"

        total_commits = stats.get("total_commits", 0)
        conventional_commits = sum(stats.get("conventional_commits", {}).values())

        footer += f"- **Total commits:** {total_commits}\n"
        footer += f"- **Conventional commits:** {conventional_commits}\n"

        if stats.get("breaking_changes", 0) > 0:
            footer += f"- **Breaking changes:** {stats['breaking_changes']}\n"

        if stats.get("features", 0) > 0:
            footer += f"- **New features:** {stats['features']}\n"

        if stats.get("fixes", 0) > 0:
            footer += f"- **Bug fixes:** {stats['fixes']}\n"

        # Add version change info
        if current_version != new_version:
            try:
                # Try to import version bumper for proper comparison
                from packaging import version as pkg_version

                if pkg_version.parse(new_version) > pkg_version.parse(current_version):
                    footer += (
                        f"\n**Version bump:** v{current_version} → v{new_version}\n"
                    )
            except ImportError:
                # Fallback: just show the version change
                footer += f"\n**Version change:** v{current_version} → v{new_version}\n"

        footer += "\n"
        return footer

    def generate_simple_summary(
        self, analysis_data: dict[str, Any], current_version: str, new_version: str
    ) -> str:
        """Generate a simple summary for short release notes."""
        categorized = analysis_data.get("categorized_commits", {})

        breaking_count = len(categorized.get("breaking_changes", []))
        feature_count = len(categorized.get("features", []))
        fix_count = len(categorized.get("fixes", []))

        summary_parts = []

        if breaking_count > 0:
            summary_parts.append(
                f"**{breaking_count} breaking change{'s' if breaking_count != 1 else ''}**"
            )

        if feature_count > 0:
            summary_parts.append(
                f"**{feature_count} new feature{'s' if feature_count != 1 else ''}**"
            )

        if fix_count > 0:
            summary_parts.append(
                f"**{fix_count} bug fix{'es' if fix_count != 1 else ''}**"
            )

        if not summary_parts:
            return f"Release v{new_version} - Internal changes and improvements"

        return f"Release v{new_version} - {', '.join(summary_parts)}"


def main():
    parser = argparse.ArgumentParser(
        description="Generate release notes from commit analysis"
    )
    parser.add_argument(
        "--analysis-file", required=True, help="JSON file with commit analysis"
    )
    parser.add_argument("--current-version", required=True, help="Current version")
    parser.add_argument("--new-version", required=True, help="New version")
    parser.add_argument("--output", help="Output file (default: stdout)")
    parser.add_argument(
        "--simple", action="store_true", help="Generate simple summary only"
    )
    parser.add_argument(
        "--format",
        choices=["markdown", "text"],
        default="markdown",
        help="Output format",
    )

    args = parser.parse_args()

    try:
        with open(args.analysis_file) as f:
            analysis_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: Analysis file not found: {args.analysis_file}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in analysis file: {e}", file=sys.stderr)
        return 1

    generator = ReleaseNotesGenerator()

    try:
        if args.simple:
            notes = generator.generate_simple_summary(
                analysis_data, args.current_version, args.new_version
            )
        else:
            notes = generator.generate_release_notes(
                analysis_data, args.current_version, args.new_version
            )

        if args.output:
            with open(args.output, "w") as f:
                f.write(notes)
        else:
            print(notes)

    except Exception as e:
        import traceback

        print(f"Error generating release notes: {e}", file=sys.stderr)
        print(f"Traceback: {traceback.format_exc()}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
