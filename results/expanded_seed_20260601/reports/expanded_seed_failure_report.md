# Expanded-Seed Evaluation Failure Report

## Executive summary

The expanded-seed runner and configuration were prepared, but the requested cloud execution could not proceed because the container has no scientific Python dependencies installed and cannot download them through its configured network proxy. The smoke test was attempted twice at most: once initially and once after a simple remediation attempt. The final 10-seed run was not executed, and no numeric values were fabricated.

## Requested command

```bash
python -m src.expanded_seed_experiments --config configs/expanded_seeds.yaml --mode smoke
```

## Exact failure

The smoke runner fails during Python import before invoking any experiment stage:

```text
ModuleNotFoundError: No module named 'matplotlib'
```

This is an environment limitation, not a generated research result.

## Environment checks performed

- The shell resolves `python` to `/root/.pyenv/shims/python` (`Python 3.12.13`).
- `conda` and `micromamba` are unavailable.
- NumPy is absent from every discovered pyenv interpreter (Python 3.10, 3.11, 3.12, 3.13, and 3.14).
- The active interpreter is also missing pandas, PyYAML, SciPy, Matplotlib, and tabulate.
- `environment.yml` correctly declares the scientific dependencies required by the repository.

## Remediation attempt

```bash
python -m pip install --retries 0 numpy scipy pandas matplotlib scikit-learn networkx pyyaml tqdm joblib tabulate
```

The remediation failed because the cloud proxy rejected package-index access:

```text
Tunnel connection failed: 403 Forbidden
```

See `results/expanded_seed_20260601/logs/dependency_install_attempt.log` for the exact output.

## Preservation and scientific-honesty status

- Existing five-seed evidence under the legacy `results/` directories was not overwritten or deleted.
- `paper/main.tex` was not edited.
- Existing paper result numbers were not changed.
- No synthetic, copied, or stale metrics were presented as expanded-seed results.
- The isolated runner is designed to use `.expanded_seed_work/<mode>/results/` as fresh pipeline storage and to publish only explicit expanded outputs.
- The legacy five-seed long table is read only for a future explicit stability comparison after a successful final run.

## What remains blocked

Because the smoke rerun failed, the following were intentionally not generated:

- 10-seed raw metric CSV
- expanded aggregate CSV tables
- compact LaTeX result tables
- numeric TXT/MD/JSON summaries
- result figure
- completed numeric sanity checks
- optional 20-seed evaluation

## Recovery path

Run the prepared workflow in a cloud container that already has the dependencies from `environment.yml`, or one that can access a package index. The first commands should be:

```bash
python -m src.expanded_seed_experiments --config configs/expanded_seeds.yaml --mode smoke
python -m src.expanded_seed_experiments --config configs/expanded_seeds.yaml --mode final
```

The user is not asked to run these commands locally; this report records the cloud-environment blocker for a follow-up cloud execution.

## Push status

A local commit was created on `codex/research-evidence-upgrades`. The requested push was attempted with:

```bash
git push -u origin codex/research-evidence-upgrades
```

The push could not complete because this cloud checkout has no configured `origin` remote. The exact Git error is saved in `results/expanded_seed_20260601/logs/push_attempt.log`.
