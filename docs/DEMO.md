# Demo runbook (recording script)

All commands are run from `qa-orchestrator/` in PowerShell with the venv active.
Docker Desktop must be running; the app stack (db, backend, mailpit) must be up (`qa app status`).

## One-time setup
```powershell
cd "C:\Users\bansa\OneDrive\Desktop\Damco assignment\qa-orchestrator"
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .
npm install
npx playwright install chromium
claude --version        # local Claude Code must be installed and logged in
```
Start the app (only the first time, or after a reboot):
```powershell
cd ..\full-stack-fastapi-template
docker compose up -d --build db backend mailpit
docker compose exec -T backend bash -c "cd /app/backend && bash scripts/prestart.sh"   # migrations + admin user (first time only)
cd ..\qa-orchestrator
```

## Before recording: clean slate
```powershell
qa reset-demo --deploy      # clears runs + Mailpit, app back on master, plan stays approved
qa app status               # expect: master @ aabb901, healthy
```

## Scene 1: happy run (verdict Go)
```powershell
qa run --label happy        # 31 API + 17 UI tests, builds report + dashboard
qa email                    # then open http://localhost:8025 to show the email
```

## Scene 2: sabotage the app on a new branch
```powershell
qa sabotage apply           # creates branch demo/sabotage in the app repo with 2 deliberate bugs
git -C ..\full-stack-fastapi-template --no-pager diff master demo/sabotage     # show the planted bugs (--no-pager: no "(END)" prompt)
qa app deploy               # rebuilds the backend container from the sabotage branch
```

## Scene 3: run on the sabotaged app, see failures and impacted area
```powershell
qa run --label sabotaged    # expect 3 failures (TC-017, TC-043, TC-005), verdict No-Go
qa triage                   # AI groups failures into defects, names the suspect file, writes defect reports
qa email                    # No-Go email with failing modules; show it in Mailpit
```
Open `runs\<latest>\report.html` (and `runs\<latest>\defects\DEF-00x.md`) to show the impacted modules.

## Scene 4: your decision per defect (human in the loop)
```powershell
qa decide                   # interactive. DEF about GET /items leaking data -> press c (fix CODE)
                            #              DEF about password length 8 -> 10  -> press t (update TEST)
qa fix                      # shows each proposed diff and asks y/N before applying
```
(Defect numbers depend on the AI's ordering; choose by title. Non-interactive form:
`qa decide --defect DEF-001 --choice code`, `qa fix --yes`.)

## Scene 5: verify, expect 100%
```powershell
qa app deploy               # redeploy with the code fix
qa run --label fixed        # 48/48, verdict Go, both defects auto-closed
qa email
start dashboard\index.html  # trend: Go -> No-Go -> Go, defects Closed
```

## Scene 6: a developer's PR keeps the automation up to date (48 -> 50 tests)
```powershell
qa feature apply --pr       # plays the developer: branch feature/item-search + a real PR on your fork (prints the PR number)
qa pr-sync --pr 1           # QA agent reads the PR: impact analysis, existing cases at risk, proposes 1 API + 1 UI case
                            # (use the PR number printed above; checks the PR branch out in the app repo)
```
Review `runs\<latest>\test_cases.json` (the two new cases TC-050/TC-051), then approve (Gate 1 again):
```powershell
qa run                      # (optional) shows the gate refusing: plan not approved
qa approve plan
qa generate all --new-only  # writes tests ONLY for the new cases, in new files; existing tests untouched
qa app deploy               # deploy the PR branch
qa run --label pr-feature   # 50 tests (32 API + 18 UI); report shows change under test + new cases
qa email
start dashboard\index.html
```
No GitHub? Use a local branch instead: `qa feature apply` then `qa pr-sync --branch feature/item-search`.

## After recording
Collect the real evidence for the submission first (reset deletes the run folders), then commit it:
```powershell
qa package                  # copies reports, defect reports, screenshots, dashboard into submission\evidence
git add submission; git commit -m "Add recorded-run evidence"; git push
qa reset-demo --deploy
```
