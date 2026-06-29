#!/usr/bin/env python3
"""
Determine version bump type based on commit analysis following semantic versioning rules.
Follows semver.org specification: https://semver.org/
"""

import argparse
import json
import sys
from typing import Any


class VersionBumpDeterminer:
    """Determines version bump type based on commit analysis."""

    def __init__(self):
        # Priority order for version bumps (higher number = higher priority)
        self.BUMP_PRIORITY = {"major": 3, "minor": 2, "patch": 1, "none": 0}

    def determine_bump(self, analysis_data: dict[str, Any]) -> str:
        """
        Determine version bump based on enhanced commit analysis (conventional + intelligent).

        Rules (following semver.org with intelligent fallback):
        - MAJOR: Breaking changes (detected via conventional commits or code analysis)
        - MINOR: New features (detected via conventional commits or code analysis)
        - PATCH: Bug fixes (detected via conventional commits or code analysis)
        - NONE: No version-worthy changes
        """
        stats = analysis_data.get("stats", {})

        # Get conventional commit analysis
        breaking_changes = stats.get("breaking_changes", 0)
        features = stats.get("features", 0)
        fixes = stats.get("fixes", 0)

        conventional_commits = stats.get("conventional_commits", {})
        has_conventional = any(conventional_commits.values())

        # Check for intelligent analysis if available
        intelligent_analysis = analysis_data.get("intelligent_analysis", {})
        if intelligent_analysis:
            intelligent_features = intelligent_analysis["content_analysis"]["features"]
            intelligent_fixes = intelligent_analysis["content_analysis"]["bug_fixes"]
            intelligent_breaking = intelligent_analysis["content_analysis"][
                "breaking_changes"
            ]

            # Combine conventional and intelligent findings
            total_features = features + intelligent_features
            total_fixes = fixes + intelligent_fixes
            total_breaking = breaking_changes + intelligent_breaking

            # Use intelligent version bump if available
            if (
                intelligent_analysis.get("version_bump")
                and intelligent_analysis["version_bump"] != "none"
            ):
                return intelligent_analysis["version_bump"]
        else:
            # Use only conventional analysis
            total_features = features
            total_fixes = fixes
            total_breaking = breaking_changes

        # Determine bump based on semver rules
        if total_breaking > 0:
            return "major"
        elif total_features > 0:
            return "minor"
        elif total_fixes > 0:
            return "patch"
        elif has_conventional:
            # Has conventional commits but no features or fixes
            # Could be documentation, style, refactoring, etc.
            # These don't require version bumps according to semver
            return "none"
        else:
            # Check for API changes that might indicate a patch
            api_changes = stats.get("api_changes", 0)
            config_changes = stats.get("config_changes", 0)

            if api_changes > 0 or config_changes > 0:
                return "patch"  # Default to patch for significant changes

            return "none"

    def get_bump_reason(self, analysis_data: dict[str, Any], bump_type: str) -> str:
        """Get human-readable reason for the version bump."""
        stats = analysis_data.get("stats", {})
        categorized = analysis_data.get("categorized_commits", {})

        reasons = []

        if bump_type == "major":
            breaking_count = stats.get("breaking_changes", 0)
            if breaking_count > 0:
                reasons.append(f"Found {breaking_count} breaking change(s)")
                for breaking in categorized.get("breaking_changes", [])[
                    :3
                ]:  # Show first 3
                    reasons.append(f"  - {breaking['description']}")
                if len(categorized.get("breaking_changes", [])) > 3:
                    remaining = len(categorized["breaking_changes"]) - 3
                    reasons.append(f"  - ... and {remaining} more")

        elif bump_type == "minor":
            feature_count = stats.get("features", 0)
            if feature_count > 0:
                reasons.append(f"Found {feature_count} new feature(s)")
                for feature in categorized.get("features", [])[:5]:  # Show first 5
                    desc = feature["description"]
                    if feature["scope"]:
                        desc = f"({feature['scope']}) {desc}"
                    reasons.append(f"  - {desc}")
                if len(categorized.get("features", [])) > 5:
                    remaining = len(categorized["features"]) - 5
                    reasons.append(f"  - ... and {remaining} more")

        elif bump_type == "patch":
            fix_count = stats.get("fixes", 0)
            if fix_count > 0:
                reasons.append(f"Found {fix_count} bug fix(s)")
                for fix in categorized.get("fixes", [])[:5]:  # Show first 5
                    desc = fix["description"]
                    if fix["scope"]:
                        desc = f"({fix['scope']}) {desc}"
                    reasons.append(f"  - {desc}")
                if len(categorized.get("fixes", [])) > 5:
                    remaining = len(categorized["fixes"]) - 5
                    reasons.append(f"  - ... and {remaining} more")

        elif bump_type == "none":
            if not any(stats.get("conventional_commits", {}).values()):
                reasons.append("No conventional commits found")
            else:
                reasons.append(
                    "Only non-versionable changes (docs, style, refactoring, etc.)"
                )

        return "\n".join(reasons) if reasons else "No specific reason identified"

    def analyze_commit_types(self, analysis_data: dict[str, Any]) -> dict[str, Any]:
        """Analyze commit types for detailed reporting."""
        conventional_commits = analysis_data.get("stats", {}).get(
            "conventional_commits", {}
        )

        # Group commit types by their impact on versioning
        version_impacts = {
            "major_changes": [],
            "minor_changes": ["feat"],
            "patch_changes": ["fix"],
            "no_version_changes": [
                "docs",
                "style",
                "refactor",
                "perf",
                "test",
                "build",
                "ci",
                "chore",
                "revert",
            ],
        }

        impact_summary = {}
        for impact_type, commit_types in version_impacts.items():
            impact_summary[impact_type] = {
                "commit_types": commit_types,
                "count": sum(conventional_commits.get(ct, 0) for ct in commit_types),
                "commits": [],
            }

        # Add details for each commit type found
        for commit_type, count in conventional_commits.items():
            if count > 0:
                found_impact = None
                for impact_type, commit_types in version_impacts.items():
                    if commit_type in commit_types:
                        found_impact = impact_type
                        break

                if found_impact:
                    impact_summary[found_impact]["commits"].append(
                        {
                            "type": commit_type,
                            "count": count,
                            "description": self._get_commit_type_description(
                                commit_type
                            ),
                        }
                    )

        return impact_summary

    def _get_commit_type_description(self, commit_type: str) -> str:
        """Get description for a conventional commit type."""
        descriptions = {
            "feat": "New feature (backward compatible)",
            "fix": "Bug fix (backward compatible)",
            "docs": "Documentation changes only",
            "style": "Code style changes (formatting, etc.)",
            "refactor": "Code refactoring (no functional changes)",
            "perf": "Performance improvements",
            "test": "Test-related changes",
            "build": "Build system or dependency changes",
            "ci": "CI configuration changes",
            "chore": "Maintenance tasks (no user-facing changes)",
            "revert": "Revert previous changes",
        }
        return descriptions.get(commit_type, f"Unknown commit type: {commit_type}")


