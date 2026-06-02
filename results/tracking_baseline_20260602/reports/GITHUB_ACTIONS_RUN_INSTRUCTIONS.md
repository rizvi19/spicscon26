# Run the tracking baseline evidence workflow

Please run the `tracking-baseline-evidence` workflow from GitHub Actions on branch `codex/tracking-baseline-evidence`.

The workflow installs `requirements.txt`, runs smoke first, runs the final held-out ten-seed experiment only after smoke passes, uploads the evidence artifact, and commits complete generated outputs back to the branch.
