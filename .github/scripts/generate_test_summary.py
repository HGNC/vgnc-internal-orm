#!/usr/bin/env python3
"""Generate test summary from JUnit XML files."""

import json
import os
import glob
from pathlib import Path


def parse_junit_xml(xml_file):
    """Parse JUnit XML file and extract test counts."""
    try:
        import xml.etree.ElementTree as ET
        tree = ET.parse(xml_file)
        root = tree.getroot()

        tests = int(root.get('tests', 0))
        failures = int(root.get('failures', 0))
        errors = int(root.get('errors', 0))
        skipped = int(root.get('skipped', 0))

        return tests, failures, errors, skipped
    except Exception as e:
        print(f'Error parsing {xml_file}: {e}')
        return 0, 0, 0, 0


def main():
    """Generate test summary markdown."""
    total_tests = 0
    total_failures = 0
    total_errors = 0
    total_skipped = 0

    print('## 🧪 Test Results Summary\\n')

    # Process unit test results
    unit_files = glob.glob('all-test-results/**/unit-*.xml', recursive=True)
    if unit_files:
        print('### Unit Tests')
        for file in unit_files:
            tests, failures, errors, skipped = parse_junit_xml(file)
            total_tests += tests
            total_failures += failures
            total_errors += errors
            total_skipped += skipped
            status = '✅' if failures == 0 and errors == 0 else '❌'
            print(f'{status} {Path(file).name}: {tests} tests, {failures} failures, {errors} errors, {skipped} skipped')
        print()

    # Process integration test results
    integration_files = glob.glob('all-test-results/**/integration-*.xml', recursive=True)
    if integration_files:
        print('### Integration Tests')
        for file in integration_files:
            tests, failures, errors, skipped = parse_junit_xml(file)
            total_tests += tests
            total_failures += failures
            total_errors += errors
            total_skipped += skipped
            status = '✅' if failures == 0 and errors == 0 else '❌'
            print(f'{status} {Path(file).name}: {tests} tests, {failures} failures, {errors} errors, {skipped} skipped')
        print()

    # Overall summary
    print('### 📊 Overall Summary')
    success_rate = ((total_tests - total_failures - total_errors) / total_tests * 100) if total_tests > 0 else 0
    print(f'- **Total Tests:** {total_tests}')
    print(f'- **Passed:** {total_tests - total_failures - total_errors}')
    print(f'- **Failed:** {total_failures}')
    print(f'- **Errors:** {total_errors}')
    print(f'- **Skipped:** {total_skipped}')
    print(f'- **Success Rate:** {success_rate:.1f}%')

    if total_failures > 0 or total_errors > 0:
        print('\\n❌ Some tests failed!')
        exit(1)
    else:
        print('\\n✅ All tests passed!')


if __name__ == '__main__':
    main()
