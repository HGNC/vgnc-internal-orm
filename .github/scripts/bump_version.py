#!/usr/bin/env python3
"""
Bump semantic version numbers following semver.org specification.
Supports MAJOR.MINOR.PATCH format with validation.
"""

import argparse
import re
import sys


class VersionBumper:
    """Handles semantic version bumping operations."""

    # Semantic version pattern
    SEMVER_PATTERN = re.compile(
        r"^(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)"
        r"(?:-(?P<prerelease>(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)"
        r"(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
        r"(?:\+(?P<build>[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
    )

    def __init__(self):
        self.bump_functions = {
            "major": self._bump_major,
            "minor": self._bump_minor,
            "patch": self._bump_patch,
            "none": self._no_bump,
        }

    def parse_version(self, version: str) -> tuple[int, int, int]:
        """
        Parse semantic version string into (major, minor, patch) tuple.
        Raises ValueError if version is not valid semver.
        """
        match = self.SEMVER_PATTERN.match(version.strip())
        if not match:
            raise ValueError(f"Invalid semantic version: {version}")

        major = int(match.group("major"))
        minor = int(match.group("minor"))
        patch = int(match.group("patch"))

        return major, minor, patch

    def format_version(self, major: int, minor: int, patch: int) -> str:
        """Format version components into semver string."""
        return f"{major}.{minor}.{patch}"

    def _bump_major(self, major: int, minor: int, patch: int) -> tuple[int, int, int]:
        """Bump major version and reset minor and patch (semver rule)."""
        return major + 1, 0, 0

    def _bump_minor(self, major: int, minor: int, patch: int) -> tuple[int, int, int]:
        """Bump minor version and reset patch (semver rule)."""
        return major, minor + 1, 0

    def _bump_patch(self, major: int, minor: int, patch: int) -> tuple[int, int, int]:
        """Bump patch version."""
        return major, minor, patch + 1

    def _no_bump(self, major: int, minor: int, patch: int) -> tuple[int, int, int]:
        """No version bump."""
        return major, minor, patch

    def bump_version(self, current_version: str, bump_type: str) -> str:
        """
        Bump version according to semver rules.

        Args:
            current_version: Current semantic version string
            bump_type: Type of bump ('major', 'minor', 'patch', 'none')

        Returns:
            New semantic version string

        Raises:
            ValueError: If current_version is invalid or bump_type is unknown
        """
        if bump_type not in self.bump_functions:
            raise ValueError(
                f"Unknown bump type: {bump_type}. Must be one of: {list(self.bump_functions.keys())}"
            )

        try:
            major, minor, patch = self.parse_version(current_version)
        except ValueError as e:
            raise ValueError(
                f"Failed to parse current version '{current_version}': {e}"
            ) from e

        bump_function = self.bump_functions[bump_type]
        new_major, new_minor, new_patch = bump_function(major, minor, patch)

        return self.format_version(new_major, new_minor, new_patch)

    def validate_version(self, version: str) -> bool:
        """Check if version string is valid semantic version."""
        return bool(self.SEMVER_PATTERN.match(version.strip()))

    def get_version_info(self, version: str) -> dict:
        """Get detailed information about a semantic version."""
        match = self.SEMVER_PATTERN.match(version.strip())
        if not match:
            return {"valid": False, "error": "Invalid semantic version format"}

        info = {
            "valid": True,
            "major": int(match.group("major")),
            "minor": int(match.group("minor")),
            "patch": int(match.group("patch")),
            "prerelease": match.group("prerelease"),
            "build": match.group("build"),
        }

        # Determine if this is a development version (0.x.x)
        info["is_development"] = info["major"] == 0

        # Get version stability level
        if info["is_development"]:
            info["stability"] = "development"
        elif info["prerelease"]:
            info["stability"] = "pre-release"
        else:
            info["stability"] = "stable"

        return info

    def compare_versions(self, version1: str, version2: str) -> int:
        """
        Compare two semantic versions.

        Returns:
            -1 if version1 < version2
             0 if version1 == version2
             1 if version1 > version2
        """
        try:
            v1_major, v1_minor, v1_patch = self.parse_version(version1)
            v2_major, v2_minor, v2_patch = self.parse_version(version2)
        except ValueError as e:
            raise ValueError(f"Cannot compare versions: {e}") from e

        # Compare major version
        if v1_major < v2_major:
            return -1
        elif v1_major > v2_major:
            return 1

        # Compare minor version
        if v1_minor < v2_minor:
            return -1
        elif v1_minor > v2_minor:
            return 1

        # Compare patch version
        if v1_patch < v2_patch:
            return -1
        elif v1_patch > v2_patch:
            return 1

        # Versions are equal
        return 0


def main():
    parser = argparse.ArgumentParser(description="Bump semantic version numbers")
    parser.add_argument("--current", required=True, help="Current semantic version")
    parser.add_argument(
        "--bump",
        required=True,
        choices=["major", "minor", "patch", "none"],
        help="Type of version bump",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only validate the current version, don't bump",
    )
    parser.add_argument(
        "--info",
        action="store_true",
        help="Show detailed information about the version",
    )
    parser.add_argument(
        "--compare", help="Compare current version with another version"
    )

    args = parser.parse_args()

    bumper = VersionBumper()

    try:
        # Validate current version
        if not bumper.validate_version(args.current):
            print(
                f"Error: Invalid semantic version format: {args.current}",
                file=sys.stderr,
            )
            print("Expected format: MAJOR.MINOR.PATCH (e.g., 1.2.3)", file=sys.stderr)
            return 1

        if args.info:
            info = bumper.get_version_info(args.current)
            print(f"Version: {args.current}")
            print(f"Valid: {info['valid']}")
            print(f"Major: {info['major']}")
            print(f"Minor: {info['minor']}")
            print(f"Patch: {info['patch']}")
            if info["prerelease"]:
                print(f"Prerelease: {info['prerelease']}")
            if info["build"]:
                print(f"Build: {info['build']}")
            print(f"Stability: {info['stability']}")
            if info["is_development"]:
                print("Note: This is a development version (0.x.x)")

        if args.compare:
            comparison = bumper.compare_versions(args.current, args.compare)
            if comparison < 0:
                print(f"{args.current} < {args.compare}")
            elif comparison > 0:
                print(f"{args.current} > {args.compare}")
            else:
                print(f"{args.current} == {args.compare}")

        if args.validate_only:
            print(f"✅ Version {args.current} is valid")
            return 0

        # Bump version
        new_version = bumper.bump_version(args.current, args.bump)
        print(new_version)

        if args.bump != "none":
            # Show what changed
            print(f"  {args.current} -> {new_version}", file=sys.stderr)

            if args.bump == "major":
                print(
                    "  Breaking change detected (major version bump)", file=sys.stderr
                )
            elif args.bump == "minor":
                print("  New feature added (minor version bump)", file=sys.stderr)
            elif args.bump == "patch":
                print("  Bug fix applied (patch version bump)", file=sys.stderr)

    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
