#!/usr/bin/env python3
"""Generate an SVG coverage badge from a coverage.json report.

Reads ``coverage.json`` (produced by ``coverage json``) and writes an SVG
badge whose color is chosen by coverage thresholds:

    < 70 %  -> red
    < 80 %  -> orange
    < 90 %  -> yellow
    >= 95 % -> green

Designed to run in CI after the coverage report step. Requires the
``anybadge`` package (in the ``dev`` dependency group).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from anybadge import Badge

# Ascending coverage -> color. anybadge picks the color of the *highest*
# threshold key that is <= the value, so we express each bucket by its
# minimum passing percentage.
COVERAGE_THRESHOLDS: dict[int, str] = {
    0: "red",
    70: "orange",
    80: "yellow",
    90: "green",
}


def color_for(coverage: float) -> str:
    """Return the badge color for a given coverage percentage."""
    chosen = COVERAGE_THRESHOLDS[0]
    for threshold, color in COVERAGE_THRESHOLDS.items():
        if coverage >= threshold:
            chosen = color
    return chosen


def read_coverage(path: Path) -> float:
    """Read ``totals.percent_covered`` from a coverage.json report.

    Raises:
        FileNotFoundError: if the report does not exist.
        KeyError: if the report is missing ``totals.percent_covered``.
    """
    data = json.loads(Path(path).read_text())
    return float(data["totals"]["percent_covered"])


def generate_badge(coverage_path: Path, out_path: Path | None = None) -> Badge:
    """Build a coverage Badge from a coverage.json report.

    Args:
        coverage_path: Path to coverage.json.
        out_path: Optional path to write the SVG. If given, the file is
            overwritten if it already exists.

    Returns:
        The anybadge Badge object (also exposes ``badge_svg_text`` and
        ``badge_color``).
    """
    coverage = read_coverage(coverage_path)
    badge = Badge(
        label="coverage",
        value=f"{coverage:.1f}",
        value_suffix="%",
        thresholds=COVERAGE_THRESHOLDS,
    )
    if out_path is not None:
        badge.write_badge(Path(out_path), overwrite=True)
    return badge


def main() -> int:
    """CLI entry point: read coverage.json, write coverage-badge.svg."""
    # Prefer coverage.json in the repo root; allow an override via argv.
    coverage_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("coverage.json")
    out_path = Path("coverage-badge.svg")

    coverage = read_coverage(coverage_path)
    badge = generate_badge(coverage_path, out_path=out_path)

    print(f"Generated coverage badge: {coverage:.1f}%")
    print(f"Badge color: {badge.badge_color}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
