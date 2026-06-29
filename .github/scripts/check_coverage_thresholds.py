#!/usr/bin/env python3
"""Check coverage thresholds."""

import json
import sys


def main():
    """Check if coverage meets minimum thresholds."""
    with open("coverage-combined.json") as f:
        data = json.load(f)

    coverage_pct = data["totals"]["percent_covered"]

    # Define thresholds
    MIN_COVERAGE = 75.0
    WARNING_THRESHOLD = 80.0
    GOOD_THRESHOLD = 90.0

    print(f"Current coverage: {coverage_pct:.1f}%")

    if coverage_pct < MIN_COVERAGE:
        print(f"❌ Coverage below minimum threshold ({MIN_COVERAGE}%)")
        sys.exit(1)
    elif coverage_pct < WARNING_THRESHOLD:
        print(f"⚠️ Coverage below warning threshold ({WARNING_THRESHOLD}%)")
    elif coverage_pct < GOOD_THRESHOLD:
        print("✅ Coverage meets minimum requirements")
    else:
        print(f"🎉 Excellent coverage ({coverage_pct:.1f}% >= {GOOD_THRESHOLD}%)")


if __name__ == "__main__":
    main()
