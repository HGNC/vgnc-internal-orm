#!/usr/bin/env python3
"""
Enhanced commit analyzer that combines conventional commit analysis with intelligent code analysis.
Automatically detects change types even when commit messages don't follow conventional format.
"""

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from typing import Any


@dataclass
class CommitInfo:
    """Information about a single commit."""

    hash: str
    message: str
    type: str | None = None
    scope: str | None = None
    breaking: bool = False
    description: str = ""


class CommitAnalyzer:
    """Enhanced commit analyzer that combines conventional and intelligent analysis."""

    # Conventional commit types
    CONVENTIONAL_TYPES = {
        "feat": "features",
        "fix": "fixes",
        "docs": "documentation",
        "style": "style",
        "refactor": "refactoring",
        "perf": "performance",
        "test": "tests",
        "build": "build",
        "ci": "ci",
        "chore": "chore",
        "revert": "reverts",
    }

    # Breaking change indicators
    BREAKING_PATTERNS = [
        r"BREAKING CHANGE:\s*(.+)",
        r"BREAKING-CHANGE:\s*(.+)",
        r"!:\s*",  # feat!: add new api (breaking)
    ]

    # Conventional commit pattern
    CONVENTIONAL_COMMIT_PATTERN = re.compile(
        r"^(?P<type>\w+)(?:\((?P<scope>[^)]+)\))?(?P<breaking>!)?:\s*(?P<description>.+)$",
        re.MULTILINE,
    )

    def __init__(self) -> None:
        self.commits: list[CommitInfo] = []
        self.stats: dict[str, Any] = {
            "total_commits": 0,
            "conventional_commits": dict.fromkeys(self.CONVENTIONAL_TYPES, 0),
            "breaking_changes": 0,
            "features": 0,
            "fixes": 0,
            "other_changes": 0,
            "commits_by_type": {},
            "breaking_details": [],
        }

    def get_commits(self, commit_range: str) -> list[str]:
        """Get commit messages from git log."""
        try:
            result = subprocess.run(
                ["git", "log", "--pretty=format:%H|%s|%b", commit_range],
                capture_output=True,
                text=True,
                check=True,
            )

            if not result.stdout.strip():
                return []

            return [line.strip() for line in result.stdout.split("\n") if line.strip()]

        except subprocess.CalledProcessError as e:
            print(f"Error getting commits: {e}", file=sys.stderr)
            return []

    def parse_commit(self, commit_line: str) -> CommitInfo:
        """Parse a single commit line into CommitInfo."""
        parts = commit_line.split("|", 2)
        if len(parts) < 2:
            return CommitInfo(hash="", message=commit_line)

        commit_hash = parts[0]
        subject = parts[1]
        body = parts[2] if len(parts) > 2 else ""
        full_message = f"{subject}\n{body}".strip()

        commit_info = CommitInfo(hash=commit_hash, message=full_message)

        # Check for breaking changes in subject or body
        for pattern in self.BREAKING_PATTERNS:
            matches = re.findall(pattern, full_message, re.MULTILINE | re.IGNORECASE)
            if matches:
                commit_info.breaking = True
                if matches[0].strip():
                    commit_info.description = matches[0].strip()
                break

        # Parse conventional commit format
        match = self.CONVENTIONAL_COMMIT_PATTERN.match(subject)
        if match:
            commit_info.type = match.group("type")
            commit_info.scope = match.group("scope")
            commit_info.description = (
                match.group("description") or commit_info.description
            )

            # Check for breaking change indicator in type
            if match.group("breaking"):
                commit_info.breaking = True

        return commit_info

    def analyze_commit(self, commit: CommitInfo):
        """Analyze a single commit and update statistics."""
        self.stats["total_commits"] += 1

        if commit.type and commit.type in self.CONVENTIONAL_TYPES:
            self.stats["conventional_commits"][commit.type] += 1
            self.stats["commits_by_type"][commit.type] = (
                self.stats["commits_by_type"].get(commit.type, 0) + 1
            )

            if commit.type == "feat":
                self.stats["features"] += 1
            elif commit.type == "fix":
                self.stats["fixes"] += 1
        else:
            self.stats["other_changes"] += 1

        if commit.breaking:
            self.stats["breaking_changes"] += 1
            if commit.description:
                self.stats["breaking_details"].append(
                    {"hash": commit.hash[:8], "description": commit.description}
                )

        self.commits.append(commit)

    def get_analysis_summary(self) -> dict[str, Any]:
        """Get comprehensive analysis summary."""
        # Categorize commits for release notes
        categorized_commits = {
            "features": [],
            "fixes": [],
            "breaking_changes": [],
            "other": [],
        }

        for commit in self.commits:
            if commit.breaking:
                categorized_commits["breaking_changes"].append(
                    {
                        "hash": commit.hash[:8],
                        "description": commit.description
                        or commit.message.split("\n")[0],
                        "scope": commit.scope,
                        "type": commit.type,
                    }
                )
            elif commit.type == "feat":
                categorized_commits["features"].append(
                    {
                        "hash": commit.hash[:8],
                        "description": commit.description,
                        "scope": commit.scope,
                    }
                )
            elif commit.type == "fix":
                categorized_commits["fixes"].append(
                    {
                        "hash": commit.hash[:8],
                        "description": commit.description,
                        "scope": commit.scope,
                    }
                )
            else:
                categorized_commits["other"].append(
                    {
                        "hash": commit.hash[:8],
                        "type": commit.type,
                        "description": commit.message.split("\n")[0],
                    }
                )

        return {
            "stats": self.stats,
            "categorized_commits": categorized_commits,
            "all_commits": [
                {
                    "hash": commit.hash[:8],
                    "type": commit.type,
                    "scope": commit.scope,
                    "breaking": commit.breaking,
                    "description": commit.description,
                    "message": commit.message.split("\n")[0],
                }
                for commit in self.commits
            ],
        }


