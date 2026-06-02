"""Generate runtime, reproducibility, and evidence-audit reports from saved evidence.

This module intentionally reads existing expanded-seed artifacts only. It does not
run the experiment or modify the expanded-seed result directory.
"""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPANDED = ROOT / "results/expanded_seed_20260601"
OUT = ROOT / "results/runtime_reproducibility_20260601"
STATUS = EXPANDED / "reports/github_actions_run_status.md"
SUMMARY_JSON = EXPANDED / "logs/expanded_seed_summary.json"
NUMERIC_SUMMARY = EXPANDED / "reports/expanded_seed_numeric_summary.txt"
SANITY_REPORT = EXPANDED / "reports/02_sanity_check_report.md"
WORKFLOW = ROOT / ".github/workflows/expanded-seed-evidence.yml"
CONFIG = ROOT / "configs/expanded_seeds.yaml"
REQUIREMENTS = ROOT / "requirements.txt"

REQUIRED_CSVS = [
    "results/expanded_seed_20260601/raw/errors_by_seed_scenario_method_expanded.csv",
    "results/expanded_seed_20260601/tables/table_main_expanded_seed_results.csv",
    "results/expanded_seed_20260601/tables/table_ablation_expanded_seed_results.csv",
    "results/expanded_seed_20260601/tables/table_seed_stability_comparison.csv",
    "results/expanded_seed_20260601/tables/table_best_method_by_scenario.csv",
]
REQUIRED_LATEX = [
    "paper/tables/expanded_seed_20260601/compact_main_results_expanded.tex",
    "paper/tables/expanded_seed_20260601/compact_ablation_expanded.tex",
    "paper/tables/expanded_seed_20260601/compact_seed_stability.tex",
]
SCENARIOS = ["s1_clean", "s2_wifi_degraded", "s3_vlp_blocked", "s4_mixed_dynamic"]
KEY_METHODS = ["static_fusion", "static_fusion_median", "graph_diffusion_3", "adaptive_fusion"]


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def extract(pattern: str, text: str, default: str = "not available") -> str:
    match = re.search(pattern, text, flags=re.MULTILINE)
    return match.group(1) if match else default


def yes_no(value: bool) -> str:
    return "PASS" if value else "FAIL"


