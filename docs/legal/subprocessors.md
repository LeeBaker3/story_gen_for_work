# Subprocessors And Service Providers

Effective date: 2026-05-13

This page lists the external service providers that are currently known to be
used by the repository baseline. It intentionally avoids naming vendors that the
current app does not depend on.

## Current Providers

| Provider | Purpose | Data Types | Notes |
| --- | --- | --- | --- |
| OpenAI | Story text generation, image generation, and AI-assisted prompt/image workflows | Story outlines, character details, uploaded-image-derived prompts, and generated content needed for the request | Used when AI features are enabled. The app can also be configured for OpenAI-compatible endpoints during development or testing. |

## What Is Not A Subprocessor In The Current Baseline

The checked-in app baseline stores data locally by default in SQLite and on the
filesystem under the configured data directories. Those local storage locations
are part of the application deployment, not external subprocessors.

The repository does not currently include a managed email vendor, analytics SDK,
payments stack, or third-party support platform. If any of those are introduced
later, they should be added here before the related feature goes live.

## Update Rule

If a new external vendor is added for hosting, storage, monitoring, messaging,
or AI processing, this list should be updated to match the live product
configuration.