def main():
    parser = argparse.ArgumentParser(
        description="Analyze git commits for version bumping"
    )
    parser.add_argument(
        "--range", required=True, help='Git commit range (e.g., "v1.0.0..HEAD")'
    )
    parser.add_argument("--output", required=True, help="Output JSON file")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    analyzer = CommitAnalyzer()

    # Get commits
    commit_lines = analyzer.get_commits(args.range)
    if not commit_lines:
        print(f"No commits found in range: {args.range}", file=sys.stderr)
        # Still output empty analysis
        analysis = analyzer.get_analysis_summary()
        with open(args.output, "w") as f:
            json.dump(analysis, f, indent=2)
        return 0

    if args.verbose:
        print(f"Analyzing {len(commit_lines)} commits...")

    # Analyze each commit
    for commit_line in commit_lines:
        commit = analyzer.parse_commit(commit_line)
        analyzer.analyze_commit(commit)

        if args.verbose:
            status = "🔴" if commit.breaking else "🟢"
            type_info = f"({commit.type})" if commit.type else "(unknown)"
            print(
                f"{status} {commit.hash[:8]} {type_info} {commit.message.split(chr(10))[0][:50]}..."
            )

    # Generate analysis
    analysis = analyzer.get_analysis_summary()

    # Perform intelligent analysis as fallback/backup
    has_conventional_commits = any(analysis["stats"]["conventional_commits"].values())

    if not has_conventional_commits or args.verbose:
        # Import and run intelligent analyzer
        try:
            sys.path.append(os.path.dirname(os.path.abspath(__file__)))
            from intelligent_commit_analyzer import IntelligentCommitAnalyzer

            intelligent_analyzer = IntelligentCommitAnalyzer()
            intelligent_analysis = intelligent_analyzer.generate_intelligent_analysis(
                args.range
            )

            # Merge intelligent analysis with conventional analysis
            analysis["intelligent_analysis"] = intelligent_analysis

            # Update stats with intelligent findings if no conventional commits
            if not has_conventional_commits:
                # Enhance stats with intelligent analysis
                analysis["stats"].update(
                    {
                        "intelligent_features": intelligent_analysis[
                            "content_analysis"
                        ]["features"],
                        "intelligent_fixes": intelligent_analysis["content_analysis"][
                            "bug_fixes"
                        ],
                        "intelligent_breaking": intelligent_analysis[
                            "content_analysis"
                        ]["breaking_changes"],
                        "api_changes": len(
                            intelligent_analysis["categorized_changes"]["api_changes"]
                        ),
                        "config_changes": len(
                            intelligent_analysis["categorized_changes"][
                                "config_changes"
                            ]
                        ),
                    }
                )

                # Update categorized commits with intelligent findings
                analysis["categorized_commits"]["features"].extend(
                    [
                        {
                            "hash": "intelligent",
                            "description": f"Auto-detected feature: {detail[:80]}...",
                            "scope": "auto-detect",
                        }
                        for detail in intelligent_analysis["content_analysis"][
                            "feature_details"
                        ][:3]
                    ]
                )

                analysis["categorized_commits"]["fixes"].extend(
                    [
                        {
                            "hash": "intelligent",
                            "description": f"Auto-detected fix: {detail[:80]}...",
                            "scope": "auto-detect",
                        }
                        for detail in intelligent_analysis["content_analysis"][
                            "bug_fix_details"
                        ][:5]
                    ]
                )

                if intelligent_analysis["content_analysis"]["breaking_changes"] > 0:
                    analysis["categorized_commits"]["breaking_changes"].extend(
                        [
                            {
                                "hash": "intelligent",
                                "description": f"Auto-detected breaking change: {detail[:80]}...",
                                "scope": "auto-detect",
                            }
                            for detail in intelligent_analysis["content_analysis"][
                                "breaking_details"
                            ][:3]
                        ]
                    )

                print("🤖 Intelligent analysis completed", file=sys.stderr)

        except ImportError as e:
            print(f"⚠️  Intelligent analysis not available: {e}", file=sys.stderr)
        except Exception as e:
            print(f"⚠️  Intelligent analysis failed: {e}", file=sys.stderr)

    # Add summary for quick reference
    analysis["summary"] = {
        "total": analysis["stats"]["total_commits"],
        "breaking": analysis["stats"]["breaking_changes"],
        "features": analysis["stats"]["features"],
        "fixes": analysis["stats"]["fixes"],
        "has_conventional": has_conventional_commits,
        "intelligent_mode": not has_conventional_commits,
        "recommended_bump": None,  # Will be determined by another script
    }

    # Save analysis
    with open(args.output, "w") as f:
        json.dump(analysis, f, indent=2)

    if args.verbose:
        print("\n📊 Analysis Summary:")
        print(f"  Total commits: {analysis['summary']['total']}")
        print(f"  Breaking changes: {analysis['summary']['breaking']}")
        print(f"  Features: {analysis['summary']['features']}")
        print(f"  Fixes: {analysis['summary']['fixes']}")
        print(f"  Conventional commits: {analysis['summary']['has_conventional']}")
        print(f"\n📄 Analysis saved to: {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