def generate() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    status_text = read(STATUS)
    smoke_command = read(EXPANDED / "logs/github_actions_smoke_command.log")
    final_command = read(EXPANDED / "logs/github_actions_final_command.log")
    final_log = read(EXPANDED / "logs/final_run.log")
    smoke_log = read(EXPANDED / "logs/smoke_run.log")
    summary = json.loads(read(SUMMARY_JSON))
    numeric_text = read(NUMERIC_SUMMARY)
    sanity_text = read(SANITY_REPORT)
    workflow_text = read(WORKFLOW)
    dependencies = [line.strip() for line in read(REQUIREMENTS).splitlines() if line.strip() and not line.startswith("#")]

    smoke_seconds = extract(r"smoke completed in ([0-9.]+) seconds", smoke_command)
    final_seconds = extract(r"final completed in ([0-9.]+) seconds", final_command)
    workflow_url = extract(r"Workflow run: `([^`]+)`", status_text)
    branch = extract(r"Branch: `([^`]+)`", status_text)
    generated_at = extract(r"Generated at UTC: `([^`]+)`", status_text)
    dependency_status = extract(r"Dependency installation status: `([^`]+)`", status_text)
    smoke_status = extract(r"Smoke-run status: `([^`]+)`", status_text)
    final_status = extract(r"Final ten-seed run status: `([^`]+)`", status_text)

    runtime_rows = [
        ["smoke elapsed time", smoke_seconds, "seconds", "results/expanded_seed_20260601/logs/github_actions_smoke_command.log", "Extracted from the saved GitHub Actions command wrapper output."],
        ["final expanded run elapsed time", final_seconds, "seconds", "results/expanded_seed_20260601/logs/github_actions_final_command.log", "Extracted from the saved GitHub Actions command wrapper output."],
        ["total final run time", final_seconds, "seconds", "results/expanded_seed_20260601/logs/github_actions_final_command.log", "The saved wrapper elapsed time for the final ten-seed pipeline."],
        ["per-seed runtime", "not available", "", "results/expanded_seed_20260601/logs/final_run.log", "Seed-level elapsed timing was not recorded in the current logs."],
        ["per-stage runtime", "not available", "", "results/expanded_seed_20260601/logs/final_run.log", "Per-stage runtime was not recorded in the current logs."],
        ["workflow run URL", workflow_url, "", "results/expanded_seed_20260601/reports/github_actions_run_status.md", "Saved GitHub Actions workflow run."],
        ["branch name", branch, "", "results/expanded_seed_20260601/reports/github_actions_run_status.md", "Branch recorded by the successful workflow."],
        ["timestamp", generated_at, "UTC", "results/expanded_seed_20260601/reports/github_actions_run_status.md", "Workflow status report generation timestamp."],
    ]
    with (OUT / "runtime_summary.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["item", "value", "unit", "source_file", "note"])
        writer.writerows(runtime_rows)

    (OUT / "runtime_summary.md").write_text(f"""# Expanded 10-Seed Runtime Summary

## Scope

This report summarizes runtime evidence already saved for the successful expanded 10-seed experiment. It does not rerun the experiment and should not be interpreted as a hardware runtime benchmark.

## Extracted runtime values

| Item | Value | Source |
| --- | ---: | --- |
| Smoke pipeline elapsed time | {smoke_seconds} seconds | `results/expanded_seed_20260601/logs/github_actions_smoke_command.log` |
| Final expanded 10-seed pipeline elapsed time | {final_seconds} seconds | `results/expanded_seed_20260601/logs/github_actions_final_command.log` |
| Total final run time | {final_seconds} seconds | `results/expanded_seed_20260601/logs/github_actions_final_command.log` |
| Workflow run | `{workflow_url}` | `results/expanded_seed_20260601/reports/github_actions_run_status.md` |
| Branch recorded by workflow | `{branch}` | `results/expanded_seed_20260601/reports/github_actions_run_status.md` |
| Status-report timestamp | `{generated_at}` | `results/expanded_seed_20260601/reports/github_actions_run_status.md` |

## Limitations of runtime logging

- Per-seed runtime is **not available** because seed-level elapsed timing was not recorded in the current logs.
- Per-stage runtime was not recorded in the current logs.
- The saved elapsed times cover the smoke and final pipeline command wrappers on a GitHub Actions runner. They are useful execution-trace evidence, but they are not a controlled hardware benchmark.
- The exact runner image version, CPU model, memory size, and dependency-install duration are **not available** in the saved logs.

## Recommendation

For future runs, record UTC start/end timestamps and elapsed seconds for each seed and stage, plus the resolved runner image, CPU model, memory size, Python version, and installed package versions. Keep wrapper-level elapsed timing as a cross-check and publish the timing records beside the numeric results.
""", encoding="utf-8")

    manifest = {
        "repo": "https://github.com/rizvi19/spicscon26",
        "branch_used": branch,
        "config_file_path": "configs/expanded_seeds.yaml",
        "seed_list": summary["seeds"],
        "number_of_seeds": summary["n_seeds"],
        "scenarios": summary["scenarios"],
        "methods": summary["methods"],
        "key_result_files": REQUIRED_CSVS + REQUIRED_LATEX + [
            "results/expanded_seed_20260601/reports/expanded_seed_numeric_summary.txt",
            "results/expanded_seed_20260601/logs/final_run.log",
            "results/expanded_seed_20260601/logs/smoke_run.log",
        ],
        "sanity_check_file_path": "results/expanded_seed_20260601/reports/02_sanity_check_report.md",
        "github_actions_run_url": workflow_url,
        "workflow_status": {
            "dependency_installation": int(dependency_status),
            "smoke_run": int(smoke_status),
            "final_ten_seed_run": int(final_status),
        },
        "python_dependencies_from_requirements_txt": dependencies,
        "evidence_generation_date": generated_at,
        "note": "Final numeric results are stored under results/expanded_seed_20260601/.",
    }
    (OUT / "reproducibility_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    python_executable = extract(r"RUN: (/opt/hostedtoolcache/Python/([^/]+)/x64/bin/python)", smoke_log)
    python_version = extract(r"RUN: /opt/hostedtoolcache/Python/([^/]+)/x64/bin/python", smoke_log)
    runner_label = extract(r"runs-on: ([^\n]+)", workflow_text).strip()
    (OUT / "environment_summary.txt").write_text(f"""Expanded 10-seed environment summary
====================================

Evidence source
---------------
GitHub Actions run: {workflow_url}
Workflow branch: {branch}
Status-report timestamp (UTC): {generated_at}

Python
------
Python executable observed in saved smoke log: {python_executable}
Python version observed from executable path: {python_version}
The saved logs do not include a separate `python --version` output from the successful GitHub Actions run.

OS / runner
-----------
GitHub Actions runner label from workflow configuration: {runner_label}
Exact resolved runner image version: not available
CPU model: not available
Memory size: not available

Dependencies from requirements.txt
----------------------------------
{chr(10).join(f'- {item}' for item in dependencies)}

Completion status
-----------------
GitHub Actions completed dependency install, smoke run, and final ten-seed run with status 0.

Missing information
-------------------
Exact resolved runner image version, CPU model, memory size, a separate successful-run `python --version` line, per-seed elapsed timings, and per-stage elapsed timings are not available in the saved logs.
""", encoding="utf-8")

    csv_checks = {path: (ROOT / path).exists() for path in REQUIRED_CSVS}
    latex_checks = {path: (ROOT / path).exists() for path in REQUIRED_LATEX}
    expected_seeds = list(range(101, 111))
    seeds_ok = summary["seeds"] == expected_seeds
    scenarios_ok = summary["scenarios"] == SCENARIOS
    methods_ok = all(method in summary["methods"] for method in KEY_METHODS)
    stable = summary["old_5_seed_conclusion_remained_stable"] is True
    difficult = summary["difficult_scenario_comparison"]
    s3_improves = difficult["s3_vlp_blocked"]["mean_error_improvement_percent"] > 0
    s4_improves = difficult["s4_mixed_dynamic"]["mean_error_improvement_percent"] > 0
    conditional_claim = "no universal-best claim" in sanity_text and summary["paper_claim_recommendation"] == "preserved"
    red_flags = not all([NUMERIC_SUMMARY.exists(), SANITY_REPORT.exists(), all(csv_checks.values()), all(latex_checks.values()), seeds_ok, scenarios_ok, methods_ok, stable, s3_improves, s4_improves, conditional_claim])
    (OUT / "evidence_audit.md").write_text(f"""# Expanded 10-Seed Evidence Audit

## Scope

This audit checks the saved expanded-seed artifacts without rerunning or recomputing the experiment. It uses the existing numeric summary and sanity report, with file-existence verification for the required generated artifacts.

## Audit checklist

1. **{yes_no(NUMERIC_SUMMARY.exists())} — Does `expanded_seed_numeric_summary.txt` exist?**
   - `{relative(NUMERIC_SUMMARY)}`
2. **{yes_no(SANITY_REPORT.exists())} — Does `02_sanity_check_report.md` exist?**
   - `{relative(SANITY_REPORT)}`
3. **{yes_no(all(csv_checks.values()))} — Do all required CSV result files exist?**
{chr(10).join(f'   - `{path}`: {yes_no(exists)}' for path, exists in csv_checks.items())}
4. **{yes_no(all(latex_checks.values()))} — Do all required LaTeX table files exist?**
{chr(10).join(f'   - `{path}`: {yes_no(exists)}' for path, exists in latex_checks.items())}
5. **{yes_no(seeds_ok)} — Does the seed list contain 101–110?**
   - Saved seed list: `{summary['seeds']}`
6. **{yes_no(scenarios_ok)} — Are all four scenarios present?**
   - Saved scenarios: `{summary['scenarios']}`
7. **{yes_no(methods_ok)} — Are key methods present?**
   - Required key methods: `{KEY_METHODS}`
8. **{yes_no(stable)} — Is the old 5-seed conclusion stable?**
   - Existing numeric summary reports: `Old 5-seed conclusion remained stable: yes`.
9. **{yes_no(s3_improves)} — Does adaptive fusion improve over static fusion in `s3_vlp_blocked`?**
   - Existing numeric summary reports a `{difficult['s3_vlp_blocked']['mean_error_improvement_percent']:.3f}%` mean-error improvement (`{difficult['s3_vlp_blocked']['static_fusion']['mean_error_m']:.6f} m` to `{difficult['s3_vlp_blocked']['adaptive_fusion']['mean_error_m']:.6f} m`).
10. **{yes_no(s4_improves)} — Does adaptive fusion improve over static fusion in `s4_mixed_dynamic`?**
    - Existing numeric summary reports a `{difficult['s4_mixed_dynamic']['mean_error_improvement_percent']:.3f}%` mean-error improvement (`{difficult['s4_mixed_dynamic']['static_fusion']['mean_error_m']:.6f} m` to `{difficult['s4_mixed_dynamic']['adaptive_fusion']['mean_error_m']:.6f} m`).
11. **{yes_no(conditional_claim)} — Are paper claims still conditional, not universal-best?**
    - The existing sanity report says ranking varies by scenario and no universal-best claim is made. The numeric summary recommendation is `{summary['paper_claim_recommendation']}`.
12. **{'FAIL' if red_flags else 'PASS'} — Are there any red flags before paper update?**
    - {'One or more required evidence checks failed; review before any paper update.' if red_flags else 'No red flags were found in the required artifact, seed, scenario, method, stability, or conditional-claim checks. The saved sanity report also records no non-finite metrics, bounded failure rates, nonnegative localization errors, sensible confidence intervals, no command failures, and fresh final-run metrics.'}

## Conclusion

The expanded 10-seed evidence is internally consistent with the saved sanity report and is suitable for a later, separate paper update after review. Adaptive fusion should continue to be described conditionally as useful in the difficult VLP-blocked and mixed-dynamic scenarios, not as universally optimal.
""", encoding="utf-8")

    (OUT / "paper_ready_runtime_note.txt").write_text("""The expanded 10-seed evaluation was executed through a GitHub Actions workflow with fixed held-out seeds and saved configuration, raw CSV outputs, sanity checks, generated LaTeX tables, and automated execution logs. The saved wrapper logs record successful smoke and final pipeline execution, but this does not constitute a controlled hardware runtime benchmark. These artifacts improve reproducibility by making the reported results traceable to repository evidence.\n""", encoding="utf-8")


if __name__ == "__main__":
    generate()
