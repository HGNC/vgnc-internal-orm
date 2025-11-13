#!/usr/bin/env python3
"""Generate coverage badge."""

import json
import sys
from anybadge import Badge  # type: ignore[import-untyped]


def main():
    """Generate SVG coverage badge."""
    try:
        with open('./coverage-artifacts/coverage-combined.json') as f:
            data = json.load(f)
    except FileNotFoundError:
        # Try alternative path
        with open('coverage-combined.json') as f:
            data = json.load(f)

    coverage = data['totals']['percent_covered']

    # Determine color based on coverage percentage
    if coverage >= 90:
        color = 'green'
    elif coverage >= 80:
        color = 'yellow'
    elif coverage >= 70:
        color = 'orange'
    else:
        color = 'red'

    # Create badge
    badge = Badge(
        label='coverage',
        value=f'{coverage:.1f}%',
        default_color=color,
        num_value_padding=len(f'{coverage:.1f}%') + 1
    )

    # Write badge to file
    with open('coverage-badge.svg', 'w') as f:
        f.write(str(badge))

    print(f"Generated coverage badge: {coverage:.1f}% ({color})")


if __name__ == '__main__':
    main()
