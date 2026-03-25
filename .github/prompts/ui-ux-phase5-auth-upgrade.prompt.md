# UI / UX Phase 5 Prompt: Auth and Upgrade Surfaces

```text
Use English.

You are aligning account and upgrade surfaces to the same calm, premium product language established in the main workspace.

Scope:
- sign-in and sign-up experience
- auth form hierarchy
- OAuth button presentation
- supporting helper states
- upgrade surfaces inside the app shell
- plan and billing call-to-action presentation

Primary files to inspect and likely edit:
- frontend/src/pages/AuthPage.js
- frontend/src/components/AppShell.js
- frontend/src/App.css

Current realities to preserve:
- auth modes already exist for sign in, sign up, magic link, and forgot password
- the auth page already has a structured card layout and OAuth buttons
- upgrade actions already appear in the app shell
- working auth and checkout behavior must remain intact

Problems this phase should solve:
- auth should feel more consistent with the calmer product language used elsewhere
- the page should feel trustworthy and modern without becoming generic SaaS UI
- upgrade controls in the shell should feel integrated instead of bolted on
- plan state and account context should read clearly without crowding the shell

Design direction:
- keep the auth page minimal, confident, and easy to scan
- reduce any remaining visual mismatch between auth and the practice product
- treat upgrade messaging as a product affordance, not a hard sales push
- make plan state visible but not distracting

Implementation guidance:
- do not alter auth logic or checkout flow
- keep helper text concise and reassuring
- use the same spacing, border, surface, and accent language established in earlier phases
- keep the upgrade surface professional and respectful

Specific goals:
- refine auth topbar and auth-card rhythm
- improve OAuth button hierarchy and form spacing
- tune alert, helper, and post-success states
- simplify the shell upgrade-action grouping
- make plan status and session context more polished

Acceptance checks:
- auth feels like part of the same product family
- upgrade controls feel calmer and more intentional
- account context is easier to understand without noise
- tests and build still pass
```
