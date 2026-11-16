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
git -C ..\full-stack-fastapi-template diff master demo/sabotage     # show the planted bugs
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

## After recording
```powershell
qa reset-demo --deploy
```
