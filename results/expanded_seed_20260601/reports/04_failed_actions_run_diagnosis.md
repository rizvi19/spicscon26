# Failed GitHub Actions Run Diagnosis

## Failed run inspected

- Run URL: `https://github.com/rizvi19/spicscon26/actions/runs/26751886269/job/78847152204`
- Failed run commit: `ad9008b`
- Dispatch branch shown by GitHub: `codex/expand-seed-evaluation-for-spicscon-paper-p2gsm7`

## First real failure

The first failure was the workflow step named `Require research evidence branch`. The workflow rejected the dispatch because it required `GITHUB_REF_NAME` to equal `codex/research-evidence-upgrades`, but the run was dispatched from `codex/expand-seed-evaluation-for-spicscon-paper-p2gsm7`.

The later `Fail workflow if evidence generation did not complete` error was only the final guard. Dependency installation, the smoke experiment, and the final ten-seed experiment did not start. Therefore, the failed run is an execution-routing failure, not a research result.

## Fix

The workflow now always checks out `codex/research-evidence-upgrades`, generates evidence from that branch, and commits generated outputs back to that same target branch. It reports the UI dispatch branch for traceability but no longer fails merely because the workflow was dispatched from a different UI branch.

The workflow also opts into Node.js 24 for JavaScript actions and prints status variables plus the tails of dependency, smoke, and final logs in an `if: always()` diagnostic step.
