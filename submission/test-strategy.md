# Test strategy

## Application and flow chosen
**App:** full-stack-fastapi-template (FastAPI backend, React frontend, Postgres), a realistic open-source product with
authentication, per-user data, an admin console and a generated API client. Run locally with Docker Compose.

**Business flow:** *new user to managing their own data*: sign-up, login, create / edit / delete items, change profile
and password. This flow carries the main business risks of a multi-user app: authentication, validation, and
**data isolation between users**.

## Scope
| In scope | Out of scope |
|---|---|
| API: sign-up, login and token, users (me, update, password, delete), items CRUD, ownership rules, admin-only endpoints, auth failures (401/403), validation (422), boundary lengths | password-recovery email flow and reset-password UI |
| UI: sign-up form, login, logout, protected-route redirect, items add / edit / delete / empty state, user settings and password change, admin page access control | admin user-management UI beyond an access-control check |
| Developer-PR changes to the above (item search used as the demo change) | performance and load testing (optional in the brief, not attempted) |
| | security testing beyond authorization checks, accessibility, cross-browser (Chromium only) |
| | deployment, infrastructure, third-party services |

## Test design approach
- An AI test designer produces cases per layer with type (positive, negative, boundary), priority (P1 to P3) and the
  source module each case exercises. A human reviews and approves the plan (Gate 1) before any code is written.
- Current plan: 48 approved cases (31 API, 17 UI); 50 after the PR-driven addition. Every case maps to a source file,
  which is what lets reports show *modules covered* and lets triage name a suspect file.
- API tests verify behavior through the HTTP contract, including side effects (for example, after a blocked update the
  other user's item is still unchanged). UI tests verify user-visible outcomes only.
- Error-message text is not asserted unless the requirement is the message itself. 401 cases assert the status only.

## Risks and how the suite addresses them
| Risk | Mitigation |
|---|---|
| Data leak between users (highest impact) | P1 cases on list, read, update and delete across two users, in both API and UI |
| Weak authentication or validation | negative and boundary cases on sign-up, login, password change |
| Regression from developer changes | change analyst flags at-risk existing cases on every PR; full suite re-run |
| AI-written tests are wrong or shallow | human plan approval, coverage check, diff review, failures triaged as test issue vs product bug |
| Flaky UI tests | independent tests, unique data, auto-waiting assertions, no fixed sleeps, single worker; two consecutive green runs required |
| Overfitting tests to current behavior | cases come from the plan, not from the code; the triager is told to question whether a change is a bug or a policy change |

## Test data and environment
- Every test creates its own users and items through the API with unique emails and titles, and deletes the users
  afterwards through the admin API. Tests never assert on global counts and never depend on pre-existing data.
- One shared superuser from the app's seed data is used only for cleanup and the admin-access cases.
- Environment: Docker Compose on the tester's machine; the app image is rebuilt from the branch under test
  (`qa app deploy`). Email is captured by Mailpit. `qa reset-demo` restores a known state.

## Entry criteria
- Plan approved (hash recorded); app healthy at its health-check endpoint; app commit recorded in the run metadata.
- For PR-driven runs: PR diff available and the new cases approved.

## Exit criteria and release verdict
The verdict is computed by code, not by the agent:

| Verdict | Condition |
|---|---|
| **No-Go** | any P1 test failing, or any open Sev1/Sev2 defect, or overall pass rate below 90% |
| **Go with risks** | only P2/P3 failures or skipped tests, pass rate at least 90% |
| **Go** | all executed tests pass and no open defects |

Severity guide used by triage: Sev1 security or data leak, Sev2 core flow broken, Sev3 minor or edge case, Sev4 cosmetic.

## Defect handling
Failures are grouped by root cause into defects (id, severity, classification, suspect module, steps, expected,
actual, evidence). The AI recommends; a human decides per defect whether the **code** or the **test** is wrong.
Fixes and test updates are applied only after the human confirms the diff, and a defect closes automatically when
its tests pass in a later run.
