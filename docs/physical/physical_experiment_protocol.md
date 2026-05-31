# Physical Sanity Check Protocol

Project: SPICSCON 2026 — Reliability-Aware WiFi and Visible-Light Fusion  
Purpose: Small physical sanity check only. This is not a full real-world indoor positioning system.

## 1. Goal

This experiment checks two physical assumptions used in the simulation:

1. WiFi RSSI generally changes with distance and body/obstacle blockage.
2. Light intensity generally changes with distance and optical blockage.

These measurements will only motivate the simulated WiFi-degraded and VLP-blocked scenarios. They will not be used as the main quantitative evaluation.

## 2. Devices

Use low-cost available devices:

- One Android phone
- One WiFi router or mobile hotspot
- One LED bulb / flashlight / room light
- Measuring tape or marked floor positions
- Notebook / spreadsheet / CSV editor

## 3. Measurement Area

Use a straight corridor or room where approximate distances can be marked from the signal source.

Preferred distance points:

- 0.5 m
- 1 m
- 2 m
- 3 m
- 4 m
- 5 m

If 5 m is not possible, use the maximum available distance and record it.

## 4. WiFi RSSI Experiment

### Setup

- Place the WiFi router or mobile hotspot at a fixed position.
- Keep the phone connected to the same WiFi network.
- Mark positions away from the router: 0.5 m, 1 m, 2 m, 3 m, 4 m, 5 m.
- Hold the phone at roughly the same height for all measurements.

### Conditions

Collect data under two conditions:

1. normal: line-of-sight / no intentional body blockage
2. blocked: body/hand/object placed between phone and router

### Samples

Collect 20 samples per distance per condition.

If time is very short, collect 10 samples per distance per condition, but 20 is better.

### WiFi CSV Columns

sample_id,timestamp,device,scenario,distance_m,position_id,blockage,rssi_dbm,notes

### Example Row

1,2026-05-31 12:00:00,Redmi Note 10,wifi_physical_sanity,1.0,P2,normal,-48,no blockage

## 5. Light Intensity Experiment

### Setup

- Place a light source at a fixed position.
- Use the phone light sensor or any sensor app that shows light intensity.
- Mark positions away from the light: 0.5 m, 1 m, 2 m, 3 m, 4 m, 5 m.
- Keep phone orientation as consistent as possible.
- Avoid changing room lighting during measurement.

### Conditions

Collect data under two conditions:

1. unblocked: phone sensor has direct/normal exposure to light
2. blocked: hand/body/object partially blocks the light path

### Samples

Collect 20 samples per distance per condition.

### Light CSV Columns

sample_id,timestamp,device,scenario,distance_m,position_id,blockage,light_value,unit,notes

### Example Row

1,2026-05-31 12:10:00,Redmi Note 10,light_physical_sanity,1.0,P2,unblocked,310,lux,no blockage

## 6. Position IDs

Use these position IDs:

| position_id | distance_m |
|---|---:|
| P1 | 0.5 |
| P2 | 1.0 |
| P3 | 2.0 |
| P4 | 3.0 |
| P5 | 4.0 |
| P6 | 5.0 |

## 7. Recording Rules

- Do not move the router/light source during the experiment.
- Keep phone height and orientation as similar as possible.
- Record the exact device model in the device column.
- Record missing/unusual cases in notes.
- Do not mix multiple routers or multiple phones unless clearly noted.
- If a value fluctuates, write each observed sample separately.

## 8. Claim Boundary

Allowed paper wording:

"A small physical sanity check was conducted using a smartphone, WiFi router/hotspot, and LED/light source to confirm that RSSI and light intensity vary under distance and blockage changes. This check supports the motivation for the simulated degradation scenarios but is not used as full real-world localization validation."

Avoid:

- "Real deployment"
- "Hardware-validated indoor positioning system"
- "State-of-the-art physical localization"
- "The proposed system works in real buildings"
- "New WiFi/VLP hardware system"

## 9. Paper Integration

Use this as a short subsection:

"Physical Sanity Check for Simulation Motivation"

It should appear after the simulation setup or before limitations.

Expected outputs:

- results/physical/wifi_rssi_measurements.csv
- results/physical/light_intensity_measurements.csv
- results/tables/table_physical_sanity_summary.csv
- results/figures/fig8_physical_sanity_wifi_light.png
- results/logs/physical_sanity_summary.json

