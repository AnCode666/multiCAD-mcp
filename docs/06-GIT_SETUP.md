# 06 - Git Setup

## Repository

**URL**: https://github.com/AnCode666/multiCAD-mcp

## Commit Convention

```
<type>(<scope>): <subject>
```

### Types

- `feat` - New feature
- `fix` - Bug fix
- `docs` - Documentation
- `refactor` - Code refactoring
- `test` - Tests
- `chore` - Build, dependencies

### Examples

```powershell
git commit -m "feat(blocks): add insert_block tool"
git commit -m "fix(adapter): correct coordinate handling"
git commit -m "docs(readme): update tool count"
```

## Workflow

### Feature Branch

```powershell
git checkout -b feature/my-feature
# ... make changes ...
git add .
git commit -m "feat(module): description"
git push -u origin feature/my-feature
```

### Merge

```powershell
git checkout main
git pull origin main
git merge feature/my-feature
git push origin main
git branch -d feature/my-feature
```

## Branch Naming

- `feature/<description>` - New features
- `fix/<description>` - Bug fixes
- `refactor/<description>` - Refactoring
- `docs/<description>` - Documentation

## Rules

- **Do commit**: Source code, tests, documentation
- **Don't commit**: Generated files, logs, `.env`, IDE settings
- **Always**: Test before committing (`pytest tests/ -v`)
- **Never**: Force push to main
