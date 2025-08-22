# Compatibility Matrix

Track compatibility between frontend and backend versions and API versions.

- API URL version is independent from package versions. Only bump `/api/v1` → `/api/v2` for breaking API changes.
- Backend responses include `X-API-Version: v1` (recommended addition) to make version explicit.

## Matrix

| Frontend | Requires Backend | API Version |
|---------:|------------------:|:-----------|
| >=0.4.4  | >=0.4.4           | v1         |

## Policy
- Breaking API changes: mark commits with `feat!: ...`, plan deprecation, and update this matrix.
- Frontend release notes must state minimum backend version and API version.
- Backend release notes must state any deprecations and migration steps.
