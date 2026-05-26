# Story Preview & Editor — UI/UX Review

Date: 2026-05-26
Scope: Story Preview section (read-only) and Edit Mode in the frontend SPA.
Audience: Product, Frontend.
Status: Review and recommendations only. No code changes proposed in this pass.

> Historical-note convention: this document is a point-in-time review. The
> current product contract still lives in the repo-root README, CONFIG, the
> PRD, and the code under [frontend](../../frontend/).

## 1. Summary

The Story Preview is functional and covers all the editor responsibilities
called out in the PRD (per-page text/image edit, regenerate, restore, structural
page edits, document defaults, PDF preview/export, undo/redo, autosave). The
read-only preview is clean.

Edit mode is where the UI becomes cluttered:

- Each page card exposes up to **11 action buttons** in a single header row,
  almost all using the same neutral grey styling.
- Several controls overlap conceptually (Text Position vs Text Alignment;
  Regenerate vs Restore; Add Page After vs Duplicate).
- Destructive and structural actions sit next to high-frequency actions with
  no visual hierarchy or grouping.
- The top toolbar mixes title, cover subtitle, cover author, undo/redo, save
  status, retry, save, and "Back to Preview" in one wrapping row.

The result is a screen that works but is visually noisy, hard to scan, and
intimidating for the "basic users who want desktop publishing control without
professional design knowledge" target persona called out in the PRD.

## 2. What the user sees today

### 2.1 Read-only Story Preview

- One header (`Story Preview`).
- Per-page rendered preview.
- Two buttons at the bottom: `Preview PDF`, `Export as PDF`.

This screen is in good shape. The recommendations below focus on Edit Mode.

### 2.2 Edit Mode top toolbar

Currently a single flex row containing:

- Story Title input
- Cover Subtitle input
- Cover Author input
- `Back to Preview`
- `Undo` / `Redo`
- Save status pill (`Saving...` / `Saved 12:34:56` / `Save failed...`)
- `Retry save` (conditionally visible)
- `Save`

### 2.3 Document Defaults sidebar

A vertical list of: Layout Mode, Font, Font Size, Font Colour + swatches,
Text Position (V + H selects), Text Alignment, Readability Treatment, Text Box
Opacity slider with live percentage.

### 2.4 Per-page card

Each non-cover page card header shows, left-to-right:

1. `Restore Text`
2. `Restore Image`
3. `Regenerate Text`
4. `Regenerate Image`
5. `Add Page After`
6. `Duplicate`
7. `Move Up`
8. `Move Down`
9. `Split`
10. `Merge Next`
11. `Delete`

The body of each card then shows:

- Page text textarea
- Text Position Override (two selects)
- Text Alignment Override
- Font Size Override
- Font Colour Override + swatches
- Text Box Opacity Override slider
- `Use Document Defaults` button

That is roughly 17 interactive controls per page. For a 12-page story that is
almost 200 controls on one screen.

## 3. Findings

### 3.1 Button overload on each page card

- 11 actions in a single row produce a "wall of grey pills".
- Almost all share `action-button-secondary` styling (uniform grey). The two
  exceptions (`Regenerate Text`, `Regenerate Image`) use `action-button-info`
  blue, but they are buried in the middle of the row.
- `Delete` is styled as `action-button-secondary` rather than the existing
  `action-button-danger` variant. Destructive actions should be visually
  distinct.
- On narrow viewports the row wraps to multiple lines, which destroys whatever
  ordering meaning was implied.

### 3.2 Overlapping or confusing controls

- `Restore Text` vs `Regenerate Text` vs `Undo`: users will reasonably ask
  "what does Restore do that Undo does not?" Answer: Restore returns to the
  *originally generated* text; Undo steps back one edit. That distinction is
  not surfaced in the UI.
- `Restore Image` vs `Regenerate Image`: same pattern, same confusion.
- `Add Page After` vs `Duplicate`: both create a new page after the current
  one; only the seed content differs.
- `Text Position Override` (V + H) vs `Text Alignment Override`: the V/H
  position selects already encode horizontal anchor; a separate alignment
  control is needed for true text alignment but the relationship is not
  explained.
- `Merge Next` reads as a verb on the next page. "Merge with next page" is
  clearer.

### 3.3 Hierarchy and grouping

