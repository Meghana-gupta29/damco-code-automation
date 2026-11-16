# QA Lead Build Challenge: Agentic QA Workflow

An agentic QA workflow that takes one business flow of an open-source app from test design to a release-readiness
verdict, with human review gates, defect triage, a fix-or-update decision, and PR-driven test maintenance.

- **Application under test:** [full-stack-fastapi-template](https://github.com/fastapi/full-stack-fastapi-template)
  (FastAPI + React + Postgres), run locally in Docker. Fork used for PRs: `Meghana-gupta29/damco-code-opensource`.
- **Flow tested:** sign-up, login, items create/edit/delete (with ownership isolation), user settings and password change.
- **Orchestrator:** a Python CLI (`qa`). Agents are prompt files in `.claude/agents/`, run through the local Claude Code
  CLI (`claude -p`). No API key is needed. An Anthropic API provider is stubbed for later hosted use.

## Deliverables

| # | Deliverable | Where | Status |
|---|---|---|---|
| 1 | Source repo with agents, prompts, test code, README | this repo; agents in `.claude/agents/`, run instructions below | Done |
| 2 | Architecture diagram (roles, inputs/outputs, tools, human review) | [architecture.md](architecture.md), visual: [flowchart.html](flowchart.html) | Done |
| 3 | Test strategy note | [test-strategy.md](test-strategy.md) | Done |
| 4 | Generated artifacts: test cases, API and UI scripts, sample defects | cases: [test-plan.md](test-plan.md) (source: `runs/run-20261116-093132/test_cases.json`); API: `generated/api/`; UI: `generated/ui/`; defects: `evidence/` (see note) | Defects: pending recording |
| 5 | QA dashboard (summary by suite, defects, trend, verdict) | `dashboard/index.html` and `evidence/*/report.html` | Pending recording run |
| 6 | AI evaluation note | [ai-evaluation.md](ai-evaluation.md) | Done |
| 7 | Demo recording | to be added | Pending |

**Evidence note:** run outputs are produced by the demo. After recording, run `qa package` to copy real reports, defect
reports, failure screenshots and the dashboard into `submission/evidence/`. Nothing in that folder is hand-written.

**Not attempted:** performance testing (optional in the brief).

## Minimum evidence required by the brief

| Requirement | Result |
|---|---|
| At least 15 API tests executed | 31 API tests (32 after the PR-driven addition) |
| At least 10 UI E2E tests executed | 17 UI tests (18 after the PR-driven addition) |
| Defect reports with steps and evidence | produced by `qa triage`, one markdown file per defect |
| Trend across at least 2 runs | dashboard shows every run: happy, sabotaged, fixed, PR feature |
| Go / No-Go verdict with reasoning | rule-based verdict in every report |

## How to run

Prerequisites: Windows with Docker Desktop, Python 3.10+, Node 18+, Git, GitHub CLI (logged in), local Claude Code
(logged in). Full runbook: [../docs/DEMO.md](../docs/DEMO.md).

```powershell
# one-time
git clone https://github.com/Meghana-gupta29/damco-code-automation.git qa-orchestrator
cd qa-orchestrator
python -m venv .venv; .venv\Scripts\Activate.ps1
pip install -e .
npm install; npx playwright install chromium

# app under test (sibling folder: ../full-stack-fastapi-template, cloned from the fork)
cd ..\full-stack-fastapi-template
docker compose up -d --build db backend mailpit
docker compose exec -T backend bash -c "cd /app/backend && bash scripts/prestart.sh"
cd ..\qa-orchestrator

# happy run
qa run --label happy
qa email            # report arrives in Mailpit: http://localhost:8025
```

Command reference:

| Command | Purpose |
|---|---|
| `qa init`, `qa plan` | discover the app, AI writes the test plan |
| `qa approve plan` | Gate 1: human approves the plan (hash recorded) |
| `qa generate api\|ui\|all [--new-only]` | AI writes the tests for approved cases |
| `qa run [--label x]` | run API and UI suites, build report, dashboard and verdict |
| `qa triage` | AI classifies failures into defects with a suspect file |
| `qa decide`, `qa fix` | Gate 2: human chooses fix the code or update the test; AI proposes, human confirms the diff |
| `qa sabotage apply`, `qa app deploy` | demo: plant bugs on a branch and redeploy |
| `qa feature apply --pr`, `qa pr-sync --pr N` | demo: developer PR, AI analyses impact and proposes new cases |
| `qa email` | send the report (to Mailpit by default) |
| `qa package` | copy run evidence into `submission/evidence/` |
| `qa reset-demo [--deploy]` | return to the pre-recording state |
