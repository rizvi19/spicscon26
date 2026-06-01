# Expanded-Seed Smoke Test Report

## Command run

```bash
python -m src.expanded_seed_experiments --config configs/expanded_seeds.yaml --mode smoke
```

## Status

**FAIL — stop before final evaluation.**

The smoke command was attempted initially and rerun once after checking the environment, following the requested failure workflow. Both attempts failed before any experiment stage executed because the Codex cloud Python environment does not contain the repository's declared scientific dependencies. The first missing import is `matplotlib`.

## Dependency remediation attempt

The repository declares NumPy, SciPy, pandas, Matplotlib, scikit-learn, NetworkX, PyYAML, and related packages in `environment.yml`. No Conda or Micromamba executable is available in this cloud container, and none of the installed pyenv Python versions contains NumPy. A direct package installation attempt was made:

```bash
python -m pip install --retries 0 numpy scipy pandas matplotlib scikit-learn networkx pyyaml tqdm joblib tabulate
```

That command failed because access to the package index is blocked by the cloud network proxy with `Tunnel connection failed: 403 Forbidden`.

## Generated files

- `results/expanded_seed_20260601/logs/smoke_run.log` — exact traceback from the allowed smoke rerun.
- `results/expanded_seed_20260601/logs/dependency_install_attempt.log` — exact blocked package-install output.
- `results/expanded_seed_20260601/reports/00_repo_inspection.md` — pre-run repository inspection.
- `results/expanded_seed_20260601/reports/01_smoke_test_report.md` — this report.
- `results/expanded_seed_20260601/reports/02_sanity_check_report.md` — explicit not-run sanity status.
- `results/expanded_seed_20260601/reports/03_optional_20seed_decision.md` — explicit optional-run decision.
- `results/expanded_seed_20260601/reports/expanded_seed_failure_report.md` — full failure and recovery report.

No numeric experiment output was generated. No old five-seed artifact was overwritten. No result was fabricated.

## Warnings/errors

- Missing Python dependency: `matplotlib`.
- Package installation blocked by proxy: `403 Forbidden`.
- The final 10-seed evaluation was intentionally not started.

## Is the final run safe to proceed?

**No.** The cloud environment must first provide the dependencies declared in `environment.yml`. Per the instructions, execution stops here after the smoke rerun failure.