- There is no visual separation between **content actions** (Regenerate /
  Restore text and image), **structural actions** (Add / Duplicate / Move /
  Split / Merge / Delete), and **override actions** (clear overrides, change
  per-page styling).
- Document defaults and page overrides use the same labels and visuals,
  separated only by the word "Override". A user can edit a per-page Font Size
  Override and not realize they have not changed the document default.

### 3.4 Always-visible buttons that are usually no-ops

- `Restore Text` and `Restore Image` are visible even when the page has never
  been edited or regenerated. They do nothing useful in that state but still
  occupy space and visual weight.
- `Move Up` / `Move Down` render as disabled buttons on the first/last
  movable page, still consuming space.

### 3.5 Top toolbar density

- Title, Cover Subtitle, Cover Author, history controls, save state, retry,
  and Save sit on the same row. On most laptop widths this wraps awkwardly.
- Cover Subtitle / Cover Author are only relevant when the user is thinking
  about the cover; they currently take horizontal space on every page edit.
- Save status, Save button, and Retry are three separate elements expressing
  one state machine.

### 3.6 PDF actions

- `Preview PDF` and `Export as PDF` live at the very bottom of the page
  outside the editor toolbar. After a long editing session the user has to
  scroll past every page to reach them.
- Inside the PDF preview modal, there is no "Download this PDF" action — the
  user must close the modal and use `Export as PDF` to actually download.

### 3.7 Accessibility and discoverability

- Buttons rely on text labels only; there are no icons, so scanning depends
  entirely on reading each label.
- `Use Document Defaults` is the only clear "reset" action and it lives at the
  end of the override panel; users who want to revert just one field have no
  per-field "use default" affordance.
- Disabled history buttons (`Undo`, `Redo`) and disabled `Move Up/Down` do
  not visually announce *why* they are disabled.

### 3.8 Cover page edge cases

- The cover page card still exposes `Add Page After`, `Restore Image`, and
  `Regenerate Image`, but hides per-page text/structure actions. The mixed
  set on the cover is harder to reason about than a clearly cover-specific
  control surface.

## 4. Recommendations

These are grouped by impact. The intent is a tighter, more scannable Edit
mode without removing capability.

### 4.1 Quick wins (low effort, high payoff)

1. **Restyle `Delete` as `action-button-danger`.** It is the only destructive
   page action; it should look like it.
2. **Hide `Restore Text` and `Restore Image` unless the page differs from
   its original.** This removes two buttons from most page headers.
3. **Hide `Move Up` / `Move Down` on the first / last movable page**, or
   render them as a single arrow control. Disabled-but-present buttons
   create permanent visual noise.
4. **Rename `Merge Next` to `Merge with next page`** for clarity.
5. **Move `Preview PDF` and `Export as PDF` into the sticky editor toolbar**
   alongside `Save`. Add a `Download` button inside the PDF preview modal.
6. **Group cover-only fields (Cover Subtitle, Cover Author) into a collapsible
   "Cover details" section** that auto-expands when the user focuses the cover
   page card.

### 4.2 Re-group the page card actions

Replace the single 11-button row with three clearly distinct groups:

- **Primary actions** (visible, labelled, icon + text):
  - `Regenerate text`
  - `Regenerate image`
- **Secondary actions** (visible, but compact icon buttons):
  - `Restore original` (text and image revealed only when applicable, with a
    small dropdown if both are applicable)
- **Structural actions** in an overflow menu (`More` / kebab `⋯`):
  - `Add page after`
  - `Duplicate page`
  - `Split page at cursor`
  - `Merge with next page`
  - `Move up` / `Move down` (or drag handle, see 4.5)
  - `Delete page` (visually red inside the menu)

Result: each page card header drops from 11 buttons to 3 visible buttons plus
an overflow menu.

### 4.3 Consolidate Regenerate + Restore

Combine `Regenerate text` and `Restore original text` into a split button:

```
[ Regenerate text ▾ ]
   ├ Regenerate text
   └ Restore original text   (disabled when not divergent)
```

Same pattern for images. This kills two buttons per page and removes the
"why is there Restore *and* Undo?" confusion by putting Restore where users
already expect a regenerate decision.

### 4.4 Tighten the top toolbar

Re-architect the editor toolbar into a sticky two-row strip:

- Row 1 (title strip): `Story Title` input, plus a small chip showing the
  current page being scrolled (e.g. "Editing: Page 3 of 8").