def main():
    parser = argparse.ArgumentParser(
        description="Determine version bump from commit analysis"
    )
    parser.add_argument("analysis_file", help="JSON file with commit analysis")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument(
        "--format", choices=["text", "json"], default="text", help="Output format"
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

    determiner = VersionBumpDeterminer()

    # Determine version bump
    bump_type = determiner.determine_bump(analysis_data)
    reason = determiner.get_bump_reason(analysis_data, bump_type)
    impact_analysis = determiner.analyze_commit_types(analysis_data)

    if args.format == "json":
        output = {
            "bump_type": bump_type,
            "reason": reason,
            "impact_analysis": impact_analysis,
            "summary": {
                "total_commits": analysis_data.get("stats", {}).get("total_commits", 0),
                "breaking_changes": analysis_data.get("stats", {}).get(
                    "breaking_changes", 0
                ),
                "features": analysis_data.get("stats", {}).get("features", 0),
                "fixes": analysis_data.get("stats", {}).get("fixes", 0),
                "has_conventional": any(
                    analysis_data.get("stats", {})
                    .get("conventional_commits", {})
                    .values()
                ),
            },
        }
        print(json.dumps(output, indent=2), file=sys.stderr)
    else:
        # Always output just the bump type (for workflow integration)
        print(bump_type)

        if args.verbose:
            print(f"Version bump: {bump_type.upper()}", file=sys.stderr)
            if reason:
                # Print reason to stderr to avoid interfering with workflow output
                for line in reason.split("\n"):
                    if line.strip():
                        print(f"Reason: {line}", file=sys.stderr)

            print("\n📊 Detailed Analysis:", file=sys.stderr)
            summary = analysis_data.get("summary", {})
            print(f"  Total commits: {summary.get('total', 0)}", file=sys.stderr)
            print(f"  Breaking changes: {summary.get('breaking', 0)}", file=sys.stderr)
            print(f"  Features: {summary.get('features', 0)}", file=sys.stderr)
            print(f"  Fixes: {summary.get('fixes', 0)}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
