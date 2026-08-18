# Git History Remediation Procedure

## Objective
Remove `intentlock.db` and `logs/audit_trail.jsonl` from all Git history without executing destructive operations.

## Files to Purge
- `intentlock.db` — SQLite runtime database
- `logs/audit_trail.jsonl` — JSONL audit log

## Pre-Execution Verification Checklist

Execute these commands BEFORE any destructive operation:

```bash
# 1. Verify current branch
git branch --show-current

# 2. Verify remote
git remote -v

# 3. Verify HEAD commit
git log --oneline -1

# 4. Verify uncommitted changes (should be none or only intended files)
git status --short

# 5. Verify files exist in history
git log --all --oneline -- intentlock.db logs/audit_trail.jsonl

# 6. Verify files are NOT in current working tree (should be deleted)
ls -la intentlock.db logs/audit_trail.jsonl 2>/dev/null || echo "Files not present in working tree"
```

Expected results:
- Current branch: `master` (or your protected branch)
- Remote: your upstream repository URL
- No uncommitted changes to application code
- Both files appear in `git log --all` history
- Files do not exist in working tree

## Backup Procedure

```bash
# Create a backup branch from current HEAD
git branch backup-before-history-rewrite-$(date +%Y%m%d-%H%M%S)

# Verify backup exists
git branch --list "backup-before-history-rewrite-*"

# Push backup to remote (requires write access)
git push origin backup-before-history-rewrite-$(date +%Y%m%d-%H%M%S)
```

**Critical:** The backup branch preserves the full history including the runtime files. Do NOT delete this branch until the rewrite is verified successful.

## History Rewrite Procedure

### Option A: git-filter-repo (Recommended)

`git-filter-repo` is the modern, supported tool for history rewriting. It replaces the deprecated `git filter-branch`.

```bash
# 1. Install git-filter-repo
pip install git-filter-repo

# 2. Verify installation
git filter-repo --help | head -5

# 3. Execute the filter
git filter-repo \
  --path intentlock.db \
  --path logs/audit_trail.jsonl \
  --invert-paths

# 4. Verify removal from history
git log --all --oneline -- intentlock.db logs/audit_trail.jsonl
# Expected: no output (files completely removed from history)

# 5. Verify repository integrity
git fsck --full
# Expected: no errors

# 6. Verify current HEAD is intact
git log --oneline -5
```

### Option B: BFG Repo-Cleaner (Alternative)

BFG is faster for large repositories but less flexible than `git-filter-repo`.

```bash
# 1. Download BFG
curl -L -o bfg.jar https://repo1.maven.org/maven2/com/madgag/bfg/1.14.0/bfg-1.14.0.jar

# 2. Create a temporary text file listing paths to delete
echo "intentlock.db" > .bfg-ignore
echo "logs/audit_trail.jsonl" >> .bfg-ignore

# 3. Run BFG
java -jar bfg.jar --delete-files .bfg-ignore --no-blob-protection

# 4. Clean up and verify
rm -f .bfg-ignore bfg.jar
git reflog expire --expire=now --all
git gc --prune=now --aggressive
git fsck --full

# 5. Verify removal
git log --all --oneline -- intentlock.db logs/audit_trail.jsonl
# Expected: no output
```

## Post-Rewrite Verification

```bash
# 1. Verify files are absent from all history
git log --all --oneline -- intentlock.db logs/audit_trail.jsonl
# Expected: empty output

# 2. Verify .gitignore prevents re-addition
echo "test" > intentlock.db
git status --short
# Expected: intentlock.db shown as untracked (ignored)
rm intentlock.db

# 3. Verify repository size reduction (optional)
git count-objects -vH

# 4. Run full test suite to ensure no breakage
pytest -q
# Expected: 760 passed, 5 skipped, 0 failed
```

## Coordinated Force-Push Procedure

**WARNING:** Force-pushing rewrites public history. All collaborators must re-sync their local clones.

### Pre-Push Checklist
- [ ] Team notified of force-push
- [ ] Backup branch pushed to remote
- [ ] CI pipeline green on rewritten branch
- [ ] All team members have stopped local work

### Force-Push Commands

```bash
# 1. Force push the rewritten branch
git push origin --force --all

# 2. Force push tags (if any were rewritten)
git push origin --force --tags

# 3. Delete the backup branch from remote (after verification)
git push origin --delete backup-before-history-rewrite-YYYYMMDD-HHMMSS
```

### Team Re-Sync Instructions

All team members must execute:

```bash
# 1. Stash or commit any local work
git stash push -m "pre-rewrite-sync-$(date +%Y%m%d)"

# 2. Fetch the rewritten history
git fetch origin

# 3. Reset local branch to match remote
git checkout master
git reset --hard origin/master

# 4. Verify clean state
git status
# Expected: "Your branch is up to date with 'origin/master'"

# 5. Recover local work if needed
git stash pop
```

## Rollback Procedure

If issues are discovered after the force-push:

```bash
# 1. Reset to the backup branch
git checkout master
git reset --hard origin/backup-before-history-rewrite-YYYYMMDD-HHMMSS

# 2. Force push the rollback
git push origin --force --all

# 3. Investigate and retry the rewrite
```

## Risk Assessment

| Risk | Mitigation |
|------|-----------|
| History rewrite breaks CI | Backup branch preserves original state; rollback is immediate |
| Team members lose local work | Stash + reset instructions provided; backup branch available |
| Large repository clone impact | BFG or git-filter-repo reduces size; team only needs to re-fetch |
| Sensitive data remains in backup | Backup branch should be deleted after verification; enforce branch protection |

## Approval Required

**DO NOT execute this procedure without explicit team approval.**

Required approvals:
1. Repository maintainer
2. Security team
3. All active contributors notified

## Contact

For questions about this procedure, contact the repository maintainer before executing any steps.
