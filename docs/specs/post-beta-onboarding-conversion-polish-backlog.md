# Post-Beta Onboarding And Conversion Polish Backlog

Effective date: 2026-05-20

This document is the source-of-truth backlog for post-beta onboarding and
conversion polish work. It defines measurable experiments for the current Story
Generator product surfaces after the commercial-beta trust, legal, billing, and
entitlement baseline is in place.

It is intentionally a product specification, not an implementation plan. It
does not claim the current frontend already renders every onboarding aid,
education panel, or conversion prompt described below.

## Scope

Use this backlog for:

- first-run onboarding and help inside the existing auth, wizard, character,
  progress, preview, and account-hub surfaces;
- activation experiments tied to first successful story generation;
- conversion experiments tied to trial understanding, entitlement clarity, and
  paid checkout starts;
- prioritization rules that depend on real beta funnel data rather than generic
  UX brainstorming.

Do not use this backlog for:

- pricing or credit-rule changes already defined in the PRD;
- legal-policy copy that belongs in the trust/support copy spec or legal docs;
- speculative landing-page redesign work disconnected from the in-product
  funnel;
- lifecycle email, CRM, or support-operations work that is not triggered by the
  current product surfaces.

## Inputs And Guardrails

This backlog must stay aligned with:

- `docs/PRODUCT_REQUIREMENTS_DOCUMENT.md` section 3.8 for trial, entitlement,
  and quota rules;
- `docs/specs/launch-trust-support-outage-copy-spec.md` for trust, ownership,
  support, and degraded-mode wording constraints;
- `docs/legal/README.md` and linked policies for product claims about privacy,
  support, and AI processing;
- the currently shipped funnel surfaces described in `frontend/index.html`,
  `frontend/script.js`, and the account-hub tests.

Product guardrails for every item below:

- keep the wizard responsible for pre-generation choices and first-run help;
- keep the post-generation editor responsible for editing and layout work after
  value is created;
- do not promise faster generation, guaranteed support, broader ownership
  rights, or new refund terms unless another source document adds those
  commitments;
- do not add conversion prompts that hide remaining trial credits, entitlement
  state, or outage conditions.

## Funnel Definitions

Use these definitions when ranking or evaluating experiments.

- `signup_completed`: account creation succeeds.
- `wizard_started`: authenticated user reaches the first wizard step.
- `review_reached`: user reaches the review step of the wizard.
- `generation_started`: user starts a first story-generation request.
- `first_story_completed`: first story reaches a successful generated state.
- `first_story_viewed`: user opens preview or editor after the first completed
  story.
- `checkout_started`: user opens a paid checkout session from an eligible trial,
  grace, or paid-management surface.
- `paid_activated`: entitlement resolves to `paid-active` after checkout.

Primary product outcomes:

- activation: `signup_completed` to `first_story_completed`;
- assisted activation: `signup_completed` to `first_story_viewed`;
- conversion: `first_story_completed` to `checkout_started`, and
  `checkout_started` to `paid_activated`.

## Measurement Readiness Requirement

Do not permanently rank later experiments until beta funnel instrumentation can
answer these questions by cohort:

- where first-run users abandon between wizard step 1, character work, review,
  and generation start;
- how often users create or upload a character photo before their first story;
- how often first-time generators encounter slow, failed, or quota-blocked
  generation states;
- whether checkout starts happen before or after a first successful story;
- which entitlement states (`trial`, `grace`, `paid-active`, `suspended`) are
  present when users visit the account hub or generation entry points.

If those signals are missing, the priority order below is provisional and should
be revisited after one beta measurement cycle.

## Prioritization Method

Rank experiments in this order:

1. unblock first successful story generation for new eligible users;
2. clarify cost, credits, and trust at the moment a user is deciding whether to
   generate;
3. improve upgrade intent only after a user has seen story value;
4. defer generic visual polish that does not move one of the funnel outcomes
   above.

An experiment should move down the backlog if it depends on a surface that does
not yet exist in the shipped shell or if it cannot be evaluated against one of
the funnel definitions in this document.

## Prioritized Experiment Backlog

### P0 Measurement Baseline For Onboarding And Conversion

Surface
- Auth completion, wizard steps, character create/upload flow, generation
  progress, account hub, and checkout entry points.

