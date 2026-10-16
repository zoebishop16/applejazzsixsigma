# Demonstrate BikeShare Operations

This walkthrough uses **invented data**, not a live municipal feed. All times are
UTC and all service targets are editable demonstration settings, not city standards.
Use the repository-root installation and launch instructions in [the README](../README.md).
Then open the address printed by `python app/testme.py` (normally port 8000).

## Reproduce all three cases

From the repository root, with the environment installed:

```powershell
.venv\Scripts\python.exe demo/verify.py
```

The command uses the same `app/qc.py` functions as the website. It reads each
scenario's `snapshots.csv.gz` and `work_orders.csv`, checks replay-safe ticket
visibility at the last poll, prints exact JSON results, and asserts the expected
availability ordering. It exits unsuccessfully if those assertions fail.

To see matching full-window results in the website, choose a scenario from the
sidebar, move **Replay** to **6047** (September 27, 2026, 23:55 UTC), choose all
stations/districts/statuses, Any age, minimum open docks 0, and turn off Problem
stations only. Keep recovery target at 15 minutes. Filters and earlier replay
times intentionally change the analysis population and censor unfinished episodes.

| Scenario and input files | Known-data availability | Known coverage | Unusable station-minutes | Episodes / completed | Mean completed recovery (min) | Completed within 15 min | Technical tickets | MTBF usable hours |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `data/normal_week/snapshots.csv.gz`, `work_orders.csv` | 99.806527% | 99.989253% | 1,170 | 203 / 203 | 5.763547 | 98.522167% | 44 | 49.553777 |
| `data/high_failure_week/snapshots.csv.gz`, `work_orders.csv` | 97.367697% | 99.182374% | 15,790 | 1,285 / 1,284 | 12.289720 | 88.006231% | 132 | 7.581321 |
| `data/improvement_week/snapshots.csv.gz`, `work_orders.csv` | 99.989253% | 100.000000% | 65 | 7 / 7 | 9.285714 | 85.714286% | 22 | 1,439.845238 |

**Read normal operations:** availability is high, but short empty/full incidents
still occur; rare stale polls remain unknown rather than counted as healthy.

**Read high failure:** more service loss and technical tickets justify prioritizing
maintenance and rush-hour redistribution. One incomplete/censored episode stays
out of completed-recovery statistics while its observed downtime remains exposure.

**Read simulated improvement:** downtime falls sharply, but the seven remaining
recoveries have lower within-15-minute compliance than normal. Improvement in one
metric does not guarantee improvement in every metric; small episode samples matter.
These independently simulated scenarios do not establish intervention causality.

## Seven-page dispatcher walkthrough

1. **Live Map:** start with High failure at default replay index 4995 (September
   24, 08:15 UTC). Marker shape and text supplement color. Click a station or choose
   station detail to inspect rentable/broken bikes, open/broken docks and freshness.
   The map is an explicitly synthetic coordinate schematic, not street geography.
2. **Stockouts & Heatmap:** compare residential morning emptiness with downtown
   accumulation; inspect the day/hour panel and outage table. Gray heatmap cells
   lack known observations. Duration estimates have five-minute resolution.
3. **Dock Health:** inspect effective capacity and broken assets. A broken bike
   occupies a working dock; a broken dock reduces effective capacity. The dock
   illustration displays aggregate counts, not measured individual positions.
4. **Forecast & At-Risk:** choose 30/60 minutes. Forecasts use earlier target-slot
   history, preferring matching weekday and otherwise weekday/weekend history.
   No history yields an explicit insufficient-data state. Historical fill is an
   occupancy estimate, not a measured trip forecast or guaranteed rentable supply.
5. **Dispatch:** inspect transparent priority factors and illustrative pickup/dropoff
   pairing. Add a task, assign a demonstration van, change status, then export.
   The nearest-station pairing is a heuristic, not traffic-aware route optimization.
6. **Maintenance:** inspect replay-visible technical tickets, assignment response
   time, resolution time and repeat stations. Future ticket details remain hidden.
   Task edits are session demonstration state and reset on refresh; exports retain
   a copy. No real crew dispatch occurs.
7. **Data Analysis:** try p-chart, I-MR and hourly mean charts; choose the frozen
   baseline and fixed time window. Select a single station (for example S01) for
   the hourly mean chart. Filters define a fixed station cohort at replay time;
   they do not repeatedly change the cohort at every historical poll. Then inspect capability/SLA, reliability and
   editable FMEA. Empirical SLA compliance is primary; Ppu is descriptive and is
   never Cpk. Reliability curves assume constant hazard; series/parallel illustrations
   assume independent components. FMEA scores are editable judgments.

For a useful empty-state check, choose an impossible combination such as a high
minimum-open-dock count. The tool should show that no observations match. Reset
filters before comparing against the table. Upload invalid telemetry to see a
validation message; the dataset schema is in [the codebook](../data/README.md).

## Statistical interpretation

Availability excludes unknown telemetry from its denominator and reports coverage
separately. Scheduled gaps count as unknown exposure. Continuous unusability is
one episode even when empty/full/offline reason changes; the reason is recorded
at onset. Boundary/unknown-gap censoring prevents incomplete recoveries from being
treated as completed durations. Technical tickets can overlap inventory outages;
do not sum those counts as unique failures.

Control limits use a baseline rather than the entire shifted series and apply
only the three-sigma point rule. Repeated station polls and rush-hour cycles violate
independence; the charts are exploratory, not validated production alarm rules.
Zero-variation baselines produce an explanatory message instead of control limits.
MTBF uses usable station-hours per observed onset; it is not calendar cycle time.
See [statistics review evidence](statistics_review.md) for known-answer checks.

## Reproducibility fingerprints

`demo/verify.py` prints SHA-256 of the compressed snapshots:

```text
normal_week      23e6a78c47f63cd1948ad0bb8f745e8c7d354251f0e30c327c658f98528f15e5
high_failure_week df2d2e73cc1466995d95f75beee385775424e5b37326cfb7ede1427590031fad
improvement_week b4eb7cb7149dc562cd15084d14920048b8a1e03dac71f042a9e85845cbc650c1
PASS: all three synthetic scenarios reproduce; failure < normal < simulated improvement availability.
```

The generator rerun reproduced those bytes. Human teammate walkthrough and public
deployment verification remain separate checks; this document does not claim they
have happened merely because the automated demonstration script passes.
