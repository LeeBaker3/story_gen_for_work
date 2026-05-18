# Launch Trust, Support, And Outage Copy Spec

Effective date: 2026-05-18

This document is the product copy and state guidance for launch trust,
support, ownership/licensing, and degraded-mode messaging.

It is intentionally a specification for future frontend/account work. It does
not claim the current application already renders every state, banner, or
surface below.

## Scope

Use this spec for:

- signup and sign-in trust copy;
- wizard entry and pre-generation trust copy;
- generation progress and degraded-mode messaging;
- account and story-surface support messaging;
- ownership/licensing summary text for generated output and uploads.

## Product State Definitions

These states are the minimum set the UI should be able to express.

- `trust_ready`: the user can sign up, log in, and continue to the wizard.
- `generation_ready`: the account has access and the provider path is healthy.
- `generation_slow`: generation is still in progress, but the provider is
  slower than usual.
- `generation_paused`: generation is temporarily unavailable because provider
  health, limits, or a fail-safe says not to spend.
- `generation_locked`: the account can still use non-generation features and
  existing content, but it cannot start new generation jobs.
- `support_best_effort`: support is available through the repository issue
  tracker with no guaranteed response time.

## Placement Guidance

- Signup and account creation: place short trust copy directly below the
  primary action and keep the policy links visible.
- Wizard start and review: place a concise AI disclosure near the generate
  action and repeat the most important ownership/trust summary on the review
  step.
- Generation progress: place status-specific banners above the progress UI.
- Account or story headers: place entitlement, support, and plan summary copy in
  an info block or sidebar where users can find it again later.
- Story preview, editor, and export: place ownership/licensing summary copy in a
  help panel, footer note, or info drawer rather than as a blocking dialog.

## Copy Deck

### Signup Trust Copy

Use a short, plain statement that explains AI use and policy acceptance without
overpromising product behavior.

Suggested product copy:

> By creating an account, you agree to the Terms of Service, Privacy Policy,
> and Copyright and IP Policy. We use AI to generate stories and images from
> the content you provide.

Supporting note for adjacent UI text:

> Uploads should only include content you are allowed to use.

### Wizard Entry And Pre-Generation Copy

Use this copy near the first wizard step and again on the final review step.

Suggested product copy:

> Review your story details before generating. Your outline, selected
> characters, and layout choices will be used to create the story.

> Generation can take a few minutes. If service health degrades, we may pause
> new generation and keep your existing stories available.

### Support Availability Copy

Use this on account surfaces, help links, and policy pages.

Suggested product copy:

> Support is best effort through the repository issue tracker.

> We can help with login, story generation, editing, export, characters, and
> documentation questions.

> We do not promise a response time or a formal SLA.

Do not add live chat, phone support, or guaranteed turnaround copy unless a
future release explicitly adds those commitments.

### Ownership And Licensing Summary Copy

Use this in story preview, editor, export, account, and policy-entry surfaces.

Suggested product copy:

> You keep the rights you already have in the prompts, outlines, uploads, and
> other content you submit.

> You must have permission to upload character photos or any other third-party
> material.

> Generated stories, images, and PDFs may still resemble ideas, names,
> settings, or visual elements that are protected by third-party rights.

> Review the output before you publish, distribute, or commercially use it.

If a future release adds explicit output licensing, royalty terms, or resale
rights, this section must be updated before that launch.

### Degraded-Mode And Outage Copy

Use these messages for slow generation, provider outages, and spend fail-safe
states.

Slow generation:

> Generation is taking longer than usual. Your request is still in progress.

Provider unavailable or paused:

> Story generation is temporarily unavailable. You can still edit existing
> stories and try again later.

Generation locked by entitlement:

> You have used all available generation access for this period. You can still
> edit, preview, export, and manage existing stories.

Fail-safe / unsafe spend state:

> Generation is temporarily paused while provider health recovers. New
> generation requests are blocked until the service is safe to use again.

Keep outage copy factual and short. Do not imply compensation, guaranteed
recovery times, or automatic credit restoration unless another document
explicitly authorizes that behavior.

## Source Documents

This spec should stay aligned with:

- `docs/PRODUCT_REQUIREMENTS_DOCUMENT.md` section 3.8;
- `docs/legal/support-policy.md`;
- `docs/legal/service-status.md`;
- `docs/legal/copyright-ip-policy.md`;
- `docs/legal/README.md`.

If those documents change in a way that affects the user-facing wording here,
update this spec in the same release.