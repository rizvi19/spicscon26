| Scenario      | Method                | Mean error (m)   | P90 error (m)   | Failure rate   | Smoothness (m/step)   |
|:--------------|:----------------------|:-----------------|:----------------|:---------------|:----------------------|
| Clean         | WiFi-only             | 1.365 ± 0.171    | 2.635 ± 0.535   | 0.188 ± 0.054  | 1.972 ± 0.314         |
| Clean         | VLP-only              | 0.452 ± 0.011    | 0.756 ± 0.031   | 0.004 ± 0.009  | 0.455 ± 0.027         |
| Clean         | Static fusion         | 0.450 ± 0.012    | 0.754 ± 0.032   | 0.004 ± 0.009  | 0.451 ± 0.021         |
| Clean         | Median-DSP fusion     | 0.674 ± 0.020    | 1.099 ± 0.035   | 0.004 ± 0.009  | 0.367 ± 0.036         |
| Clean         | Graph-smoothed fusion | 0.733 ± 0.121    | 1.319 ± 0.268   | 0.032 ± 0.027  | 0.839 ± 0.108         |
| Clean         | Adaptive fusion       | 0.452 ± 0.011    | 0.756 ± 0.031   | 0.004 ± 0.009  | 0.455 ± 0.027         |
| WiFi degraded | WiFi-only             | 2.232 ± 0.311    | 5.080 ± 1.096   | 0.392 ± 0.065  | 3.120 ± 0.445         |
| WiFi degraded | VLP-only              | 0.451 ± 0.018    | 0.757 ± 0.088   | 0.004 ± 0.005  | 0.462 ± 0.040         |
| WiFi degraded | Static fusion         | 0.467 ± 0.029    | 0.759 ± 0.087   | 0.006 ± 0.005  | 0.496 ± 0.087         |
| WiFi degraded | Median-DSP fusion     | 0.670 ± 0.027    | 1.105 ± 0.036   | 0.002 ± 0.004  | 0.365 ± 0.027         |
| WiFi degraded | Graph-smoothed fusion | 1.108 ± 0.147    | 2.308 ± 0.494   | 0.138 ± 0.060  | 1.398 ± 0.114         |
| WiFi degraded | Adaptive fusion       | 0.451 ± 0.019    | 0.757 ± 0.088   | 0.004 ± 0.005  | 0.462 ± 0.040         |
| VLP blocked   | WiFi-only             | 1.369 ± 0.146    | 2.792 ± 0.470   | 0.192 ± 0.046  | 1.978 ± 0.230         |
| VLP blocked   | VLP-only              | 1.015 ± 0.091    | 2.689 ± 0.315   | 0.170 ± 0.045  | 1.285 ± 0.135         |
| VLP blocked   | Static fusion         | 1.013 ± 0.092    | 2.667 ± 0.305   | 0.168 ± 0.045  | 1.283 ± 0.138         |
| VLP blocked   | Median-DSP fusion     | 0.924 ± 0.051    | 1.799 ± 0.087   | 0.090 ± 0.012  | 0.600 ± 0.019         |
| VLP blocked   | Graph-smoothed fusion | 0.923 ± 0.091    | 1.854 ± 0.200   | 0.084 ± 0.023  | 1.118 ± 0.070         |
| VLP blocked   | Adaptive fusion       | 0.751 ± 0.031    | 1.578 ± 0.201   | 0.074 ± 0.011  | 0.672 ± 0.064         |
| Mixed dynamic | WiFi-only             | 1.918 ± 0.226    | 3.986 ± 0.614   | 0.336 ± 0.094  | 2.714 ± 0.450         |
| Mixed dynamic | VLP-only              | 0.759 ± 0.101    | 1.749 ± 0.704   | 0.100 ± 0.035  | 0.917 ± 0.154         |
| Mixed dynamic | Static fusion         | 0.759 ± 0.101    | 1.749 ± 0.704   | 0.100 ± 0.035  | 0.917 ± 0.154         |
| Mixed dynamic | Median-DSP fusion     | 0.794 ± 0.037    | 1.362 ± 0.201   | 0.044 ± 0.025  | 0.463 ± 0.030         |
| Mixed dynamic | Graph-smoothed fusion | 1.084 ± 0.071    | 2.169 ± 0.365   | 0.116 ± 0.038  | 1.329 ± 0.081         |
| Mixed dynamic | Adaptive fusion       | 0.611 ± 0.078    | 1.198 ± 0.335   | 0.040 ± 0.023  | 0.535 ± 0.067         |