#!/usr/bin/env python3
"""
Intelligent commit analyzer that automatically detects change types from code diffs.
Analyzes file patterns and content changes to determine version bump requirements.
"""

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from enum import Enum
from typing import Any


class ChangeType(Enum):
    """Types of changes that affect version bumping."""

    MAJOR = "major"  # Breaking changes
    MINOR = "minor"  # New features
    PATCH = "patch"  # Bug fixes
    NONE = "none"  # No version change


@dataclass
class FileChange:
    """Information about a file change."""

    path: str
    change_type: str  # 'A' Added, 'M' Modified, 'D' Deleted
    additions: int
    deletions: int
    file_type: str
    is_api: bool = False
    is_config: bool = False
    is_doc: bool = False
    is_test: bool = False


class IntelligentCommitAnalyzer:
    """Analyzes code changes to automatically determine version bump requirements."""

    def __init__(self):
        # File patterns that indicate different types of changes
        self.API_PATTERNS = [
            r"^src/.*\.py$",  # Source code (must start with src/)
            r"^src/vgnc_internal_orm/.*",  # ORM models and core
            r"^src/.*__init__\.py$",  # Public API exports
        ]

        # Exclude patterns to avoid analyzing our own scripts
        self.EXCLUDE_PATTERNS = [
            r"^\.github/",  # GitHub workflows and scripts
            r"^docs/",  # Documentation files
            r"^.*\.md$",  # Markdown files
            r"^.*\.yml$",
            r"^.*\.yaml$",  # YAML files
            r"^.*\.json$",  # JSON files
            r"^.*\.txt$",  # Text files
        ]

        self.CONFIG_PATTERNS = [
            r"pyproject\.toml$",  # Package configuration
            r"requirements.*\.txt$",  # Dependencies
            r"\.env.*",  # Environment files
            r"\.yaml$",
            r"\.yml$",  # YAML configs
            r"\.json$",  # JSON configs (if not src)
        ]

        self.DOC_PATTERNS = [
            r"README\.md$",  # Documentation
            r"docs/.*\.md$",  # Documentation files
            r"\.rst$",  # ReStructuredText
            r"CHANGELOG\.md$",  # Changelog
        ]

        self.TEST_PATTERNS = [
            r"tests/.*",  # Test files
            r"test_.*\.py$",  # Test Python files
            r".*_test\.py$",  # Test Python files
        ]

        self.BREAKING_CHANGE_INDICATORS = [
            # Function/API removals (more specific)
            r"^-\s*def\s+\w+.*:\s*#.*removed",
            r"^-\s*class\s+\w+.*:\s*#.*removed",
            # Import removals (more specific)
            r"^-\s*from\s+[\w\.]+import\s+\w+",
            r"^-\s*import\s+[\w\.]+",
            # Breaking change annotations in commit messages only
            r"BREAKING CHANGE:",
            r"BREAKING-CHANGE:",
            # API signature changes (more restrictive)
            r"^-\s*def\s+(\w+)\([^)]*\):.*\n^\+\s*def\s+\1\([^)]*\):",  # Parameter changes across lines
        ]

        self.FEATURE_INDICATORS = [
            # New functions/classes
            r"^\+\s*def\s+\w+",
            r"^\+\s*class\s+\w+",
            r"^\+\s*async\s+def\s+\w+",
            # New exports
            r"^\+\s*__all__",
            r"^\+\s*from\s+.*import.*\*",
            # New routes/endpoints
            r"^\+\s*@\w+\.route",
            r"^\+\s*app\.\w+",
            # New dependencies (minor features)
            r"^\+\s*\w+\s*>=",
        ]

        self.BUG_FIX_INDICATORS = [
            # Code change patterns that suggest fixes (more specific)
            r"^\+\s*#.*fix.*bug",
            r"^\+\s*#.*bug.*fix",
            r"^-\s*#.*bug",
            r"^-\s*#.*todo.*bug",
            # Exception handling additions (more restrictive)
            r"^\+\s*except\s+\w+Error:",
            r"^\+\s*except\s+\w+Exception:",
            r"^\+\s*raise\s+\w+Error",
        ]

    def get_file_changes(self, commit_range: str) -> list[FileChange]:
        """Get detailed file changes for a commit range."""
        try:
            # Get git diff summary
            result = subprocess.run(
                ["git", "diff", "--numstat", "--name-status", commit_range],
                capture_output=True,
                text=True,
                check=True,
            )

            if not result.stdout.strip():
                return []

            changes = []
            for line in result.stdout.strip().split("\n"):
                if line.strip():
                    parts = line.split("\t")
                    if len(parts) >= 3:
                        change_type = parts[2]
                        additions = int(parts[0]) if parts[0] != "-" else 0
                        deletions = int(parts[1]) if parts[1] != "-" else 0
                        file_path = parts[2] if len(parts) == 3 else parts[3]

                        file_change = FileChange(
                            path=file_path,
                            change_type=change_type,
                            additions=additions,
                            deletions=deletions,
                            file_type=self._get_file_type(file_path),
                            is_api=self._matches_patterns(file_path, self.API_PATTERNS),
                            is_config=self._matches_patterns(
                                file_path, self.CONFIG_PATTERNS
                            ),
                            is_doc=self._matches_patterns(file_path, self.DOC_PATTERNS),
                            is_test=self._matches_patterns(
                                file_path, self.TEST_PATTERNS
                            ),
                        )
                        changes.append(file_change)

            return changes

        except subprocess.CalledProcessError as e:
            print(f"Error getting file changes: {e}", file=sys.stderr)
            return []

    def get_commit_messages(self, commit_range: str) -> list[str]:
        """Get commit messages for analysis."""
        try:
            result = subprocess.run(
                ["git", "log", "--pretty=format:%s", commit_range],
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip().split("\n") if result.stdout.strip() else []
        except subprocess.CalledProcessError:
            return []

    def _get_file_type(self, file_path: str) -> str:
        """Get file type from path."""
        if "." in file_path:
            return file_path.split(".")[-1].lower()
        return "unknown"

    def _matches_patterns(self, file_path: str, patterns: list[str]) -> bool:
        """Check if file path matches any of the given patterns."""
        # First check if file should be excluded
        for pattern in self.EXCLUDE_PATTERNS:
            if re.search(pattern, file_path):
                return False

        # Then check if it matches the desired patterns
        for pattern in patterns:
            if re.search(pattern, file_path):
                return True
        return False

    def analyze_content_changes(self, commit_range: str) -> dict[str, Any]:
        """Analyze actual content changes for breaking changes and features."""
        try:
            # Get file changes first to filter
            file_changes = self.get_file_changes(commit_range)

            # Only analyze source code files
            source_files = [
                c for c in file_changes if c.is_api and not self._should_exclude(c.path)
            ]

            if not source_files:
                return {
                    "breaking_changes": 0,
                    "features": 0,
                    "bug_fixes": 0,
                    "breaking_details": [],
                    "feature_details": [],
                    "bug_fix_details": [],
                }

            # Get diff for only source files
            diff_files = [f.path for f in source_files]
            if not diff_files:
                return {
                    "breaking_changes": 0,
                    "features": 0,
                    "bug_fixes": 0,
                    "breaking_details": [],
                    "feature_details": [],
                    "bug_fix_details": [],
                }

            result = subprocess.run(
                ["git", "diff", commit_range, "--"] + diff_files,
                capture_output=True,
                text=True,
                check=True,
            )

            diff_content = result.stdout

            # Look for breaking changes (more conservative)
            breaking_changes = []
            for pattern in self.BREAKING_CHANGE_INDICATORS:
                matches = re.findall(pattern, diff_content, re.MULTILINE)
                breaking_changes.extend(matches)

            # Look for new features (only in source files)
            features = []
            for pattern in self.FEATURE_INDICATORS:
                matches = re.findall(pattern, diff_content, re.MULTILINE)
                # Filter out matches from comments
                features.extend([m for m in matches if not m.strip().startswith("#")])

            # Look for bug fixes (more conservative)
            bug_fixes = []
            for pattern in self.BUG_FIX_INDICATORS:
                matches = re.findall(pattern, diff_content, re.MULTILINE)
                bug_fixes.extend(matches)

            return {
                "breaking_changes": len(breaking_changes),
                "features": len(features),
                "bug_fixes": len(bug_fixes),
                "breaking_details": breaking_changes[:3],  # First 3 examples
                "feature_details": features[:5],  # First 5 examples
                "bug_fix_details": bug_fixes[:5],  # First 5 examples
            }

        except subprocess.CalledProcessError:
            return {
                "breaking_changes": 0,
                "features": 0,
                "bug_fixes": 0,
                "breaking_details": [],
                "feature_details": [],
                "bug_fix_details": [],
            }

    def _should_exclude(self, file_path: str) -> bool:
        """Check if file should be excluded from analysis."""
        for pattern in self.EXCLUDE_PATTERNS:
            if re.search(pattern, file_path):
                return True
        return False

    def analyze_commit_messages(self, messages: list[str]) -> dict[str, Any]:
        """Analyze commit messages for semantic information."""
        analysis = {
            "conventional_commits": {
                "feat": 0,
                "fix": 0,
                "docs": 0,
                "style": 0,
                "refactor": 0,
                "perf": 0,
                "test": 0,
                "build": 0,
                "ci": 0,
                "chore": 0,
                "revert": 0,
            },
            "breaking_keywords": 0,
            "feature_keywords": 0,
            "fix_keywords": 0,
            "total_messages": len(messages),
        }

        conventional_pattern = re.compile(
            r"^(?P<type>\w+)(?:\([^)]+\))?!?:\s*(?P<desc>.+)"
        )

        for message in messages:
            # Check for conventional commits
            match = conventional_pattern.match(message)
            if match:
                commit_type = match.group("type")
                if commit_type in analysis["conventional_commits"]:
                    analysis["conventional_commits"][commit_type] += 1
                if "!" in message or "BREAKING" in message.upper():
                    analysis["breaking_keywords"] += 1

            # Check for keywords in non-conventional commits (more specific)
            message_lower = message.lower()
            if any(
                keyword in message_lower
                for keyword in [
                    "breaking change",
                    "remove api",
                    "delete function",
                    "deprecat",
                ]
            ):
                analysis["breaking_keywords"] += 1
            elif any(
                keyword in message_lower
                for keyword in ["add new", "implement", "new feature", "support"]
            ):
                analysis["feature_keywords"] += 1
            elif any(
                keyword in message_lower
                for keyword in ["fix bug", "fix issue", "resolve error", "bug fix"]
            ):
                analysis["fix_keywords"] += 1

        return analysis

    def determine_version_bump(
        self,
        file_changes: list[FileChange],
        content_analysis: dict[str, Any],
        message_analysis: dict[str, Any],
    ) -> ChangeType:
        """Determine version bump based on all analysis."""

        # Check for breaking changes (highest priority)
        breaking_indicators = (
            content_analysis["breaking_changes"] > 0
            or message_analysis["breaking_keywords"] > 0
            or any(
                change.is_api and change.change_type == "D" for change in file_changes
            )
        )

        if breaking_indicators:
            return ChangeType.MAJOR

        # Check for new features
        feature_indicators = (
            content_analysis["features"] > 0
            or message_analysis["feature_keywords"] > 0
            or message_analysis["conventional_commits"]["feat"] > 0
            or any(
                change.is_api and change.change_type == "A" for change in file_changes
            )
        )

        if feature_indicators:
            return ChangeType.MINOR

        # Check for bug fixes
        fix_indicators = (
            content_analysis["bug_fixes"] > 0
            or message_analysis["fix_keywords"] > 0
            or message_analysis["conventional_commits"]["fix"] > 0
            or any(
                change.is_api and change.change_type == "M" for change in file_changes
            )
        )

        if fix_indicators:
            return ChangeType.PATCH

        # Check if there are significant changes that don't warrant version bump
        significant_changes = any(change.is_config for change in file_changes) or any(
            change.is_api for change in file_changes
        )

        if significant_changes:
            return ChangeType.PATCH  # Default to patch for significant changes

        return ChangeType.NONE

    def generate_intelligent_analysis(self, commit_range: str) -> dict[str, Any]:
        """Perform comprehensive intelligent analysis."""

        # Gather all information
        file_changes = self.get_file_changes(commit_range)
        commit_messages = self.get_commit_messages(commit_range)
        content_analysis = self.analyze_content_changes(commit_range)
        message_analysis = self.analyze_commit_messages(commit_messages)

        # Determine version bump
        version_bump = self.determine_version_bump(
            file_changes, content_analysis, message_analysis
        )

        # Categorize changes
        categorized_changes = {
            "api_changes": [c for c in file_changes if c.is_api],
            "config_changes": [c for c in file_changes if c.is_config],
            "doc_changes": [c for c in file_changes if c.is_doc],
            "test_changes": [c for c in file_changes if c.is_test],
            "other_changes": [
                c
                for c in file_changes
                if not any([c.is_api, c.is_config, c.is_doc, c.is_test])
            ],
        }

        # Generate summary
        summary = self._generate_analysis_summary(
            file_changes, content_analysis, message_analysis, version_bump
        )

        return {
            "version_bump": version_bump.value,
            "analysis_type": "intelligent",
            "file_changes": {
                "total_files": len(file_changes),
                "files_added": len([c for c in file_changes if c.change_type == "A"]),
                "files_modified": len(
                    [c for c in file_changes if c.change_type == "M"]
                ),
                "files_deleted": len([c for c in file_changes if c.change_type == "D"]),
                "total_additions": sum(c.additions for c in file_changes),
                "total_deletions": sum(c.deletions for c in file_changes),
            },
            "content_analysis": content_analysis,
            "message_analysis": message_analysis,
            "categorized_changes": {
                category: [
                    {
                        "path": c.path,
                        "type": c.change_type,
                        "additions": c.additions,
                        "deletions": c.deletions,
                    }
                    for c in changes
                ]
                for category, changes in categorized_changes.items()
            },
            "summary": summary,
            "recommendations": self._generate_recommendations(
                file_changes, content_analysis, message_analysis, version_bump
            ),
        }

    def _generate_analysis_summary(
        self,
        file_changes: list[FileChange],
        content_analysis: dict[str, Any],
        message_analysis: dict[str, Any],
        version_bump: ChangeType,
    ) -> str:
        """Generate human-readable analysis summary."""

        summary_parts = []

        # Version bump recommendation
        if version_bump != ChangeType.NONE:
            summary_parts.append(f"Recommend {version_bump.value.upper()} version bump")
        else:
            summary_parts.append("No version bump required")

        # Change summary
        api_files = len([c for c in file_changes if c.is_api])
        if api_files > 0:
            summary_parts.append(f"{api_files} API file(s) changed")

        # Content findings
        if content_analysis["breaking_changes"] > 0:
            summary_parts.append(
                f"{content_analysis['breaking_changes']} potential breaking change(s)"
            )
        if content_analysis["features"] > 0:
            summary_parts.append(
                f"{content_analysis['features']} new feature(s) detected"
            )
        if content_analysis["bug_fixes"] > 0:
            summary_parts.append(
                f"{content_analysis['bug_fixes']} bug fix(es) detected"
            )

        return " | ".join(summary_parts)

    def _generate_recommendations(
        self,
        file_changes: list[FileChange],
        content_analysis: dict[str, Any],
        message_analysis: dict[str, Any],
        version_bump: ChangeType,
    ) -> list[str]:
        """Generate recommendations based on analysis."""
        recommendations = []

        if version_bump == ChangeType.MAJOR:
            recommendations.append(
                "⚠️  Breaking changes detected - consider API versioning"
            )
        elif version_bump == ChangeType.MINOR:
            recommendations.append("✨ New features detected - update documentation")
        elif version_bump == ChangeType.PATCH:
            recommendations.append("🐛 Bug fixes detected - consider adding tests")
        else:
            recommendations.append(
                "📝 Consider conventional commits for better tracking"
            )

        # API-specific recommendations
        api_changes = [c for c in file_changes if c.is_api]
        if api_changes:
            recommendations.append(
                f"🔧 {len(api_changes)} API file(s) modified - review impact"
            )

        # Message quality recommendations
        conventional_ratio = sum(
            message_analysis["conventional_commits"].values()
        ) / max(message_analysis["total_messages"], 1)
        if conventional_ratio < 0.5:
            recommendations.append("📋 Consider using conventional commit format")

        return recommendations


def main():
    parser = argparse.ArgumentParser(
        description="Intelligent commit analysis for version bumping"
    )
    parser.add_argument(
        "--range", required=True, help='Git commit range (e.g., "v1.0.0..HEAD")'
    )
    parser.add_argument("--output", required=True, help="Output JSON file")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    analyzer = IntelligentCommitAnalyzer()

    try:
        # Perform intelligent analysis
        analysis = analyzer.generate_intelligent_analysis(args.range)

        # Save analysis
        with open(args.output, "w") as f:
            json.dump(analysis, f, indent=2)

        if args.verbose:
            print("🤖 Intelligent Analysis Complete")
            print(f"📊 Version bump recommendation: {analysis['version_bump'].upper()}")
            print(f"📁 Files analyzed: {analysis['file_changes']['total_files']}")
            print(f"📝 Analysis saved to: {args.output}")

            # Show recommendations
            print("\n💡 Recommendations:")
            for rec in analysis["recommendations"]:
                print(f"  {rec}")

        return 0

    except Exception as e:
        print(f"Error during intelligent analysis: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