Hypothesis
- The team cannot confidently rank onboarding and conversion polish without a
  shared beta funnel baseline across first story completion and checkout start.

Defined change
- Capture the funnel events in this spec and review them by weekly cohort before
  promoting or cutting later experiments.

Primary evaluation
- A dashboard or equivalent report can show conversion between
  `signup_completed`, `wizard_started`, `review_reached`,
  `generation_started`, `first_story_completed`, `checkout_started`, and
  `paid_activated`.

Guardrail metrics
- Event coverage for the core funnel should be high enough to compare cohorts.
- Entitlement state and generation outcome need to be joinable for the same
  user journey.

Dependencies
- Existing entitlement and billing runtime surfaces.
- Beta usage data.

### P1 First-Run Wizard Orientation

Surface
- Wizard step 1 and the review step in the existing story-creation flow.

Hypothesis
- New users who understand what the wizard does, what inputs matter, how long
  generation may take, and when credits are used will reach review and start a
  first generation more often.

Defined change
- Add a first-run help panel that explains the four-step flow, expected output,
  typical generation timing, and when a story-generation credit is consumed.
- Reuse the trust-copy spec for ownership and outage wording rather than adding
  new policy language here.

Primary evaluation
- Improve `wizard_started` to `review_reached` and `review_reached` to
  `generation_started` for first-time eligible users.

Guardrail metrics
- No increase in support contacts about hidden charges or unclear trial usage.
- No decrease in `generation_started` caused by overloading the step with too
  much copy.

Decision rule
- Promote if the experiment materially improves review reach or generation start
  without increasing early abandonment.

Dependencies
- P0 measurement baseline.
- Trust-copy deck in `docs/specs/launch-trust-support-outage-copy-spec.md`.

### P1 Outline Examples And Quality Guidance

Surface
- Wizard step 1 outline input and adjacent helper content.

Hypothesis
- A blank outline box makes first-run users hesitate; concrete examples and
  quality guidance will increase completed outlines and first story starts.

Defined change
- Provide a small set of example outlines and short guidance on what makes a
  strong prompt for the current product.
- Keep examples tied to existing story-generation inputs rather than a broad
  inspiration gallery.

Primary evaluation
- Improve completion of step 1 and increase `review_reached` for users with no
  prior completed story.

Guardrail metrics
- No increase in low-quality or repetitive generated stories that trigger
  obvious regret or immediate abandonment.
- No misleading claim that examples guarantee a specific output quality.

Decision rule
- Promote if example use correlates with higher first-story completion for new
  users.

Dependencies
- P0 measurement baseline.
- Existing wizard structure in the shipped frontend.

### P1 Character-Photo And Reference-Image Education

Surface
- Character creation flow, character-photo upload flow, and the wizard's
  character step.

Hypothesis
- Users who understand that uploaded photos are private by default, what kinds
  of photos are appropriate, and how reference generation affects story quality
  will complete character setup more often and abandon less often before their
  first story.

Defined change
- Add concise education around private-photo handling, acceptable uploads, and
  when using a photo helps versus when a text-only character is enough.
- Keep this guidance in-product near character actions instead of burying it in
  policy docs.

Primary evaluation
- Improve `wizard_started` to `generation_started` for users who enter the
  character flow before their first story.

Guardrail metrics
- No increase in unsafe ownership claims beyond the current copyright and AI
  disclosure docs.
- No increased upload failure loop caused by adding too much friction.

Decision rule
- Promote if the experiment increases successful character completion or first
  story completion among photo-flow users.

Dependencies
- Trust-copy deck and legal docs.
- Existing private-photo behavior already documented in the repo.

### P1 Generation Expectation Setting During Review And Progress

Surface
- Wizard review step and generation progress state.

Hypothesis
- Users who know that generation can take time, may slow down during provider
  issues, and will preserve existing stories even when new generation is paused
  are less likely to abandon after clicking generate.

Defined change
- Strengthen expectation-setting copy at generation start and during progress.
- Clarify the difference between slow generation, temporary unavailability, and
  credit exhaustion using the existing state model.

Primary evaluation
- Improve `generation_started` to `first_story_completed` for first-time users.

Guardrail metrics
- No increase in repeated generate attempts while a request is already running.
- No misleading claim about guaranteed turnaround times or automatic credits.

