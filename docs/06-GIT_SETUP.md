# Git Repository Setup

## Repository Information

**Repository URL**: <https://github.com/AnCode666/multiCAD-mcp>

**Local instalation location**: multiCAD-mcp project directory (can be placed anywhere - output files saved to `~/Documents/multiCAD Exports`)

**Status**: Initialized and Ready for Development

## Commit History

### Initial Commit

```text
feat(version): implement centralized version management and simplify config

Complete project implementation:
- FastMCP 2.0 server with 46 MCP tools in 9 categories
- Universal CAD adapter supporting AutoCAD®, ZWCAD®, GstarCAD®, BricsCAD®
- Factory pattern for CAD type selection via ProgID
- Natural language processing for command interpretation
- Centralized version management in __version__.py (v0.1.0)
- 45+ test cases with pytest
- Comprehensive documentation (8 files)
- Implements exception hierarchy
- 100% type hints coverage
- Excel export with locale-aware formatting
- Git configuration and workflow setup
```

---

## Files Tracked

### Source Code

**Core Infrastructure**:

- `src/server.py` - FastMCP server entry point
- `src/config.json` - Configuration file

**Core Modules** (`src/core/`):

- `cad_interface.py` - Abstract base class
- `config.py` - Configuration management
- `exceptions.py` - Exception classes

**Adapters** (`src/adapters/`):

- `autocad_adapter.py` - Universal CAD adapter
- `__init__.py` - Factory pattern implementation

**MCP Tools** (`src/mcp_tools/`):

- `constants.py`, `helpers.py`, `decorators.py`, `adapter_manager.py`
- `tools/` - 9 tool categories (connection, drawing, entities, files, layers, nlp, simple, debug, export)

**NLP** (`src/nlp/`):

- `processor.py` - Natural language processor

### Tests (3 files)

- `tests/test_nlp_processor.py` - NLP tests
- `tests/test_adapters.py` - Adapter tests
- `tests/__init__.py` - Test package init

### Documentation (`docs/`)

- `README.md` - Documentation index (this folder)
- `01-SETUP.md` - Development environment setup
- `02-ARCHITECTURE.md` - System design and architecture
- `03-EXTENDING.md` - Guide to adding features
- `04-TROUBLESHOOTING.md` - Debugging guide
- `05-REFERENCE.md` - Complete API reference
- `06-GIT_SETUP.md` - This file (Git workflow)
- `07-CHANGELOG.md` - Version history

### Root Documentation

- `README.md` (root) - Main project documentation

### Configuration (2 files)

- `.gitignore` - Git exclusions
- `requirements.txt` - Python dependencies

---

## Getting Started with Git

### Clone the Repository

```powershell
# Clone from remote (when remote is set up)
git clone <remote-url>

# Navigate to project
cd multiCAD-mcp
```

### View Commit History

```powershell
# Show all commits
git log

# Show one-line summary
git log --oneline

# Show detailed stats
git log --stat

# Show specific commit
git show <commit-hash>
```

### Create a New Branch

```powershell
# Create and switch to new branch
git checkout -b feature/my-feature

# Make changes
git add .
git commit -m "Describe your changes"

# Push to remote (when remote is configured)
git push origin feature/my-feature
```

### Make Changes and Commit

```powershell
# Check status
git status

# Stage changes
git add .

# Or add specific files
git add src/adapters/my_adapter.py

# Commit with message
git commit -m "Description of changes"

# View recent commits
git log --oneline -5
```

### Merge Changes

```powershell
# Switch to master
git checkout master

# Merge feature branch
git merge feature/my-feature

# Delete feature branch
git branch -d feature/my-feature
```

---

## Commit Message Guidelines

This project follows conventional commit format:

```xml
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- **feat**: New feature
- **fix**: Bug fix
- **docs**: Documentation changes
- **style**: Code style changes (formatting)
- **refactor**: Code refactoring
- **test**: Test additions/changes
- **chore**: Build, dependencies, etc.

### Examples

```powershell
# New feature
git commit -m "feat(adapters): add BricsCAD adapter support"

# Bug fix
git commit -m "fix(nlp): correct coordinate extraction for negative values"

# Documentation
git commit -m "docs(readme): update installation instructions"