- Row 2 (action strip): `Undo` / `Redo`, save state pill (which itself can
  include `Retry` inline when save fails), `Preview PDF`, `Export as PDF`,
  `Save`, `Back to Preview`.

Move Cover Subtitle and Cover Author into the cover page card body, where
they are contextually relevant, and remove them from the global toolbar.

### 4.5 Replace per-page move buttons with a drag handle

This is already on the PRD backlog ("Page thumbnails with drag-and-drop
reordering"). Even before thumbnails, adding a drag handle on the left edge
of each page card and removing `Move Up` / `Move Down` would simplify both
the UI and the mental model.

If keyboard reordering must remain, expose it via the overflow menu (`Move
up` / `Move down`) rather than as always-on buttons.

### 4.6 Reconcile Text Position and Text Alignment

- Keep `Text Position` as the anchor control (vertical + horizontal anchor
  inside the page).
- Repurpose `Text Alignment` as a sub-control under Text Position with an
  inline helper text: "Alignment of text inside the chosen position".
- For per-page overrides, show a single "Position & alignment" group with a
  small "Reset to default" link beside it, instead of two separate override
  rows.

### 4.7 Per-field "use default" affordance

Each override field (Font Size, Font Colour, Text Box Opacity, Text Position,
Text Alignment) should have a tiny reset link or `↺` icon when it is
currently overridden. Keep the global `Use Document Defaults` button as a
"reset all overrides on this page" action for power users.

### 4.8 Visual hierarchy through colour and weight

Currently every page-card button is grey except the two regenerate buttons
in blue. Recommended palette use:

- `action-button-primary` (green): `Save` only.
- `action-button-info` (blue): high-value content actions — `Regenerate
  text`, `Regenerate image`, `Preview PDF`, `Export as PDF`.
- `action-button-secondary` (grey): low-frequency structural actions inside
  the overflow menu, plus `Back to Preview`, `Undo`, `Redo`.
- `action-button-danger` (red): `Delete page`, and the destructive confirm
  inside any confirm dialog.

### 4.9 Icons + text on buttons

Add lightweight inline icons (SVG, no extra dependency) to the visible
buttons. This is cheap and dramatically improves scannability for a dense
editor surface, especially when the same button group repeats N times for
N pages.

### 4.10 Confirmations for destructive actions

`Delete page` and (optionally) `Merge with next page` should both prompt a
small confirm dialog (or inline confirm pill) before applying. With autosave,
an accidental click is otherwise hard to recover beyond the bounded undo
buffer.

### 4.11 Responsiveness

The page card currently breaks into wrapped button rows on narrow widths.
Once the overflow menu pattern (4.2) is in place, the card naturally
collapses to 3 visible buttons + `⋯`, which fits most laptop widths cleanly
and degrades well on tablets.

## 5. Suggested phasing

A practical order that delivers user-visible cleanup quickly without forcing
a large refactor:

- Phase 1 (visual hygiene, no behaviour change):
  - 4.1 quick wins
  - 4.8 colour palette discipline
  - 4.10 destructive confirmations

- Phase 2 (page card restructure):
  - 4.2 group + overflow menu
  - 4.3 split-button for regenerate / restore
  - 4.9 icons + text

- Phase 3 (toolbar + overrides):
  - 4.4 sticky two-row toolbar with PDF actions inline
  - 4.6 reconcile Text Position vs Text Alignment
  - 4.7 per-field "use default" affordance

- Phase 4 (structural reorder model):
  - 4.5 drag handle / reorder UI (already in PRD backlog)

## 6. Out of scope for this review

- Backend or API changes. All recommendations are frontend-only.
- New editor capabilities beyond what the PRD already lists. This pass is
  about tightening what already exists.
- Mobile-first redesign. Recommendations improve responsiveness but the
  primary target remains desktop / laptop.

## 7. Acceptance checks for a follow-up implementation

Future implementation work should be able to verify:

- Each page card shows at most 3 visible action buttons plus an overflow
  menu.
- `Delete page` uses danger styling and requires confirmation.
- `Restore` actions appear only when the page has diverged from its
  original.
- `Preview PDF` and `Export as PDF` are reachable without scrolling past
  the last page.
- The editor toolbar remains usable at 1280px width without wrapping into
  three or more rows.
- All controls remain keyboard accessible and announce disabled-state
  reasons via `aria-disabled` + `aria-describedby` where applicable.
