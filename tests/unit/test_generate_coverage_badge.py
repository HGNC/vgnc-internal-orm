"""Tests for the coverage badge generator.

These exercise the badge script against a realistic coverage.json fixture
(skipped if `anybadge` is not installed) and assert the produced SVG plus the
chosen color map sensibly to the coverage percentage.
"""

import json
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = (Path(__file__).resolve().parents[2] / ".github" / "scripts").resolve()
sys.path.insert(0, str(SCRIPTS_DIR))

anybadge = pytest.importorskip("anybadge")  # skip whole module if anybadge missing
import generate_coverage_badge  # noqa: E402  (must follow path setup + importorskip)


@pytest.fixture()
def coverage_json(tmp_path: Path) -> Path:
    """Write a realistic coverage.json and return its path."""
    data = {
        "meta": {"version": "7.4.4"},
        "files": {},
        "totals": {
            "covered_lines": 80,
            "num_statements": 100,
            "percent_covered": 80.0,
            "percent_covered_display": "80",
            "missing_lines": 20,
            "excluded_lines": 0,
        },
    }
    path = tmp_path / "coverage.json"
    path.write_text(json.dumps(data))
    return path


class TestColorThresholds:
    def test_thresholds_are_ascending_and_cover_full_range(self):
        """The color map must be keyed by ascending coverage and span low->high."""
        t = generate_coverage_badge.COVERAGE_THRESHOLDS
        keys = list(t.keys())
        assert keys == sorted(keys), "threshold keys must be ascending"
        # Lowest bucket must be a clearly-failing value, highest a clearly-good one
        assert t[keys[0]] == "red"
        assert t[keys[-1]] == "green"

    def test_color_for_low_coverage_is_red(self):
        assert generate_coverage_badge.color_for(50.0) == "red"

    def test_color_for_high_coverage_is_green(self):
        assert generate_coverage_badge.color_for(96.0) == "green"


class TestReadCoverage:
    def test_reads_percent_covered_from_coverage_json(self, coverage_json):
        pct = generate_coverage_badge.read_coverage(coverage_json)
        assert pct == pytest.approx(80.0)

    def test_missing_file_raises_filenotfound(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            generate_coverage_badge.read_coverage(tmp_path / "nope.json")


class TestGenerateBadge:
    def test_writes_svg_with_percentage_value(
        self, coverage_json, tmp_path, monkeypatch
    ):
        out = tmp_path / "coverage-badge.svg"
        svg = generate_coverage_badge.generate_badge(coverage_json, out_path=out)
        text = svg.badge_svg_text
        assert "<svg" in text
        assert "80" in text  # the percentage appears in the badge
        # File was written
        assert out.exists()
        assert out.read_text() == text

    def test_returns_chosen_color(self, coverage_json, tmp_path):
        svg = generate_coverage_badge.generate_badge(
            coverage_json, out_path=tmp_path / "x.svg"
        )
        # 80.0 falls in the coverage bands; any valid color string is acceptable
        assert isinstance(svg.badge_color, str)
        assert svg.badge_color in generate_coverage_badge.COVERAGE_THRESHOLDS.values()
