#!/usr/bin/env python3
"""Generate coverage badge."""

import json

from anybadge import Badge  # type: ignore[import-untyped]


def main():
    """Generate SVG coverage badge."""
    try:
        with open("./coverage-artifacts/coverage-combined.json") as f:
            data = json.load(f)
    except FileNotFoundError:
        # Try alternative path
        with open("coverage-combined.json") as f:
            data = json.load(f)

    coverage = data["totals"]["percent_covered"]

    # Define color thresholds for coverage
    thresholds = {70: "red", 80: "orange", 90: "yellow", 95: "green"}

    # Create badge with automatic color selection based on thresholds
    badge = Badge(label="coverage", value=f"{coverage:.1f}%", thresholds=thresholds)

    # Write badge to file
    with open("coverage-badge.svg", "w") as f:
        f.write(str(badge))

    print(f"Generated coverage badge: {coverage:.1f}%")
    # Determine actual color for logging
    actual_color = "red"
    for threshold, color in sorted(thresholds.items(), reverse=True):
        if coverage >= threshold:
            actual_color = color
            break
    print(f"Badge color: {actual_color}")


if __name__ == "__main__":
    main()
