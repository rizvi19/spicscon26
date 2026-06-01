# Expanded-Seed Smoke Test Report

- Command run: `python -m src.expanded_seed_experiments --config configs/expanded_seeds.yaml --mode smoke`
- Status: **PASS**
- Smoke seeds: `[101, 102]`
- Elapsed seconds: `25.561`
- Generated files: isolated full-pipeline stage artifacts under `.expanded_seed_work/smoke/results/`, including adaptive metric tables for seeds 101 and 102.
- Required adaptive metric files present: `True`
- Warnings/errors: none.
- Final run safe to proceed: **yes**. The isolated workspace prevents overwriting preserved five-seed evidence.
