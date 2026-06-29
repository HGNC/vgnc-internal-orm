#!/usr/bin/env python3
"""
Generate test summary from JUnit XML files for CI workflow.
This script parses test results from various test jobs and creates a markdown summary.
"""

import glob
import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def parse_junit_xml(file_path: str) -> tuple[int, int, int, int, list[str]]:
    """Parse JUnit XML file and return (tests, failures, errors, skipped, failed_tests)"""
    if not os.path.exists(file_path):
        return 0, 0, 0, 0, []

    try:
        tree = ET.parse(file_path)
        root = tree.getroot()

        total_tests = 0
        failures = 0
        errors = 0
        skipped = 0
        failed_tests = []

        # Handle both pytest and standard JUnit format
        for testcase in root.findall(".//testcase"):
            total_tests += 1

            failure = testcase.find("failure")
            error = testcase.find("error")
            skipped_elem = testcase.find("skipped")

            if failure is not None:
                failures += 1
                class_name = testcase.get("classname", "unknown")
                test_name = testcase.get("name", "unknown")
                failed_tests.append(f"{class_name}.{test_name}")
            elif error is not None:
                errors += 1
                class_name = testcase.get("classname", "unknown")
                test_name = testcase.get("name", "unknown")
                failed_tests.append(f"{class_name}.{test_name}")
            elif skipped_elem is not None:
                skipped += 1

        return total_tests, failures, errors, skipped, failed_tests

    except Exception as e:
        print(f"Error parsing {file_path}: {e}", file=sys.stderr)
        return 0, 0, 0, 0, []


def find_test_results() -> list[str]:
    """Find all test result XML files"""
    results_dir = Path("all-test-results")
    if not results_dir.exists():
        print("No test results directory found", file=sys.stderr)
        return []

    # Look for JUnit XML files
    xml_files = []
    for pattern in ["**/*.xml", "**/*-*.xml"]:
        xml_files.extend(glob.glob(str(results_dir / pattern), recursive=True))

    return sorted(xml_files)


def get_job_name_from_file(file_path: str) -> str:
    """Extract job name from file path"""
    # Extract job name from path like: all-test-results/test-results-3.13-unit/unit-3.13.xml
    parts = Path(file_path).parts
    for part in reversed(parts):
        if "unit" in part.lower():
            return "Unit Tests"
        elif "integration" in part.lower():
            return "Integration Tests"
        elif "performance" in part.lower():
            return "Performance Tests"
        elif "load" in part.lower():
            return "Load Tests"

    return "Unknown Tests"


def generate_summary() -> str:
    """Generate the test summary markdown"""
    xml_files = find_test_results()

    if not xml_files:
        return """# 🧪 Test Summary

**❌ No test results found**

Test results could not be found. This might indicate:
- Test execution failed
- Artifacts were not uploaded properly
- Test results directory structure has changed

Please check the individual job logs for details.
"""

    # Aggregate results by job type
    job_results: dict[str, dict] = {}
    total_tests = 0
    total_failures = 0
    total_errors = 0
    total_skipped = 0
    all_failed_tests = []

    for xml_file in xml_files:
        job_name = get_job_name_from_file(xml_file)
        tests, failures, errors, skipped, failed_tests = parse_junit_xml(xml_file)

        if job_name not in job_results:
            job_results[job_name] = {
                "tests": 0,
                "failures": 0,
                "errors": 0,
                "skipped": 0,
                "files": [],
            }

        job_results[job_name]["tests"] += tests
        job_results[job_name]["failures"] += failures
        job_results[job_name]["errors"] += errors
        job_results[job_name]["skipped"] += skipped
        job_results[job_name]["files"].append(xml_file)

        total_tests += tests
        total_failures += failures
        total_errors += errors
        total_skipped += skipped
        all_failed_tests.extend(failed_tests)

    # Generate summary
    summary_lines = ["# 🧪 Test Summary\n"]

    # Overall status
    if total_failures == 0 and total_errors == 0 and total_tests > 0:
        summary_lines.append("## ✅ Overall Status: PASSED")
    elif total_tests == 0:
        summary_lines.append("## ❌ Overall Status: NO TESTS EXECUTED")
    else:
        summary_lines.append("## ❌ Overall Status: FAILED")

    summary_lines.append("")

    # Summary table
    summary_lines.append("| Job | Tests | Failed | Errors | Skipped | Status |")
    summary_lines.append("|-----|-------|--------|--------|---------|--------|")

    for job_name, results in sorted(job_results.items()):
        status = (
            "✅ PASSED"
            if results["failures"] == 0 and results["errors"] == 0
            else "❌ FAILED"
        )
        summary_lines.append(
            f"| {job_name} | {results['tests']} | {results['failures']} | "
            f"{results['errors']} | {results['skipped']} | {status} |"
        )

    summary_lines.append("")

    # Overall totals
    summary_lines.append("## 📊 Overall Totals")
    summary_lines.append(f"- **Total Tests**: {total_tests}")
    summary_lines.append(f"- **Total Failures**: {total_failures}")
    summary_lines.append(f"- **Total Errors**: {total_errors}")
    summary_lines.append(f"- **Total Skipped**: {total_skipped}")
    summary_lines.append("")

    # Failed tests details
    if all_failed_tests:
        summary_lines.append("## ❌ Failed Tests")
        for failed_test in sorted(set(all_failed_tests)):
            summary_lines.append(f"- `{failed_test}`")
        summary_lines.append("")

    # Performance results (if available)
    perf_files = [
        f for f in xml_files if "performance" in f.lower() or "benchmark" in f.lower()
    ]
    if perf_files:
        summary_lines.append("## 🚀 Performance Tests")
        summary_lines.append(
            "Performance benchmarks were executed and results are available in the artifacts."
        )
        summary_lines.append("")

    # Load test results (if available)
    load_files = [f for f in xml_files if "load" in f.lower()]
    if load_files:
        summary_lines.append("## ⚡ Load Tests")
        summary_lines.append(
            "Load tests were executed and results are available in the artifacts."
        )
        summary_lines.append("")

    # Coverage information
    coverage_files = [f for f in xml_files if "coverage" in f.lower()]
    if coverage_files:
        summary_lines.append("## 📈 Code Coverage")
        summary_lines.append(
            "Coverage reports were generated and are available in the artifacts."
        )
        summary_lines.append("")

    return "\n".join(summary_lines)


if __name__ == "__main__":
    summary = generate_summary()
    print(summary)

    # Exit with error code if tests failed
    if "FAILED" in summary and "NO TESTS EXECUTED" not in summary:
        sys.exit(1)
    else:
        sys.exit(0)
