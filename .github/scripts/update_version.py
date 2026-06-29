#!/usr/bin/env python3
"""
Update version in pyproject.toml file.
Handles proper TOML formatting and preserves file structure.
"""

import argparse
import re
import sys
from pathlib import Path


def update_pyproject_version(file_path: str, new_version: str) -> bool:
    """
    Update version in pyproject.toml file.

    Args:
        file_path: Path to pyproject.toml
        new_version: New version string to set

    Returns:
        True if successful, False otherwise
    """
    try:
        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            print(f"Error: File not found: {file_path}", file=sys.stderr)
            return False

        # Read the file
        content = file_path_obj.read_text(encoding="utf-8")

        # Update version using regex to maintain TOML formatting
        # Look for version = "x.x.x" in [project] section
        version_pattern = r'^(version\s*=\s*")[^"]*(")'

        # Check if we found a version in the project section
        if not re.search(version_pattern, content, re.MULTILINE):
            # Try to find any version line
            any_version_pattern = r'^version\s*=\s*"[^"]*"'
            if not re.search(any_version_pattern, content, re.MULTILINE):
                print(
                    "Error: No version field found in pyproject.toml", file=sys.stderr
                )
                return False

        # Replace the version
        updated_content = re.sub(
            version_pattern,
            rf"\g<1>{new_version}\g<2>",
            content,
            count=1,
            flags=re.MULTILINE,
        )

        # Verify the change was made
        if updated_content == content:
            print(
                "Error: Version was not updated - pattern may not have matched",
                file=sys.stderr,
            )
            return False

        # Write back to file
        file_path_obj.write_text(updated_content, encoding="utf-8")

        print(f"✅ Updated version to {new_version} in {file_path}")
        return True

    except Exception as e:
        print(f"Error updating version: {e}", file=sys.stderr)
        return False


def verify_version_update(file_path: str, expected_version: str) -> bool:
    """
    Verify that the version was updated correctly.

    Args:
        file_path: Path to pyproject.toml
        expected_version: Expected version string

    Returns:
        True if version matches expected, False otherwise
    """
    try:
        file_path_obj = Path(file_path)
        content = file_path_obj.read_text(encoding="utf-8")

        # Extract version
        version_match = re.search(r'version\s*=\s*"([^"]*)"', content)
        if not version_match:
            print("Error: Could not find version field after update", file=sys.stderr)
            return False

        actual_version = version_match.group(1)
        if actual_version != expected_version:
            print(
                f"Error: Version mismatch after update. Expected: {expected_version}, Got: {actual_version}",
                file=sys.stderr,
            )
            return False

        return True

    except Exception as e:
        print(f"Error verifying version update: {e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(description="Update version in pyproject.toml")
    parser.add_argument("--version", required=True, help="New version to set")
    parser.add_argument(
        "--file", default="pyproject.toml", help="pyproject.toml file path"
    )
    parser.add_argument(
        "--verify", action="store_true", help="Verify the update after making it"
    )

    args = parser.parse_args()

    # Check if version is empty
    if not args.version or args.version.strip() == "":
        print("Error: Version is empty", file=sys.stderr)
        print("A valid version must be provided", file=sys.stderr)
        return 1

    # Validate version format (basic semver check)
    version_pattern = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)")
    if not version_pattern.match(args.version.strip()):
        print(
            f"Error: Invalid semantic version format: {args.version}", file=sys.stderr
        )
        print("Expected format: MAJOR.MINOR.PATCH (e.g., 1.2.3)", file=sys.stderr)
        return 1

    # Use stripped version for safety
    version = args.version.strip()

    # Update version
    success = update_pyproject_version(args.file, version)
    if not success:
        return 1

    # Verify if requested
    if args.verify:
        if not verify_version_update(args.file, args.version):
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
