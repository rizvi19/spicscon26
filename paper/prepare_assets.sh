#!/usr/bin/env bash
set -euo pipefail

paper_dir="$(cd "$(dirname "$0")" && pwd)"
repo_root="$(cd "$paper_dir/.." && pwd)"
source_dir="$repo_root/results/figures"
destination_dir="$paper_dir/figures"

mkdir -p "$destination_dir"
cp "$source_dir/fig1_layout_trajectory.png" "$destination_dir/"
cp "$source_dir/fig3_noisy_vs_filtered_signals.png" "$destination_dir/"
cp "$source_dir/fig4_raw_vs_graph_smoothed_heatmap.png" "$destination_dir/"
cp "$source_dir/fig5_scenario_wise_error_paper.png" "$destination_dir/"
cp "$source_dir/fig7_failure_smoothness_paper.png" "$destination_dir/"
cp "$source_dir/fig8_physical_sanity_wifi_light.png" "$destination_dir/" || true

echo "Prepared paper figures in $destination_dir"
