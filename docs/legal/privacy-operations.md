# Privacy Operations

Effective date: 2026-05-13

This page describes the current retention, deletion, and export handling for
Story Generator. It reflects the repository baseline only and does not claim
automation, billing support, or response times that are not implemented yet.

## What The App Stores

The current application may store:

- account details such as username, email address, role, and password hash;
- password reset records used to complete recovery requests;
- story drafts, completed stories, page content, and story metadata;
- character records, including optional reference-image paths;
- uploaded character photos and other user-supplied files stored outside the
  public frontend bundle;
- generated story images, character reference images, and PDF exports;
- logs, monitoring data, and admin-safe configuration overrides needed to run
  and support the service.

## Retention Baseline

The current product does not ship a formal retention timer or automated TTL for
user content. In practice, data remains stored until one of the following occurs:

- a user deletes a story or character in the app;
- an admin soft-deletes a user or story through moderation tools;
- a file is replaced by a later workflow step;
- maintainers remove content during manual support handling;
- operational logs rotate according to the configured logging setup.

Story-level export is currently available through the PDF export flow in the
app, but that is not the same thing as a full-account archive.

## Deletion Handling

Current deletion behavior is split by object type:

- deleting a story through the product removes the story record, its pages, and
  the generated files associated with that story;
- deleting a character removes the character record and associated generated or
  uploaded character image files used by that character;
- admin moderation uses soft delete flags for users and stories, which means
  the record is hidden from normal application flows rather than immediately
  purged.

Because the app is still at an early commercial-readiness stage, the repo does
not promise a guaranteed purge schedule across backups, archives, or future
deployment vendors.

## Export Requests

There is no self-serve full-account export bundle yet.

If a user needs a copy of data currently stored for an account, maintainers can
handle the request manually through the support process in this pack. The exact
format depends on the current storage layout and the scope of the request, but
it may include user profile data, story content, character records, and copies of
available uploaded or generated files where practical.

## Account Deletion Requests

There is no self-serve account deletion flow in the product yet.

For now, account deletion requests should be sent through the support process in
this pack or another private maintainer channel when one is available. Requests
may require verification that the requester controls the account. Where a
request can be fulfilled, the result may be a manual deletion or soft-deletion
action consistent with the current application state.

## When This Document Changes

If the product adds self-serve export, self-serve account deletion, a formal
retention schedule, or a new storage provider, this document should be updated
before launch of that behavior.
