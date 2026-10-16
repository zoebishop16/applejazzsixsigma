# BikeShare Operations plan

Approved: ApPLe JaZz, 24-hour on-campus; Python Shiny; dispatcher focus;
seven pages; three synthetic scenarios; editable targets. Context7 skipped.

## Methods (plain functions before interface)
- Availability = usable observed minutes / observed minutes; unknown exposure reported separately.
- Outages are contiguous unusable polls; duration = polls x 5 minutes; preserve boundary censoring.
- p-chart: pbar = baseline failures / baseline n; limits = pbar +/- 3 sqrt(pbar(1-pbar)/n), clipped to [0,1].
- I-MR: MR = absolute consecutive difference; sigma = mean(MR)/1.128; I limits = mean +/- 3 sigma; MR limits = [0,3.267 mean(MR)].
- Hourly averages: pooled within variance = sum((n-1)s²)/sum(n-1); limits = grand mean +/- 3 pooled_sigma/sqrt(n).
- Capability: empirical proportion(duration <= USL); Ppu = (USL-mean)/(3 sample SD), descriptive only.
- Failure rate = observed failure starts / usable hours; MTBF = reciprocal rate; MTTR = mean completed duration.
- Reliability illustration: R(t)=exp(-rate*t); series=product(R); parallel=1-product(1-R). Independence assumed.
- FMEA: RPN = severity x occurrence x detection; Pareto sorts descending and accumulates percentage.
- Forecast: past same day-type/time-slot mean fill, no future observations; compare 30/60-minute horizon.
- Dispatch: explicit heuristic using current severity, elapsed outage, historical frequency, observed demand proxy.

## Tasks and verification
1. H-01 SPEC.md: placeholder count 0; known p-chart UCL 0.301246117975; empty input rejects (10 min).
2. H-02 data/ and approved scripts/generate_data.py: 20 stations, 21 days, 5-minute cadence; codebook; seeded rerun checksum; bounds and rush-hour checks (20 min).
3. H-03 app/qc.py, app/requirements.txt, tests/: all known answers in SPEC; constant, censored, missing and planted-shift checks; independent stats review (30 min).
4. H-04 app/: adapt demos/pypackage into Shiny; seven pages; real callbacks; testme starts and HTTP 200; browser navigation/filter/task tests; invalid upload displays error (45 min).
5. H-05 demo/: run each scenario; exact computed outputs; no matching rows gives helpful state (10 min).
6. H-06 deployment paths: copy course workflow/scripts; generated manifest; local bundle imports; live verification awaits course credentials (15 min).
7. H-07 README.md, app/README.md: clean installation/run/test/publish instructions; document every function and units; no secret values (15 min).
8. H-08 .gitignore: exclude local environment; public push and Devpost remain human actions (5 min).

## Decisions and review state
- Synthetic scenarios span three weeks each; folder names retain the requested week naming.
- Default targets are proposed project settings, not municipal standards.
- Login roles are demonstration views; session task edits reset on refresh and can be exported.
- Work is prepared and tested sequentially; verified tasks await human review/commit.
- No commit or push without explicit approval; deployment instructions are authorized, credentials absent.

## Risks
- Autocorrelation and rush-hour cycles: label limits exploratory, allow fixed windows, never equate stability with SLA success.
- Boundary episodes and stale telemetry: retain censor flags and report unknown coverage separately.
- Python restrictions and no Node: use approved Python environment; report any unavailable browser verification.