Decision rule
- Promote if first-story completion rises or duplicate-start confusion drops for
  the same traffic cohort.

Dependencies
- Existing progress-state model and outage copy spec.
- P0 measurement baseline.

### P2 First-Value Conversion Prompt In Account Hub

Surface
- Account hub for `trial` and `grace` users after they complete at least one
  story.

Hypothesis
- Conversion improves when upgrade prompts appear after the user has already
  seen value and can compare remaining credits against a single paid plan.

Defined change
- Present a plan summary, remaining credits, renewal logic, and a single clear
  checkout action in the account hub once the user has completed a story.
- Keep the prompt factual and tied to the beta entitlement model rather than a
  broad marketing page.

Primary evaluation
- Improve `first_story_completed` to `checkout_started` for eligible trial or
  grace users.

Guardrail metrics
- No drop in `first_story_viewed` caused by pushing upgrade too early.
- No mismatch between displayed credits or renewal state and backend
  entitlement data.

Decision rule
- Promote if checkout starts improve without hurting first-story engagement.

Dependencies
- Entitlement/account hub surfaces.
- P0 measurement baseline.

### P2 Upgrade Timing At Credit-Limit And Quota States

Surface
- Generation-locked, exhausted-credit, or quota-blocked states in the wizard,
  progress, preview, and account hub surfaces.

Hypothesis
- Users are more likely to start checkout when the upgrade prompt explains what
  remains available now, what is blocked, and how paid access restores
  generation.

Defined change
- Standardize quota-state upgrade prompts around the current entitlement model:
  continue editing and export, but require paid access or renewal for new
  generation.
- Reuse the existing exhausted-credit and outage state language instead of
  inventing a new paywall voice.

Primary evaluation
- Improve `checkout_started` for users who encounter `grace` or quota-blocked
  states.

Guardrail metrics
- No false-positive upgrade prompts during temporary outage or provider
  fail-safe states.
- No suppression of useful non-generation actions such as edit, preview, or
  export.

Decision rule
- Promote if blocked users start checkout more often without higher support load
  from confusing locked-state messaging.

Dependencies
- PRD section 3.8 entitlement rules.
- Trust/outage copy spec.

### P3 Ownership And Publishing Confidence After First Story

Surface
- Story preview, export entry points, and account help surfaces after first
  story completion.

Hypothesis
- Users who quickly understand what they can review, edit, export, and publish
  with care are more likely to treat the first story as valuable and continue
  toward paid usage.

Defined change
- Add a concise ownership and review reminder that points users back to the
  existing policy summary without forcing a long legal detour.
- Keep the message focused on confident next steps: review, edit, export, and
  confirm rights before publishing.

Primary evaluation
- Improve `first_story_completed` to `first_story_viewed` and, secondarily, to
  `checkout_started`.

Guardrail metrics
- No new promise of commercial-use rights beyond the current policy documents.
- No drop in export completion caused by heavy legal copy.

Decision rule
- Keep only if the reminder improves downstream engagement or reduces support
  confusion.

Dependencies
- Copyright and IP policy.
- Trust-copy deck.

## Backlog Items Intentionally Deferred

The following are intentionally out of scope for issue #135 and should not be
pulled into this backlog unless a later issue changes product goals:

- a net-new pricing strategy, multiple plan tiers, or credit-rule changes;
- a standalone marketing site or homepage redesign not tied to the in-product
  funnel;
- email nurture campaigns, win-back campaigns, or CRM automation;
- live chat, support SLAs, or new support-channel commitments;
- editor-focused feature growth after generation, except where it directly
  helps first-story confidence;
- enterprise packaging, DPA workflow, team seats, or invoicing expansion;
- speculative visual polish without a measurable activation or conversion
  hypothesis.

## Execution Notes For Future Product And Frontend Work

- Start with one activation experiment at a time until the team can identify the
  largest first-run drop-off in beta data.
- Do not ship multiple onboarding changes together if that makes the funnel
  impossible to interpret.
- When a later implementation issue is opened, it should cite the experiment ID
  or section heading from this document and the baseline metric it aims to move.
- If the trust/support copy deck or entitlement rules change, review this
  backlog in the same release to remove stale assumptions.