# Stress/sensitivity GitHub Actions run required

Local numerical execution could not proceed because this container has no scientific Python dependencies and both `pip` and `apt` downloads are blocked by HTTP 403 responses from the package tunnel. No numerical outputs or placeholder `stress_sensitivity_ALL_RESULTS.txt` file were created locally.

Please run the `stress-sensitivity-evidence` workflow from GitHub Actions. It checks out `codex/research-evidence-upgrades`, installs `requirements.txt`, runs smoke mode first, runs final mode only after smoke passes, uploads the isolated evidence artifact, and commits generated stress/sensitivity outputs back to `codex/research-evidence-upgrades`.
