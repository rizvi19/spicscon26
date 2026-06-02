# Expanded 10-Seed Runtime Summary

## Scope

This report summarizes runtime evidence already saved for the successful expanded 10-seed experiment. It does not rerun the experiment and should not be interpreted as a hardware runtime benchmark.

## Extracted runtime values

| Item | Value | Source |
| --- | ---: | --- |
| Smoke pipeline elapsed time | 23.450 seconds | `results/expanded_seed_20260601/logs/github_actions_smoke_command.log` |
| Final expanded 10-seed pipeline elapsed time | 115.672 seconds | `results/expanded_seed_20260601/logs/github_actions_final_command.log` |
| Total final run time | 115.672 seconds | `results/expanded_seed_20260601/logs/github_actions_final_command.log` |
| Workflow run | `https://github.com/rizvi19/spicscon26/actions/runs/26768081083` | `results/expanded_seed_20260601/reports/github_actions_run_status.md` |
| Branch recorded by workflow | `codex/research-evidence-upgrades` | `results/expanded_seed_20260601/reports/github_actions_run_status.md` |
| Status-report timestamp | `2026-06-01T16:53:51Z` | `results/expanded_seed_20260601/reports/github_actions_run_status.md` |

## Limitations of runtime logging

- Per-seed runtime is **not available** because seed-level elapsed timing was not recorded in the current logs.
- Per-stage runtime was not recorded in the current logs.
- The saved elapsed times cover the smoke and final pipeline command wrappers on a GitHub Actions runner. They are useful execution-trace evidence, but they are not a controlled hardware benchmark.
- The exact runner image version, CPU model, memory size, and dependency-install duration are **not available** in the saved logs.

## Recommendation

For future runs, record UTC start/end timestamps and elapsed seconds for each seed and stage, plus the resolved runner image, CPU model, memory size, Python version, and installed package versions. Keep wrapper-level elapsed timing as a cross-check and publish the timing records beside the numeric results.
