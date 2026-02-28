# Branch Protection Implementation Guide

This guide explains how to implement the recommended branch protection rules for the gnssraw repository.

## Quick Start

The fastest way to implement branch protection is using GitHub Rulesets (modern approach) or Branch Protection Rules (classic approach).

## Option 1: GitHub Rulesets (Recommended)

Rulesets are GitHub's modern approach to branch protection, offering more flexibility and better organization.

### Steps to Implement

1. **Navigate to Repository Settings**
   - Go to https://github.com/torupati/gnssraw
   - Click **Settings** → **Rules** → **Rulesets**

2. **Create New Ruleset**
   - Click **New ruleset** → **New branch ruleset**
   - Name: `Main Branch Protection`

3. **Configure Target Branches**
   - Target: Include default branch
   - Add pattern: `main`

4. **Enable Required Rules**

   Check these rules:

   - ✅ **Require a pull request before merging**
     - Required approvals: `1`
     - Dismiss stale pull request approvals when new commits are pushed: ✅
     - Require review from Code Owners: ⬜ (optional)

   - ✅ **Require status checks to pass**
     - Add required check: `lint-typecheck`
     - Require branches to be up to date before merging: ⬜ (optional - can slow development)

   - ✅ **Block force pushes**

   - ✅ **Restrict deletions**

5. **Set Enforcement Level**
   - Choose **Active** (enforces rules)
   - Or **Evaluate** (logs but doesn't block - good for testing)

6. **Configure Bypass**
   - Repository administrators: Can bypass (for emergency fixes)
   - Or: No one can bypass (strictest)

7. **Save Ruleset**

### Creating Additional Rulesets (Optional)

You can create additional rulesets for:
- Development branches (less strict)
- Release branches (stricter)
- All branches (universal rules)

## Option 2: Classic Branch Protection Rules

If you prefer the classic approach:

1. **Navigate to Branch Settings**
   - Go to https://github.com/torupati/gnssraw
   - Click **Settings** → **Branches**

2. **Add Rule**
   - Click **Add rule** or **Add classic branch protection rule**
   - Branch name pattern: `main`

3. **Configure Protection Settings**

   Enable these options:

   - ✅ **Require a pull request before merging**
     - ✅ Require approvals: `1`
     - ✅ Dismiss stale pull request approvals when new commits are pushed
     - ⬜ Require review from Code Owners (optional)

   - ✅ **Require status checks to pass before merging**
     - ✅ Require branches to be up to date before merging (optional)
     - Search for and add: `lint-typecheck`

   - ✅ **Require linear history** (optional - for cleaner git history)

   - ✅ **Do not allow bypassing the above settings** (or allow for admins only)

   - ✅ **Include administrators** (apply rules to admins too)

4. **Save Changes**

## Verifying Setup

After implementation, test the rules:

1. **Try pushing directly to main** - Should be blocked
2. **Create a PR without CI passing** - Should not be mergeable
3. **Create a PR with passing CI** - Should require review
4. **After approval** - Should be mergeable

## Rollback Plan

If rules cause issues:

1. **Disable enforcement**:
   - Rulesets: Change to "Disabled" or "Evaluate" mode
   - Classic: Edit rule and uncheck problematic settings

2. **Adjust specific rules**: Fine-tune rather than removing entirely

3. **Communicate**: Inform team of any changes

## Recommended Rollout Strategy

For smooth adoption:

### Week 1: Preparation
- ✅ Merge this PR with documentation
- Announce upcoming branch protection to contributors
- Review open PRs and ensure they're up to date

### Week 2: Initial Setup
- Enable PR requirement with 1 reviewer
- Enable CI checks requirement
- Keep enforcement in "Evaluate" mode if available
- Monitor for issues

### Week 3: Full Enforcement
- Switch to "Active" enforcement
- Enable force push blocking
- Enable deletion restrictions
- Monitor and adjust as needed

### Week 4+: Optimization
- Gather feedback from contributors
- Adjust rules based on real usage
- Consider additional rules (linear history, signed commits)

## Common Issues and Solutions

### Issue: CI check not appearing in required checks

**Solution**:
- Ensure the workflow has run at least once on a PR
- Check that the job name in `.github/workflows/ci.yml` matches exactly
- The check name is `lint-typecheck` from the `lint-typecheck:` job

### Issue: Can't merge even with approvals

**Solution**:
- Check that all required status checks passed
- Verify branch is up to date with main if that's required
- Check for conflicting rules or restrictions

### Issue: Too slow - waiting for reviews

**Solution**:
- Consider reducing required reviewers to 1 (already recommended)
- Add CODEOWNERS for automatic reviewer assignment
- Enable "Dismiss stale reviews" to reduce re-review burden

### Issue: Admin can't make emergency fixes

**Solution**:
- Configure bypass permissions for repository admins
- Use "Allow admins to bypass" option
- Keep emergency contact list updated

## Integration with Existing Workflows

The current CI workflow (`.github/workflows/ci.yml`) already runs:
- Ruff linting
- Ruff formatting check
- Mypy type checking

These checks will automatically be available for the "require status checks" rule.

## Future Enhancements

Consider adding later:

1. **CODEOWNERS file**
   ```
   # Example .github/CODEOWNERS
   * @torupati
   /app/api/ @torupati
   *.md @torupati
   ```

2. **PR Template**
   ```markdown
   # .github/pull_request_template.md
   ## Description

   ## Related Issues
   Fixes #

   ## Testing
   - [ ] Linting passes
   - [ ] Type checking passes
   ```

3. **Dependabot** for automated dependency updates

4. **Required PR labels** for categorization

5. **Auto-merge** for approved PRs with passing checks

## Questions?

If you encounter issues:
1. Check GitHub's [branch protection documentation](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches)
2. Open an issue in this repository
3. Contact repository maintainers

## Summary

**Recommended immediate actions:**
1. ✅ Merge this PR (adds documentation)
2. ✅ Create "Main Branch Protection" ruleset
3. ✅ Enable PR requirements with 1 reviewer
4. ✅ Require `lint-typecheck` status check
5. ✅ Block force pushes and deletions

These five steps provide immediate benefit with minimal friction.

---

**Last Updated**: 2026-01-16
**Maintained by**: Repository administrators
