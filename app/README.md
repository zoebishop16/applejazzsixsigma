# BikeShare application and function reference

From the repository root run `py app/testme.py` (Windows) or `python3 app/testme.py` (macOS/Linux), then open **http://127.0.0.1:8000**. The launcher creates `.venv` and installs pinned requirements if needed. Stop with Ctrl+C. No Node.js or Context7 needed.

See [project setup/publishing](../README.md), [demo](../demo/README.md) and [data codebook](../data/README.md). There is **no verified public application URL yet**.

## Application scripts

| File | Root command (Windows) | Purpose |
|---|---|---|
| `testme.py` | `py app/testme.py` | Bootstrap environment and serve localhost8000 |
| `manifestme.py` | `.venv\Scripts\python.exe app/manifestme.py` | Copy public synthetic fixtures, normalize LF, fingerprint local app |
| `deployme.py` | `.venv\Scripts\python.exe app/deployme.py --server-name course` | Publish manifest using privately registered server |
| `README.md` | This document | Inputs, API and assumptions |

Install `requirements-deploy.txt` for publishing and `../tests/requirements.txt` for tests. Runtime dependencies are pinned in `requirements.txt`. Connect entrypoint is **dashboard:app**, app mode Shiny, Python3.13. Regenerate manifest locally after changing bundled files; the workflow verifies it without regenerating. Only public synthetic fixtures belong in bundled `data/`, never uploads or credentials.

## Plain numerical API

Import `from app import qc` from the repository root. Methods accept ordinary numbers/pandas frames, never Shiny objects. Except for `prepare_snapshots`, telemetry inputs should already be prepared. Percent fields use0–100; compliance, probability, reliability and explicitly named fraction fields use0–1. UTC timestamps and units follow the codebook.

| Function and parameters | Output and meaning |
|---|---|
| `prepare_snapshots(df,stale_minutes=10)` | Validate required fields, nonnegative integer counts, immutable metadata, UTC ordering, five-minute alignment, duplicate polls and capacity. Sorted frame adds effective_capacity, open_docks, fill_pct, open_pct, age_min, known, status, unusable. Missing polls permitted. |
| `availability_summary(df)` | Dictionary availability_pct, coverage_pct, known_minutes, unknown_minutes, usable_minutes, unusable_minutes. Schedule envelope spans panel first/last poll for stations present; entirely absent stations cannot be inferred. Empty availability undefined. |
| `outage_episodes(df)` | Frame station_id/start/end(exclusive)/duration_min/reason/left_censored/right_censored/completed. Continuous unusability remains one episode through reason changes; unknown/gaps censor boundaries. Reason recorded at onset. |
| `p_chart(counts,totals,baseline_mask=None)` | Integer failures/known counts, positive totals. Baseline default all points. Frame count,n,p,center,lower,upper,signal; clipped three-sigma binomial limits. Empty/zero-variation baseline rejected. |
| `imr_chart(values,baseline_count=None)` | Ordered recovery minutes, baseline default all. Dictionary I limits, MR center/UCL, values, moving_ranges, signal/mr_signal. Requires two varying baseline observations; MR sigma divisor1.128, UCL factor3.267. |
| `hourly_chart(df,baseline_end)` | Known open_pct station/hour mean,n,var,center,pooled_sigma,lower,upper,signal. Baseline hours end by UTC boundary; n>1 groups estimate pooled within-hour SD. Partial groups retain n. Constant/insufficient baselines rejected. Limits analytical/unbounded; select single station in UI. |
| `capability(values,usl)` | Nonnegative completed minutes and SLA minutes. Dictionary n,mean,sd,compliance,ppu,message. Sample SD; empirical <=USL fraction; descriptive one-sided Ppu. Empty/short/constant values give undefined Ppu and explanation. |
| `reliability_summary(df,episodes)` | Dictionary uptime_hours,failures,failure_rate per usable hour,mtbf_hours,mttr_min,availability fraction,message. Left-censored onsets excluded. No finite MTBF if no observed failures. |
| `exponential_reliability(rate,t)` | Probability exp(-rate*t), finite nonnegative rate/hour and time hours. Constant hazard assumed. |
| `system_reliability(probabilities,structure)` | Independent component probabilities [0,1], nonempty. Series product or parallel1-product(1-R); structure series/parallel. |
| `fmea(scores)` | Integer severity/occurrence/detection1–10, optional cause labels; append RPN product, sort descending, cumulative_pct. Empty gives empty frame. |
| `pareto(causes,values=None)` | Cause labels and optional nonnegative weights (default1/count); aggregate sorted frame cause,value,cumulative_pct. Weights may represent downtime minutes; empty yields empty. |
| `forecast(df,current,horizon_min=30)` | Per-station predicted_fill_pct,samples,horizon_min,message. Horizons30/60 (5 for checks). Strictly earlier known operational target-slot rows; same weekday preferred, then weekday/weekend fallback. No history stays undefined. |
| `dispatch_recommendations(current,history,episodes,weights=(.35,.25,.2,.2),target_min=15)` | Dictionary ranked/pairs frames. Priority0–100 weights current severity, elapsed outage/target, historical unusable frequency, inventory-change proxy. Nearest donor/recipient pair from_station,to_station,bikes. No route optimum or measured trips. |
| `heatmap_data(df)` | Known-only frame weekday(Monday0),hour0–23,unusable_fraction; absent cells stay absent. |
| `station_summary(df,episodes,usl=15)` | Per-station availability_pct, observed events, mean_recovery_min, compliance fraction and unknown_minutes plus names/district. Recovery summaries use only completed episodes. |
| `ticket_summary(orders,as_of)` | Dictionary backlog,mean_response_min,mean_repair_min,repeat_offenders frame,orders frame. Exclude future opened tickets; hide future assignments/resolutions and recalculate response. |
| `failure_counts(df,episodes,orders,as_of)` | mode,category,count,downtime_min frame clipped at replay; inventory episodes separated from technical tickets. Categories overlap, so not a unique-failure total. |
| `default_fmea(counts)` | Proposed severity8/detection3; occurrence ceil(10×relative count), bounded1–10, then fmea. Design judgment, not failure probability. |