# Tests
git commit -m "test(adapters): add 10 new test cases for AutoCAD adapter"

# Refactoring
git commit -m "refactor(config): simplify configuration loading logic"
```

---

## Remote Repository Setup (Optional)

When ready to push to GitHub or another remote:

```powershell
# Add remote
git remote add origin <remote-url>

# Verify remote
git remote -v

# Push initial commits
git push -u origin master

# Push new branches
git push -u origin feature/my-feature
```

---

## Branching Strategy

Recommended workflow:

```text
master (main branch)
  ↓
develop (development branch)
  ↓
feature/* (feature branches)
  ├── feature/nlp-improvements
  ├── feature/new-cad-adapter
  └── feature/rest-api

hotfix/* (urgent fixes)
  └── hotfix/critical-bug
```

### Branch Naming

- `feature/<description>` - New features
- `fix/<description>` - Bug fixes
- `refactor/<description>` - Code refactoring
- `test/<description>` - Test additions
- `docs/<description>` - Documentation updates
- `hotfix/<description>` - Critical production fixes

---

## Managing Development

### Starting a Feature

```powershell
# Create and switch to feature branch
git checkout -b feature/my-feature

# Make changes
# ... edit files ...

# Stage and commit
git add .
git commit -m "feat(module): description of feature"

# Push to remote
git push -u origin feature/my-feature

# Create Pull Request on GitHub
```

### Code Review Workflow

```powershell
# After review, merge locally
git checkout master
git pull origin master
git merge feature/my-feature

# Push to remote
git push origin master

# Delete remote feature branch
git push origin --delete feature/my-feature

# Delete local feature branch
git branch -d feature/my-feature
```

---

## Useful Git Commands

```powershell
# Show current status
git status

# Show file changes
git diff

# Show staged changes
git diff --staged

# Undo changes in file
git checkout -- filename

# Reset staged changes
git reset HEAD filename

# Revert a commit
git revert <commit-hash>

# View commit history with graph
git log --graph --oneline --all

# Search commits by message
git log --grep="search term"

# Search commits by author
git log --author="name"

# Create a tag for release
git tag -a v1.1.0 -m "Version 1.1.0"
git push origin v1.1.0
```

---

## Best Practices

1. **Commit Often**: Small, logical commits are better than large ones
2. **Write Good Messages**: Clear, descriptive commit messages
3. **Pull Before Push**: Always pull latest changes before pushing
4. **Branch for Features**: Use branches for new features/fixes
5. **Review Code**: Use PRs for peer review
6. **Test Before Committing**: Run tests before committing
7. **Keep History Clean**: Use rebase for cleaner history (optional)
8. **Document Changes**: Update CHANGELOG.md and docs

---

## Repository Rules

- ✅ Do commit: Source code, tests, documentation, configuration
- ❌ Don't commit: Generated files, logs, `.env` files, IDE settings (via .gitignore)
- ✅ Always: Write clear commit messages
- ✅ Always: Test before committing
- ✅ Always: Pull before pushing
- ❌ Never: Force push to master/develop

---

## Troubleshooting

### "fatal: not a git repository"

```powershell
# Initialize git
git init
```

### "rejected ... [non-fast-forward]"

```powershell
# Pull latest changes first
git pull origin master

# Then try pushing again
git push origin master
```

### "merge conflict"

```powershell
# Resolve conflicts manually
# Edit conflicted files, choose versions
git add .
git commit -m "fix: resolve merge conflict"
```

### "accidentally committed to master"

```powershell
# Undo last commit (keep changes)
git reset --soft HEAD~1

# Move to new branch
git checkout -b feature/branch-name
git commit -m "feat: your message"
```

---

## Additional Resources

- [Git Documentation](https://git-scm.com/doc)
- [GitHub Guides](https://guides.github.com/)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [Git Branching Model](https://nvie.com/posts/a-successful-git-branching-model/)

---

## Current Repository Status

```text
✅ Git initialized
✅ Initial commit created
✅ 25 files tracked
✅ .gitignore configured
✅ Remote repository configured (GitHub)
✅ Ready for development
```

**Next Steps**:

```text
1. Set up branch protection rules
2. Configure CI/CD pipeline
3. Add collaborators
4. Start development on feature branches
