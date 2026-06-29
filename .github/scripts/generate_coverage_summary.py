#!/usr/bin/env python3
"""Generate coverage summary for GitHub Actions."""

import json


def main():
    """Generate coverage summary."""
    with open("coverage-combined.json") as f:
        data = json.load(f)

    totals = data["totals"]
    lines_covered = totals["covered_lines"]
    lines_missing = totals["missing_lines"]
    total_lines = totals["num_statements"]
    coverage_pct = totals["percent_covered"]
    branches_covered = totals.get("covered_branches", 0)
    branches_missing = totals.get("missing_branches", 0)
    total_branches = totals.get("num_branches", 0)
    branch_coverage_pct = totals.get("percent_covered_display", "0.0")

    print("## Coverage Summary")
    print("")
    print(f"**Lines Coverage:** {coverage_pct}% ({lines_covered}/{total_lines})")
    print(f"**Lines Missing:** {lines_missing}")
    if total_branches > 0:
        print(
            f"**Branch Coverage:** {branch_coverage_pct}% ({branches_covered}/{total_branches})"
        )
        print(f"**Branches Missing:** {branches_missing}")
    print("")
    print("### Coverage by Module")
    for filename, file_data in data["files"].items():
        if "src/vgnc_internal_orm" in filename:
            module_name = filename.replace(
                "src/vgnc_internal_orm/", "vgnc_internal_orm."
            )
            file_pct = file_data["summary"]["percent_covered"]
            file_covered = file_data["summary"]["covered_lines"]
            file_total = file_data["summary"]["num_statements"]
            print(f"- **{module_name}**: {file_pct}% ({file_covered}/{file_total})")


if __name__ == "__main__":
    main()
