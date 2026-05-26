# Compatibility Matrix

Track compatibility between frontend and backend versions and API versions.

- API URL version is independent from package versions. Only bump `/api/v1` → `/api/v2` for breaking API changes.
- The current contract is the `/api/v1` path prefix. No `X-API-Version` response header is currently guaranteed.

## Matrix

| Frontend | Requires Backend | API Version |
|---------:|------------------:|:-----------|
| >=0.6.0  | >=0.6.0           | v1         |

## Policy
- Breaking API changes: mark commits with `feat!: ...`, plan deprecation, and update this matrix.
- Frontend release notes must state minimum backend version and API version.
- Backend release notes must state any deprecations and migration steps.
