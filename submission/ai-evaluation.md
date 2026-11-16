# AI evaluation note

Agents are the local Claude Code CLI (Sonnet-class model) driven by prompt files. This note covers what actually
went wrong in building and running the workflow, how each problem was caught, what a run costs in time, and what
should not be delegated to an agent.

## Where the agents got things wrong, and how it was caught

| # | What happened | How it was caught | Resolution |
|---|---|---|---|
| 1 | **Plan quality:** the first plan had an ambiguous case (a test-token call "without authorization" read as if a user could be authorized before login), assertions on exact error-message text, and a case that duplicated another. | Human review at Gate 1. | Case removed or reworded; two business-endpoint no-token cases added; message assertions relaxed to status codes. This is the value of Gate 1: the plan was edited before any code existed. |
| 2 | **Ghost test:** after a case was deleted from the plan, the API test agent still emitted a skipped placeholder test for the deleted id. | The result mapping showed a test id absent from the plan. | Placeholder removed. The generator now fails if a test references an id not in the approved plan, or an approved case has no test. |
| 3 | **Test written against the wrong UI behavior:** a UI delete test failed because, after Cancel, the row-actions menu stays open and hides the table from role-based queries. | The failure screenshot showed the item still present; this was classified as a *test issue*, not a product bug. | Test now presses Escape before re-checking the row. A reminder that the first red result is not always a product defect. |
| 4 | **Helper misuse:** for the PR-driven UI test the agent called shared helpers with the wrong signatures (positional arguments instead of an options object, an email instead of a user id), which would fail at login. | Reading the generated code before running it. | Root cause was ours: the prompt contained helper names, not their source. Both generation prompts now include the helper source. |
| 5 | **Tooling leak:** the first plan generation failed because the nested `claude -p` inherited the parent session's environment and answered an unrelated task. | The output was not valid JSON (schema validation failed twice). | The provider strips inherited session variables, disables tools and persistence, and passes the prompt on stdin. |
| 6 | **Overconfidence risk in triage (observed as a *good* behavior):** for a password minimum raised from 8 to 10, the triager said it could be a deliberate policy change or an accidental regression, pointing out the rule was now inconsistent across entry points, and gave low confidence. | Reading the defect report. | This is exactly why Gate 2 is a human decision. The agent's recommendation was treated as advice. |

Things the agents got right and that held up: grouping two failures with one root cause into a single Sev1 defect and
naming the removed filter line; a minimal code fix that restored the owner filter without touching the unrelated change;
a test update that moved the boundary to 9 rejected / 10 accepted and amended the plan; and, on the developer PR, flagging
six existing cases as regression risks because the list logic had been rewritten.

## Cost and time of a run

Measured wall-clock times on a laptop (agent calls are local Claude Code calls):

| Step | Time |
|---|---|
| Test plan generation (48 cases) | about 35 s |
| API test generation (31 tests) | about 35 s |
| UI test generation (17 tests) | about 47 s |
| Execute: API suite / UI suite | about 9 s / about 25 s |
| Triage (3 failures, 2 defects) | about 18 s |
| Fix: code fix plus test update | about 27 s |
| PR analysis, then incremental test generation | about 20 s, about 19 s |
| App rebuild and redeploy (cached layers) | 12 to 23 s |

A full cycle (plan, generate, execute, triage, fix, PR update) uses nine agent calls. **Token usage and money were not
measured**: the local CLI runs on a subscription and the workflow does not log usage. When switching to the API provider,
usage should be recorded per agent call. Human time is not included above; it is dominated by plan review and the
Gate 2 decision, which is intended.

## What I would not trust an agent to do

- **Decide whether the code or the test is wrong.** Both can be defensible (policy change vs regression). It stays a human gate.
- **Approve its own plan or scope.** The hash gate exists so approved scope cannot drift.
- **Set the release verdict.** Computed by rule from priorities, severities and pass rate, so it is explainable and repeatable.
- **Apply changes without a diff.** Fixes rewrite whole files; every change is shown and confirmed.
- **Judge coverage.** Agents count tests, not exercised code. The coverage here is a mapping from cases to modules, not code coverage.
- **Judge severity of security issues unreviewed.** Severity is a recommendation; a data leak should be confirmed by a person.
- **Write UI tests without running them.** UI tests only count once they pass twice in a row against the live app.
- **Run against real or production data.** Everything here targets a disposable local stack.
