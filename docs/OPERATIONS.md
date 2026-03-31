# Operations Guide

## Environments
- staging: deploys from staging using STREAMLIT_STAGING_DEPLOY_HOOK
- production: deploys from main using STREAMLIT_DEPLOY_HOOK

## Required GitHub Secrets
- STREAMLIT_DEPLOY_HOOK
- STREAMLIT_STAGING_DEPLOY_HOOK
- BACKUP_S3_BUCKET
- AWS_REGION
- AWS_ACCESS_KEY_ID
- AWS_SECRET_ACCESS_KEY

## CI/CD Workflows
- .github/workflows/ci.yml
- .github/workflows/deploy-staging.yml
- .github/workflows/deploy-production.yml
- .github/workflows/backup-sqlite.yml

## Local Environment Setup
1. Copy .env.example to .env.
2. Fill in admin auth, observability, deploy, and backup values.
3. Start app with streamlit run app.py.

## One-Click Store Onboarding
Run:
python admin/onboard_store.py --store-id my_store --name "My Store" --lat 51.5 --lng -0.1

This will:
- create data/stores/<store-id>/maps
- create data/stores/<store-id>/graphs
- copy default map/graph templates when available
- generate data/stores/<store-id>/README.md
- update data/stores.json

## Backups
Daily backup workflow uploads data/products.db snapshot to S3.
Manual run:
python -m utils.backup_sqlite_to_s3 --bucket <bucket>
