# UI redesign verification

Verified on 2026-10-06 against implementation commit `f2932ac` on `codex/build-sentinelops`.

## Build and runtime

- Frontend ESLint passed, including accessibility rules. Named scroll regions have a narrowly scoped tabindex allowance for keyboard scrolling.
- Strict TypeScript checks passed.
- Existing frontend/API proxy tests: 6 passed.
- Standard `npm run build` passed. A webpack production build also passed during the development compiler investigation.
- Final Docker dashboard build passed using the existing lockfile and cached dependency installation.
- Dashboard image: `sha256:067fbda1258a8c84d3f042fe5f46f3abc303dabeca337d0e5d56453e1c34237f`.
- Dashboard available at `http://127.0.0.1:13000`; existing API and bounded demo remain on ports 18000 and 18001.
- No dependencies added and no backend/API contract changes.

## Actual local incident workflow

[Browser report](redesign-e2e.json): 23 checks passed, with no browser page exceptions.

Incident `bcc682e2-40ec-47ab-9833-a348104f6ff8` reached approval after the real bounded demo service degraded. Evidence, multiple hypotheses, and historical matches populated. A direct execution attempt before approval returned 409. The UI presented the exact plan, required acknowledgement, recorded approval, and executed rollback.

Recovery checks collected five fresh samples. Error rate moved from 18% to 0.2%, and p95 latency from 1680 ms to 85 ms. The real demo orders endpoint returned successfully after rollback. Postmortem generation and JSON download passed. Timeline order and the durable approval/execution/verification audit records were verified. Two new proxy SSE streams returned persisted-state resync events.

Metrics are deterministic local provider observations. The bounded demo HTTP service is real; these checks do not establish production telemetry or GCP behavior.

## Responsive, interaction, and accessibility checks

- Nine routes checked at 390, 768, and 1440 pixels: 27 combinations, zero page-level horizontal overflow.
- Landing workflow, registry search/filter, metric sample windows, command navigation, all incident tabs, and direct postmortem navigation passed.
- Simulator restart, pause, resume, and speed controls passed.
- Approval drawer cancellation, acknowledgement reset, and keyboard focus containment passed.
- [State checks](redesign-state-checks.json): 8 checks passed, including visible loading, keyboard tab navigation, changed-plan blocking, rejected approval without execution, command empty state, and unknown-route 404.
- Loading/error/empty and changed-plan/approval-failure checks use isolated browser fixtures; they do not mutate backend state.
- [Accessibility report](redesign-accessibility.json): axe-core 4.13.0, WCAG 2 A/AA and 2.1 AA tags, 18 view checks, zero detected violations. Includes all primary pages, incident tabs, expanded structured evidence, and approval/command dialogs.

Automated accessibility checks and exercised keyboard interactions do not replace a complete screen-reader and cross-browser audit. Chrome was the browser used for this verification.

## Visual review

[Design decisions and screenshot index](../UI_REDESIGN.md) document the before/after checkpoints. Rendered review led to improved simulator placement, removal of stretched empty panels, incident evidence summaries, more precise chart timestamps, preserved revision casing, stronger step-label contrast, keyboard-focusable scroll regions, and the metric-window interpretation panel.

No known blocking issues remained in the tested local workflow. Real GCP integration retains its earlier unverified status.
