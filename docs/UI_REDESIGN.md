# SentinelOps interface redesign

## Product direction

SentinelOps is an operations workspace organized around a decision: what changed, what evidence supports a diagnosis, and which exact action may an operator authorize?

The design uses graphite surfaces, warm white text, lime for navigation and controlled actions, coral for degradation, amber for approval gates, and lavender for latency and investigation. Color is reinforced by text and icons. Cutobot informed the landing page's negative space and central signal composition; the app uses compact operational layouts suited to incident response.

## Routes and experience

- `/`: product landing page with an SVG signal composition, actual workspace telemetry preview, interactive workflow explanation, and demo entry.
- `/overview`: operational overview. Health and next action come first, followed by summary metrics, annotated charts, incidents, a logical operations map, and investigation activity.
- `/incidents`: searchable registry with active, approval, resolved, and review filters, plus evidence and diagnosis summaries.
- `/incidents/[id]`: incident command with lifecycle progress, current service metrics, root cause and evidence score, supporting and contradicting records, ranked hypotheses, historical matches, timeline, exact-plan approval review, recovery checks, and postmortem.
- `/services`: observed service nodes and service-specific metric views.
- `/metrics`: correlated signals with sample-window selection, alert/recovery thresholds, and revision transition markers.
- `/deployments`: serving revision, deployment counts, impact charts, configuration changes, and revision timeline.
- `/postmortems`: recovery report registry; report links select the postmortem tab directly.
- `/system`: provider configuration, connection status, execution policy, and explicit local/cloud verification boundaries.

The existing resource and incident paths remain available. The former root dashboard is now `/overview`; the root is the requested landing page.

## Data and trust

API proxy, authorization, SSE, polling fallback, and backend action contracts are preserved. Data panels consume the existing provider responses. The landing preview uses the same live data source; conceptual workflow graphics are identified separately.

Revision markers derive from revision transitions in actual metric samples. A deployment health badge describes the recorded deployment; it does not claim that the current service has that same health. Configured adapters are labeled "configured", rather than being presented as independently healthy.

Incident metrics are filtered to the affected service. Root cause scores remain labeled as heuristic evidence scores, not calibrated probabilities. Approval review identifies incident, plan ID, expiry, target, parameters, and risk. Explicit acknowledgement enables execution; changing the plan ID invalidates the review. The backend remains authoritative for expiry, approval, execution claims, and verification.

## Accessibility and interaction

Native modal dialogs provide background inertness and Escape dismissal, with explicit focus wrapping at the tab boundary. Command navigation supports Ctrl/Cmd+K and focuses its search input. Tab groups support arrows and Home/End. The interface includes visible focus indicators, skip links, selected navigation states, labeled controls, readable empty/error states, and reduced-motion support.

Motion is confined to control feedback and the landing signal reveal. No continuously moving charts or decorative loops compete with operational information.

## Screenshot refinement

The first rendered review led to these changes:

1. Move simulation controls into the initial overview surface.
2. Remove stretched empty space beside the investigation activity list.
3. Add evidence and diagnosis metadata to incident rows, plus dates to ambiguous timestamps.
4. Show seconds on short metric timelines and reduce axis tick density.
5. Preserve API/revision casing in the remediation summary.
6. Keep keyboard focus within approval review and add complete keyboard tab navigation.
7. Keep the active incident action available on mobile.

## Implementation

The existing Next.js, React, Lucide, and Recharts stack is retained. No runtime or development dependencies were added. Formatting used a temporary Prettier invocation; it is not a project dependency.

`globals.css` contains shared layout foundations; `design.css` defines semantic tokens, product treatments, landing composition, and responsive refinements. `primitives.tsx` provides charts, badges, loading/empty states, incident lifecycle, and the logical operations map. `keyboard.ts` provides shared modal/tab keyboard behavior.

## Run locally

From `apps/dashboard` in PowerShell, with the existing backend on port 18000:

```powershell
$env:API_BASE_URL = 'http://127.0.0.1:18000'
$env:PORT = '13001'
npm run dev
```

Open `http://127.0.0.1:13001/` for the landing page and `/overview` for the app. Standard Docker Compose uses the configured dashboard port; see the root README for the complete local stack.

```powershell
npm run lint
npm run typecheck
npm test
npm run build
```

Run checks sequentially because type generation and production builds share `.next`. For browser verification against a running dashboard and local backend:

```powershell
python scripts/redesign_qa.py --dashboard-url http://127.0.0.1:13001 --api-url http://127.0.0.1:18000 --demo-url http://127.0.0.1:18001
```

The browser script runs a real local incident simulation and remediation. Empty/error states use isolated browser response fixtures; those are recorded separately from the actual backend flow.

## Visual checkpoints and verification

The updated Docker dashboard is running at `http://127.0.0.1:13000/` (landing) and `http://127.0.0.1:13000/overview` (workspace).

| View | Screenshot |
|---|---|
| Original overview | [Baseline](screenshots/redesign/before.png) |
| First overview pass | [Before refinement](screenshots/redesign/overview-first.png) |
| Landing page | [Desktop](screenshots/redesign/landing-1440.png) · [Mobile](screenshots/redesign/landing-390.png) |
| Overview | [Active incident](screenshots/redesign/overview-active.png) · [Recovered](screenshots/redesign/overview-1440.png) · [Mobile](screenshots/redesign/overview-390.png) |
| Incident command | [Investigation](screenshots/redesign/incident-command.png) · [Approval drawer](screenshots/redesign/approval-review.png) · [Mobile](screenshots/redesign/incident-resolved-390.png) |
| Resource views | [Services](screenshots/redesign/services-1440.png) · [Metrics](screenshots/redesign/metrics-1440.png) · [Deployments](screenshots/redesign/deployments-1440.png) |
| Reports and status | [Postmortem](screenshots/redesign/postmortem.png) · [System](screenshots/redesign/system-1440.png) |
| UI states | [Loading](screenshots/redesign/loading-state.png) · [Empty](screenshots/redesign/empty-state.png) · [Connection error](screenshots/redesign/error-state.png) · [Approval error](screenshots/redesign/approval-error-state.png) |

The final [verification report](verification/ui-redesign.md) records the tested build, actual local incident, browser checks, and test boundaries. Screenshot review drove the refinements described above. No known blocking UI issues remained in the tested local workflow. Live GCP remains outside this verification; browser checks used Chrome.

`python scripts/ui_state_qa.py --dashboard-url http://127.0.0.1:13000` checks loading, stale-plan protection, approval failure, keyboard tabs, and command navigation without mutating backend data. Both QA scripts accept `--axe-script /path/to/axe.min.js` to run an available axe-core installation. Axe was used from the machine's existing tool cache and adds no project dependency.
