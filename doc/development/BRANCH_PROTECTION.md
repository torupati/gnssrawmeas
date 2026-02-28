# Branch Protection Ruleset

This document outlines the recommended branch protection rules for the gnssraw repository to ensure code quality, maintain stability, and facilitate effective collaboration.

## Main Branch (`main`) Protection Rules

The `main` branch should have the following protection rules enabled:

### 1. Require Pull Request Reviews

- **Minimum required approvals**: 1
- **Dismiss stale reviews**: Enabled when new commits are pushed
- **Require review from code owners**: Optional (enable when CODEOWNERS file is added)
- **Rationale**: Ensures all changes are reviewed before merging, catching bugs and maintaining code quality standards

### 2. Require Status Checks to Pass

Required status checks before merging:
- **Lint and Type Check** (from `.github/workflows/ci.yml`)
  - Ruff check
  - Ruff format check
  - Mypy type checking

- **Rationale**: Ensures code meets linting standards and passes type checking before integration, preventing CI failures on the main branch

### 3. Require Branches to be Up to Date

- **Status**: Recommended but optional
- **Rationale**: Ensures changes are tested against the latest main branch code, reducing integration issues. Can slow down development if main is frequently updated

### 4. Require Linear History

- **Status**: Recommended
- **Option**: Require merge commits OR Require rebase
- **Rationale**: Maintains a clean, understandable git history. Choose based on team preference:
  - Merge commits: Preserves feature branch context
  - Rebase: Creates linear history without merge commits

### 5. Restrict Direct Pushes

- **Allow force pushes**: Disabled
- **Allow deletions**: Disabled
- **Restrict who can push**: Enable for repository maintainers only
- **Rationale**: Prevents accidental force pushes or deletions that could cause data loss

### 6. Require Signed Commits (Optional)

- **Status**: Optional but recommended for security
- **Rationale**: Verifies commit authenticity using GPG signatures

## Feature Branch Best Practices

### Branch Naming Convention

Use descriptive branch names following these patterns:

- `feature/<issue-number>-<brief-description>` - New features
- `bugfix/<issue-number>-<brief-description>` - Bug fixes
- `enhancement/<issue-number>-<brief-description>` - Enhancements
- `docs/<description>` - Documentation changes
- `refactor/<description>` - Code refactoring

**Examples**:
- `feature/9-investigate-gnssanalysis`
- `bugfix/8-fix-pytest-issues`
- `docs/update-api-readme`

### Pull Request Workflow

1. **Create feature branch** from up-to-date `main`
2. **Make focused changes** addressing single issue/feature
3. **Run local tests** before pushing:
   ```bash
   ruff check . --output-format=github
   ruff format --check .
   mypy --explicit-package-bases app --pretty
   ```
4. **Create Pull Request** with clear description
5. **Address review feedback** promptly
6. **Merge** after approval and passing CI

## GitHub Rulesets Configuration

GitHub Rulesets (modern alternative to branch protection) should be configured as follows:

### Ruleset: Main Branch Protection

**Target**: `main` branch

**Rules**:
1. ✅ Require pull request before merging
   - Required approvals: 1
   - Dismiss stale reviews on push

2. ✅ Require status checks to pass
   - Required checks:
     - `lint-typecheck` (Lint and Type Check workflow)
   - Require branches to be up to date: Optional

3. ✅ Block force pushes

4. ✅ Restrict deletions

5. ✅ Require linear history (optional)

6. ✅ Require deployments to succeed (if applicable)

### Ruleset: All Branches

**Target**: All branches

**Rules**:
1. ✅ Block force pushes to `main` only
2. ✅ Restrict deletions of `main` only

## Enforcement Level

**Recommended approach**:
- Start with **"Active" enforcement** for main branch
- Consider **"Evaluate" mode** initially to test rules without blocking
- Exemptions: Repository administrators for emergency fixes

## Benefits of These Rules

1. **Code Quality**: Mandatory reviews and CI checks maintain high standards
2. **Stability**: Protected main branch prevents breaking changes
3. **Collaboration**: PR-based workflow encourages knowledge sharing
4. **Traceability**: All changes tracked through PRs and reviews
5. **Rollback Safety**: Clean history makes reverting changes easier

## Migration Strategy

If implementing these rules on an existing repository:

1. **Announce changes** to all contributors
2. **Enable CI checks** first (already done)
3. **Activate PR requirement** with 1 reviewer
4. **Monitor** for 1-2 weeks
5. **Add additional rules** (force push block, etc.)
6. **Adjust** based on team feedback

## Future Considerations

As the project grows, consider:

- Adding **CODEOWNERS** file for automatic reviewer assignment
- Implementing **semantic versioning** with protected release branches
- Setting up **automated dependency updates** (Dependabot/Renovate)
- Requiring **issue linking** in PR descriptions
- Adding **required PR templates**
- Implementing **automatic branch deletion** after merge

## Resources

- [GitHub Branch Protection Rules](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)
- [GitHub Rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets)
- [Managing Code Review Settings](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/reviewing-changes-in-pull-requests/about-pull-request-reviews)

## Questions or Feedback

If you have questions about these rules or suggestions for improvements, please:
1. Open an issue for discussion
2. Propose changes via pull request to this document
3. Contact repository maintainers

---

**Last Updated**: 2026-01-16
**Applies to**: gnssraw repository (torupati/gnssraw)
