# GitHub Actions Workflows

This directory contains the GitHub Actions workflows that automate the development, testing, and release processes for the VGNC Internal ORM project.

## 🚀 Semantic Release System

The project now implements **automated semantic versioning** following the rules at https://semver.org/ and using **conventional commits** to determine version bumps.

### 📋 How It Works

1. **Commit Analysis**: When pushed to `main`, the workflow analyzes commits since the last release
2. **Version Determination**: Based on commit types, it determines whether to bump MAJOR, MINOR, or PATCH
3. **Automated Release**: Creates git tag, GitHub release, updates `CHANGELOG.md`, and updates version in `pyproject.toml`

### 🔧 Conventional Commit Format

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

**Examples:**
- `feat: add new database connection pooling` → MINOR version bump
- `fix: resolve SQLAlchemy session leak` → PATCH version bump
- `feat!: change authentication API (breaking)` → MAJOR version bump
- `docs: update API documentation` → No version bump

### 📊 Version Bump Rules

| Commit Type | Version Bump | Description |
|-------------|--------------|-------------|
| `feat` | MINOR | New backward-compatible functionality |
| `fix` | PATCH | Backward-compatible bug fixes |
| `BREAKING CHANGE` | MAJOR | Incompatible API changes |
| `perf` | PATCH | Performance improvements |
| `build` | PATCH | Build system changes |
| `revert` | PATCH | Revert previous changes |
| `docs`, `style`, `refactor`, `test`, `ci`, `chore` | NONE | No version bump |

### 🎯 Triggering Releases

**Automatic:**
```bash
# Make conventional commits and push to main
git commit -m "feat: add user authentication"
git commit -m "fix: resolve timeout issue"
git push origin main
```

**Manual (Force Release):**
1. Go to Actions → Release workflow
2. Click "Run workflow"
3. Enable "Force a release"
4. Select release type (patch/minor/major)

### 📁 Files and Scripts

**Main Workflow:**
- `.github/workflows/release.yml` - Semantic release automation

**Python Scripts:**
- `analyze_commits.py` - Analyzes git commits for conventional format
- `determine_version_bump.py` - Determines MAJOR/MINOR/PATCH bump
- `bump_version.py` - Handles semantic version arithmetic
- `generate_release_notes.py` - Creates structured release notes
- `update_version.py` - Updates version in pyproject.toml
- `update_changelog.py` - Maintains CHANGELOG.md

**Configuration:**
- `semantic-release-config.json` - Release behavior configuration

## 🔍 Other Workflows

### CI Pipeline (`ci.yml`)
- Comprehensive testing across Python versions
- Unit, integration, and performance tests
- Code quality checks (Black, Ruff, MyPy, Bandit)
- Build validation
- Test result summarization

### Development Workflow (`development.yml`)
- Fast feedback for feature/bugfix branches
- Essential tests and quality checks
- Optional performance testing
- Development feedback on PRs

### Coverage Workflow (`coverage.yml`)
- Detailed code coverage analysis
- Uploads to Codecov
- Coverage badges generation
- PR comments with coverage breakdown

### Documentation Workflows (`docs.yml`, `pages.yml`)
- Sphinx documentation building
- Deployment to GitHub Pages
- Documentation validation

## 🛠️ Local Development

### Testing the Release Process

```bash
# Dry run - analyze commits without releasing
gh workflow run release.yml --field force_release=false

# Force a specific release type
gh workflow run release.yml --field force_release=true --field release_type=patch
```

### Manual Script Testing

```bash
# Analyze commits since last tag
.github/scripts/analyze_commits.py --range "v0.2.0..HEAD" --output analysis.json

# Determine version bump
.github/scripts/determine_version_bump.py analysis.json

# Test version bumping
.github/scripts/bump_version.py --current 0.2.0 --bump minor

# Generate release notes
.github/scripts/generate_release_notes.py --analysis-file analysis.json --current-version 0.2.0 --new-version 0.3.0
```

## 📚 Resources

- [Semantic Versioning](https://semver.org/)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [Keep a Changelog](https://keepachangelog.com/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)

## ⚠️ Important Notes

- **Only pushes to `main`** trigger automatic releases
- **Conventional commits** are required for version bumps
- **Breaking changes** must include `BREAKING CHANGE:` in commit body or `!` in type
- **Force releases** are available for manual version management
- **CHANGELOG.md** is automatically maintained - don't edit manually