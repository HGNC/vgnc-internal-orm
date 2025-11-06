#!/usr/bin/env python3
"""Generate coverage badge."""

import json
from coverage_badge import main as badge_main


def main():
    """Generate SVG coverage badge."""
    with open('./coverage-artifacts/coverage-combined.json') as f:
        data = json.load(f)

    coverage = data['totals']['percent_covered']
    badge_main([
        '-o', 'coverage-badge.svg',
        '-f', str(coverage),
        '--threshold=80',
        'coverage'
    ])


if __name__ == '__main__':
    main()
