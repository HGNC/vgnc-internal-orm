# CHANGELOG

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

# Release v0.3.0

**Released:** 2025-11-14
**From:** v0.2.0

---

## New Features

- add version reference updater script and integrate into release workflow fix: update .gitignore to exclude temporary GitHub Actions files fix: enhance type hints in commit info class and constructor (bc7b0af2)
- add intelligent commit analysis for automatic version detection (13344682)

## Bug Fixes

- validate new version before release and ensure proper version handling (34e8195c)
- enhance version calculation logic to handle no bumps and validate new version (180e5497)
- improve intelligent analysis accuracy and reduce false positives (2fd49848)
- properly handle dry-run mode in semantic release workflow (516057dd)
- resolve string comparison issues in release notes generation (d5d2bdef)
- resolve workflow issues with version analysis and release notes (ce66aabe)
- resolve GitHub Actions output format issue in version bump script (a4f31960)

## Chores

- chore: update file permissions for script files to executable (d2e2922f)
- chore: add automated semantic versioning and release system (d83460d1)

---

## 📊 Release Statistics

- **Total commits:** 69
- **Conventional commits:** 11
- **New features:** 2
- **Bug fixes:** 7

**Version bump:** v0.2.0 → v0.3.0
## [0.2.0] - 2024-11-14

### 🚀 Initial Release Setup
- Set up semantic versioning workflow
- Configured automated changelog generation
- Added conventional commit analysis
- Integrated with GitHub Actions for automated releases

### 📦 Package Configuration
- Updated to MIT license
- Comprehensive test suite setup
- Performance testing infrastructure
- Code quality and security checks

### 🏗️ Development Infrastructure
- GitHub Actions CI/CD pipeline
- Documentation deployment to GitHub Pages
- Code coverage reporting with Codecov
- Automated dependency management

---

**Note:** This changelog is now automatically maintained by the semantic release workflow.
All future changes will be documented here automatically based on conventional commits.