## Classification, parameters and state

Required snapshot/work-order schemas and units are in [the codebook](../data/README.md). Broken bikes occupy working docks; broken docks reduce effective capacity. Occupancy includes broken bikes, while rentable availability is separate.

Heartbeat older than10minutes is unknown, taking priority over offline. Known offline/zero-capacity is unusable; otherwise zero rentable bikes is empty and zero open docks full. Exact empty/full override bands: below30% low, at least70% high, otherwise medium. Filters choose a fixed station cohort at replay time. Trim API inputs to replay **before** episode extraction to avoid future recovery leakage.

UI recovery target defaults15minutes, availability target95%, forecast horizon30minutes; choices are editable project settings. FMEA1–10 scores and dispatch weights are judgments. Task and van assignments remain session demonstration state and reset on refresh; export a copy to retain them. No real crew dispatch, authentication or live vehicle locations.

## Assumptions and checks

Availability excludes unknown telemetry and reports coverage separately. Duration resolution is5minutes. Censored recovery episodes stay out of completed means while observed downtime stays in exposure. Technical repair tickets need not imply entire-station downtime and can overlap inventory events.

Charts use frozen baseline limits and only the three-sigma point rule. Repeated polls and rush cycles violate independence, so p/hourly charts are exploratory. Pooled I-MR recoveries are descriptive under station heterogeneity. Ppu uses overall SD, assumes normal/stable durations and is not Cpk. Constant-hazard and independent-component reliability are illustrative assumptions. Forecast historical fill cannot guarantee rentable-bike or dock availability.

Run `.venv\Scripts\python.exe -m pytest tests -q` and `.venv\Scripts\python.exe demo/verify.py` from root. [Review evidence](../demo/statistics_review.md) covers known/degenerate checks. The original teaching package and MIT license remain in `starter_reference/`, excluded from deployment and active root test invocation.
