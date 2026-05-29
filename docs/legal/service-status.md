# Service Status

Effective date: 2026-05-14

Story Generator does not yet publish a separate incident dashboard or historical
uptime page.

The running application exposes a lightweight health endpoint at `/healthz`.
That endpoint is intended as a simple availability check for the current app
deployment and returns a basic JSON status payload when the service is up.

If a production-grade status page or incident feed is added later, this document
should be updated to point to it.