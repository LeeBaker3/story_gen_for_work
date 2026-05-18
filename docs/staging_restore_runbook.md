# Staging Restore Runbook

This runbook documents the initial restore posture for the staging baseline introduced in issue #122.

## Baseline

- Database target: Neon Postgres.
- Asset target: S3-compatible object storage.
- Schema posture: Alembic-managed only.
- Retention baseline: keep at least 14 days of restorable database backups/PITR and 14 days of object-storage backup history.

## Required environment posture

- `RUN_ENV=staging`
- `DATABASE_URL=<Neon Postgres connection string for the restore target>`
- `DB_BOOTSTRAP_MODE=migrations`
- `ASSET_STORAGE_BACKEND=s3`
- `ASSET_STORAGE_PUBLIC_PREFIX=public`
- `ASSET_STORAGE_PRIVATE_PREFIX=private`
- `ASSET_STORAGE_S3_BUCKET=<restore bucket or bucket containing restored objects>`
- `ASSET_STORAGE_S3_REGION=<region>`

## Initial restore procedure

1. Choose the restore point for the Neon database.
2. Create or identify the Neon restore target and obtain its connection string.
3. Restore object-storage data into the target bucket while preserving the configured public and private prefixes.
4. Export the staging environment variables listed above against the restore target.
5. Run Alembic against the restore target before starting the app.
   - `./.venv/bin/python -m alembic -c alembic.ini upgrade head`
6. Start the API and confirm `/api/v1/admin/monitoring/config` reports:
   - `database_bootstrap_mode=migrations`
   - `asset_storage_backend=s3`
   - `runtime_schema_bootstrap_enabled=false`
7. Run a smoke check that reads existing records and verifies restored asset keys still follow the configured public/private prefixes.

## Notes

- This repository does not provision Neon or S3 resources.
- This repository does not yet implement S3 upload/download or presigned URL delivery.
- If a restore must be validated without affecting the main staging environment, use an isolated Neon target and isolated bucket/prefixes first.