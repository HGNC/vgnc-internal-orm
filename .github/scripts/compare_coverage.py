#!/usr/bin/env python3
"""Compare coverage with main branch."""

import json
import sys


def main():
    """Compare current PR coverage with main branch."""
    # Get current coverage
    with open("./coverage-artifacts/coverage.json") as f:
        current_data = json.load(f)

    current_coverage = current_data["totals"]["percent_covered"]
    print(f"Current PR coverage: {current_coverage:.1f}%")

    # Try to get main branch coverage (simplified approach)
    try:
        # This would require fetching main branch and running coverage there
        # For now, just show current coverage
        print("Coverage comparison with main branch not available in this setup")
    except Exception as e:
        print(f"Could not compare with main branch: {e}")

    # Set coverage status
    if current_coverage >= 80:
        print("✅ Coverage meets requirements (>= 80%)")
    else:
        print("❌ Coverage below requirements (< 80%)")
        sys.exit(1)


if __name__ == "__main__":
    main()
