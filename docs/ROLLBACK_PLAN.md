# Rollback Plan

This document describes how to recover quickly from a bad deployment.

## Trigger Conditions
- Production deploy succeeds but app health checks fail.
- Critical runtime error blocks navigation or admin operations.
- Corrupted product data after migration or operator changes.

## Recovery Objectives
- Target restore time: under 15 minutes.
- Preserve latest valid product dataset.

## Rollback Steps
1. Open GitHub Actions and identify the last successful production deployment commit on main.
2. Create a rollback commit that reverts the faulty commit(s):
   - git revert <bad_commit_sha>
3. Push the revert commit to main. This triggers the production deploy workflow.
4. Validate app health:
   - Open the deployed Streamlit URL.
   - Confirm route search works on all floors.
   - Run health checks from the admin panel.
5. If data regression occurred, restore the latest valid SQLite snapshot from S3:
   - Download latest snapshot from s3://<bucket>/<prefix>
   - Replace data/products.db
   - Redeploy via workflow dispatch.

## Emergency Branch Fallback
If main is unstable and fast rollback is not possible:
1. Promote staging commit by merging staging into main.
2. Trigger production deploy manually.
3. Log incident details in release notes.

## Post-Incident Actions
- Record root cause and timeline.
- Add or improve automated tests preventing recurrence.
- Rotate any exposed secrets if incident included credential leakage.
