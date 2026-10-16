# SPEC: Six Sigma Hackathon team project

What your tool IS. Your agent reads this before every task. Where the code and this file
disagree, the code is the bug: change this file first, then the code.

Most of this page is already decided by the event and the [rubric](docs/criteria.md).
**Only the `FILL IN` lines change, and you do not have to write them by hand:** describe your app and ask your agent to update them. They depend on the prompt your team picks at kickoff
(prompts are secret until then, see [`docs/prompts.md`](docs/prompts.md)) and on your team.
The examples after each `FILL IN` show the shape of an answer. They are not hints about the prompts.

## 1. Team and prompt
- **Team name:** ApPLe JaZz
- **Track:** On-campus (24 hours).
- **Prompt we chose:** Urban Systems - Bikeshare Fleets (prompt text supplied by the team).
- **Our public repo:** https://github.com/zoebishop16/applejazzsixsigma (fork of timothyfraser/sixsigmahackathon).

## 2. User and use case (rubric: scope 5, user and use case 5)
- **User:** Municipal bikeshare dispatcher; analyst tools support the same operational decisions.
- **Decision the tool helps them make, and when:** Each rush hour, decide which stations need bike redistribution or equipment repair, and prioritize van tasks.
- **Why this matches the prompt:** Tracks empty/full stations and equipment failures, identifies recurring service loss, and recommends measured dispatch actions.

## 3. Inputs (rubric: minimal inputs 5)
Only what this user can actually measure or already knows. Fewer is better; every input a user
cannot measure costs points.

| Input | Type and units | Where the user gets it |
|---|---|---|
| Five-minute station snapshots | timestamp, station ID, district, coordinates (degrees), total/broken docks (counts), rentable/broken bikes (counts), service state and last reported timestamp | Station telemetry; synthetic examples included |

## 4. The statistics, and why (rubric: valid QC analysis 25)
Say the method in words before any code exists. Load the `stats-first-steering` skill first.
- **Method:** Plain tested functions for availability and outage episodes; baseline p-chart of unusable station observations; I-MR chart of completed recovery times; hourly open-dock averages with pooled within-hour standard deviation; empirical SLA compliance and descriptive one-sided Ppu; exposure-based failure rate, MTBF and MTTR; exponential and independent series/parallel reliability illustrations; Pareto and editable FMEA (RPN = S x O x D).
- **Why it fits the use case:** Separates recurring inventory imbalance, unusual process changes, service-target violations, and equipment failures to explain dispatch priorities.
- **Assumptions and how the tool checks them:** Validate counts, capacity, timestamps and duplicates. Five-minute polls estimate duration to five-minute resolution; stale/unknown data are reported separately. Exclude boundary-censored episodes from completed-recovery averages and retain them in exposure. Freeze limits from a selected baseline; display only the three-sigma point rule. Repeated stations and rush-hour demand violate independence, so p-chart and hourly limits are exploratory, with fixed-window filters. Report empirical SLA compliance as primary; Ppu is descriptive with normality/stability caveats, never mislabeled Cpk. Exponential constant hazard and component independence are illustrative assumptions, not validated network models. Forecasts use historical day/time averages with explicit insufficient-history handling; FMEA scores and dispatch weights are editable judgments.
- **Known-answer check:** For p = 2/20 = 0.1 and n = 20, UCL = 0.1 + 3 sqrt(0.1 x 0.9 / 20) = 0.301246117975 and LCL = 0. Completed recoveries [5,10,15] minutes have mean 10, sample SD 5, compliance at USL 10 of 2/3 and Ppu = 0. RPN for S=8,O=9,D=3 is 216. R(5) with lambda=0.1/hour is exp(-0.5) = 0.6065306597. Independent components [0.9,0.8] give series reliability 0.72 and parallel reliability 0.98. Tests also cover empty inputs, zero variation, missing values, boundary-censored episodes and planted shifts.

Fixed for every team:
- The statistic lives in **one plain, tested function** (`app/qc.py` or `app/qc.R`). The API, app or
  package only calls it and displays the result. No statistics inside UI code.
- Every statistic has a test against a known answer and a degenerate case (constant data, n = 1, missing values).
- You can explain every number the tool prints. If you cannot, it is not done.

## 5. Delivery (rubric: working tool 25)
- **Stack:** Python Shiny dashboard, with pandas and matplotlib for analysis and charts; Python application code editable in VS Code.
- **Starting demo:** demos/pypackage/ for the Python core, adapted into a Python Shiny application with testme.py, manifestme.py, deployme.py and README.md. The supplied shinyapp demo is R rather than Python.

Fixed for every team:
- Start from **one** demo in `demos/`, copied to `app/`. Keep its four-script contract
  (`testme`, `manifestme`, `deployme`, `README.md`); `testme` starts the tool with one command.
- Deployed on the course **Posit Connect** server with a public URL (publisher key handed out at the
  event). Deploy early: copy one workflow from
  [`.claude/skills/connect-publish/workflows/`](.claude/skills/connect-publish/workflows/).
- A small tool that runs beats a large tool that does not.

## 6. Outputs
- **What the user sees:** Seven light-theme pages: Live Map, Stockouts & Heatmap, Dock Health, Forecast & At-Risk, Dispatch, Maintenance, Data Analysis (SPC, capability, reliability, FMEA). Shared filters, replay time and freshness; station detail, legends using shape and text, editable targets, simulated task state, and explanatory assumptions. Synthetic data is labeled everywhere; no real van locations or authentication is implied.
  Example: "a control chart with out-of-control points in red, plus 'stop the line: yes/no'"

## 7. Test datasets and codebook (rubric: demo 10, datasets 5, codebook 5)
2-3 small CSVs in `data/`, invented but shaped like real field data, each showing one behavior.
`data/README.md` is the codebook: every file, every column with units, and what it would take to
collect this data for real.
- **Datasets:** Three reproducible 21-day scenarios: normal_week, high_failure_week, improvement_week; 20 stations in four districts with 10-20 docks, five-minute observations all day, weekday 07-09 and 16-18 rush hours, weekend daylight peaks. Scenario folders include snapshots and work orders; data/README.md documents all fields and synthetic generation. scripts/generate_data.py regenerates deterministic examples.

## 8. Documentation and reproducibility (rubric: docs 10, public repo 5)
- `README.md` says what the tool does, for whom, every input and parameter, how to run it in one
  command, and walks through the demo on each test dataset.
- Public GitHub repo; a fresh clone runs `testme` and the tests pass with no extra steps.
- Submit on Devpost: the repo link plus a demo.

## 9. Out of scope
What we will NOT build, so nobody (human or agent) builds it by accident.
- Default: logins, databases, real customer data, a second statistic before the first one is tested.
- No real telemetry integration, production authentication, route optimization, or claims that simulated improvements prove field performance. Dispatch and tickets are demonstration state; clearly disclose persistence behavior.
