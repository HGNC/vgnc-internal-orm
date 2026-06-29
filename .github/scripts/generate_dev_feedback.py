#!/usr/bin/env python3
"""Generate development workflow feedback."""

import json
from pathlib import Path


def main():
    """Generate development feedback markdown."""
    feedback = []

    # Check if coverage report exists
    coverage_file = Path("dev-results/coverage.xml")
    if coverage_file.exists():
        try:
            import xml.etree.ElementTree as ET

            tree = ET.parse(coverage_file)
            root = tree.getroot()
            coverage = root.get("line-rate", "0")
            coverage_pct = float(coverage) * 100
            feedback.append(f"📊 Code Coverage: {coverage_pct:.1f}%")
            if coverage_pct >= 70:
                feedback.append("✅ Coverage meets minimum requirement (≥70%)")
            else:
                feedback.append("⚠️ Coverage below minimum requirement (<70%)")
        except Exception:
            feedback.append("❌ Could not parse coverage report")
    else:
        feedback.append("❌ No coverage report found")

    # Check if security report exists (if quality checks ran)
    security_file = Path("dev-results/security-report.json")
    if security_file.exists():
        try:
            with open(security_file) as f:
                security_data = json.load(f)
            high_issues = len(
                [
                    r
                    for r in security_data.get("results", [])
                    if r.get("issue_severity") == "HIGH"
                ]
            )
            medium_issues = len(
                [
                    r
                    for r in security_data.get("results", [])
                    if r.get("issue_severity") == "MEDIUM"
                ]
            )

            if high_issues == 0 and medium_issues == 0:
                feedback.append("🔒 Security: No critical issues found")
            else:
                feedback.append(
                    f"🔒 Security: {high_issues} high, {medium_issues} medium issues found"
                )
        except Exception:
            feedback.append("❌ Could not parse security report")

    # Generate summary
    print("## 🚀 Development Workflow Results\\n")
    for item in feedback:
        print(f"- {item}")

    print("\\n### 📋 Recommendations")
    if "Coverage meets minimum" not in " ".join(feedback):
        print("- Add more unit tests to improve code coverage")
    if "high, " in " ".join(feedback):
        print("- Address high-priority security issues")
    if "Formatting issues" in " ".join(feedback):
        print("- Run `black src/ tests/` to fix formatting")
    if "Import sorting issues" in " ".join(feedback):
        print("- Run `isort src/ tests/` to fix import sorting")
    if "Linting issues" in " ".join(feedback):
        print("- Fix linting issues reported by flake8")

    print("\\n### 🔧 Local Development Commands")
    print("```bash")
    print("# Run all tests locally")
    print("python -m pytest tests/unit/ tests/integration/")
    print("")
    print("# Run with coverage")
    print("python -m pytest tests/ --cov=src/vgnc_internal_orm --cov-report=html")
    print("")
    print("# Run quality checks")
    print("black src/ tests/")
    print("isort src/ tests/")
    print("flake8 src/ tests/")
    print("bandit -r src/")
    print("```")


if __name__ == "__main__":
    main()
