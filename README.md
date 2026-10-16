# BikeShare Operations

A Python website for a municipal bikeshare dispatcher deciding where to send redistribution and maintenance vans during empty/full-dock rush-hour disruptions. Built by **ApPLe JaZz**, Cornell Six Sigma Hackathon, 24-hour on-campus track.

Seven pages connect availability, dock health, historical forecasts, dispatch tasks, maintenance tickets and tested quality-control analysis. Three reproducible **synthetic** scenarios run without an account, API key or downloaded dataset. This demonstration does not dispatch real crews.

Repository: [zoebishop16/applejazzsixsigma](https://github.com/zoebishop16/applejazzsixsigma). **Public application URL: not deployed yet.** Course Posit Connect credentials and live verification remain outstanding.

## Run in VS Code

Install Python **3.13** (tested: 3.13.1) and VS Code. Choose **File → Open Folder** and open this repository. Open **Terminal → New Terminal** at the repository root beside `SPEC.md`.

Windows:

```powershell
py app/testme.py
```

macOS/Linux:

```bash
python3 app/testme.py
```

The launcher creates `.venv` and installs pinned runtime packages if needed. First run needs internet and may take several minutes. Open **http://127.0.0.1:8000** after the terminal prints the address. Keep the terminal running; stop with **Ctrl+C**. No Node.js or Context7 is required.

In VS Code choose **Ctrl+Shift+P → Python: Select Interpreter → .venv/Scripts/python.exe** (macOS/Linux: `.venv/bin/python`). Edit `app/dashboard.py` for behavior, `app/presentation.py` for appearance, and `app/qc.py` for analysis; restart the server after saving.

If `py` is missing, install Python or use your Python executable. If a Windows Store launcher reports “Access is denied,” use a regular Python installation or an existing environment: `.venv\Scripts\python.exe app/testme.py`.

## Demonstrate the tool

Start with **High failure**, default replay September 24, 2026, 08:15 UTC. Select a map marker for details. Shared filters select district, status, freshness, minimum open docks and problem stations; station scope selects one/all stations. Filters define a fixed station cohort at replay time.

| Page | Decision support |
|---|---|
| Live Map | Synthetic station locations, rentable bikes, open docks, freshness |
| Stockouts & Heatmap | Recurring empty/full periods and outage episodes |
| Dock Health | Broken docks/bikes versus inventory imbalance |
| Forecast & At-Risk | Historical 30/60-minute target-slot estimates and insufficient-history states |
| Dispatch | Explained priorities, donor/recipient suggestions, session tasks and export |
| Maintenance | Replay-visible tickets, response times and repeat problem stations |
| Data Analysis | p, I-MR and hourly charts; empirical SLA/Ppu; reliability; Pareto/FMEA |

Follow [the complete demo](demo/README.md) for exact scenario outputs and every page. Match full-window totals by replaying to **6047** with all stations and unrestricted filters. Select one station for hourly mean charts. Recovery target defaults to **15 minutes**, availability target **95%**; these are editable project settings, not city standards. FMEA scores and dispatch weights are editable judgments.

Task/van assignments are session demonstration state and reset on refresh; export to retain them. No production authentication, real van tracking, traffic routing or telemetry integration is included.

## Inputs and reproducible data

Select a bundled scenario or upload `.csv`/`.csv.gz` snapshots, optionally work orders `.csv`. Uploads stay in the session and are not bundled for publishing. Required snapshot columns:

```text
timestamp,station_id,station_name,district,latitude,longitude,total_docks,
broken_docks,bikes,broken_bikes,service_status,last_reported
```

Use UTC timestamps aligned to five-minute polls, nonnegative integer counts and consistent station metadata. `bikes` means **rentable** bikes; broken bikes occupy working docks. Derived open docks = total docks minus broken docks minus rentable/broken bikes. Validation rejects duplicate polls, missing fields, unsupported states and impossible capacity. Stale telemetry and missing polls remain unknown.

The [codebook](data/README.md) documents every field, unit, file and real collection source. Three folders (`normal_week`, `high_failure_week`, `improvement_week`) each contain 20 stations, four districts, 10–20 docks and **21 days**, 120,960 five-minute rows plus work orders. Names, coordinates, faults and improvements are invented. Independent scenarios do not prove causal intervention effects.

Regenerate from the root: `py scripts/generate_data.py` (macOS/Linux: `python3 scripts/generate_data.py`). The generator uses only Python's standard library and prints deterministic fingerprints.

## Test

After first launch installs the environment, use a second terminal:

```powershell
.venv\Scripts\python.exe -m pip install -r tests/requirements.txt
.venv\Scripts\python.exe -m pytest tests -q
.venv\Scripts\python.exe demo/verify.py
```

On macOS/Linux substitute `.venv/bin/python`. The core suite passed **14 tests** covering known answers, degenerate inputs, censoring, missingness, invalid data and future-data exclusion. The demo script reproduces all scenario results. See [review evidence](demo/statistics_review.md).

For browser checks with the server running and Microsoft Edge installed:

```powershell
.venv\Scripts\python.exe app/browser_check.py --channel msedge
```

Otherwise install Playwright Chromium (`.venv/bin/python -m playwright install chromium`) and omit `--channel msedge`. Browser checks exercised seven pages, three chart types, filters, queue edits, exports, scenarios, mobile layout, invalid upload and a known-answer upload showing 50.0% availability. A teammate fresh-clone walkthrough and logged-out deployed verification remain pending.

## Publish to course Posit Connect

The app uses explicit entrypoint **dashboard:app**, with a locally generated committed manifest. Use the course **Posit Connect server**, with a compatible Python interpreter. Never put keys or server addresses in source files, commits, screenshots or chat.

1. Install publishing tools and regenerate the manifest after any bundled app/data/dependency change:

   ```powershell
   .venv\Scripts\python.exe -m pip install -r app/requirements-deploy.txt
   .venv\Scripts\python.exe app/manifestme.py
   ```

   This copies only public synthetic fixtures to `app/data`, normalizes LF text and fingerprints the app. Do not generate the manifest in CI. `.gitattributes` preserves file hashes across platforms.

2. In your GitHub repo choose **Settings → Secrets and variables → Actions**. Add `CONNECT_SERVER` and `CONNECT_API_KEY` using course-provided values. The prepared `.github/workflows/deploy-shiny-py.yml` uses `APP_DIR: app`.
3. Review changes together, then stage explicit paths, commit and push:

   ```powershell
   git add README.md SPEC.md CONTRACT.yaml .gitattributes .gitignore app/ data/ tests/ demo/ scripts/generate_data.py docs/plan.md .github/workflows/deploy-shiny-py.yml .github/scripts/connect-publish-async.sh
   git commit -m "Build BikeShare Operations dashboard"
   git push origin main
   ```

   These are publication instructions; no commit or push was performed automatically. Applicable pushes to main trigger deployment, or choose **Actions → Deploy Shiny (Python) app to Posit Connect → Run workflow**.
4. Wait for green Actions, then configure content public access in Connect (“Anyone” where permitted). Open its URL logged out; verify HTTP 200, every page and a known test dataset. Add the verified URL here and submit it with the repository link on Devpost.

For a local first deployment, register a named server `course` using the `rsconnect` CLI in your private terminal (`rsconnect add --help` describes server/key options). Keep credentials local and out of tracked files. Then run:

```powershell
.venv\Scripts\python.exe app/deployme.py --server-name course
```

If the server lacks Python3.13, create an environment using a supported version, check package compatibility, retest, update `app/.python-version` and regenerate the manifest from that environment. Editing its fingerprint alone does not change the interpreter. Diagnose deployment failures from the first failing Connect task-log message.

## Methods, assumptions and sources

Every numerical analysis lives in [app/qc.py](app/qc.py); [the API reference](app/README.md) documents functions and units. Availability excludes unknown telemetry and reports coverage separately. Poll durations have five-minute resolution. Incomplete/censored episodes are excluded from completed recovery means; observed downtime remains exposure. Technical tickets can overlap inventory outages.

Charts freeze baseline limits and use only the three-sigma point rule. Repeated stations and daily cycles violate independence, making p/hourly charts exploratory. Ppu uses overall sample SD with stability/normality caveats and is **not Cpk**. Exponential reliability assumes constant hazard; series/parallel illustrations assume independence. No observed failures does not establish finite MTBF. Forecasts use only earlier available history and report insufficient samples.

Adapted from [timothyfraser/sixsigmahackathon](https://github.com/timothyfraser/sixsigmahackathon); the Python package starter and MIT license are retained in `app/starter_reference`. Publishing templates credit [fastapi-connect-demo](https://github.com/timothyfraser/fastapi-connect-demo). References: [Shiny for Python](https://shiny.posit.co/py/), NIST [p charts](https://www.itl.nist.gov/div898/handbook/pmc/section3/pmc332.htm), [individuals charts](https://www.itl.nist.gov/div898/handbook/pmc/section3/pmc322.htm), [capability](https://www.itl.nist.gov/div898/handbook/pmc/section1/pmc16.htm).

Project files: `app/` implementation and launch/publish scripts; `tests/` active checks; `data/` fixtures/codebook; `demo/` exact walkthrough; `scripts/generate_data.py` generator; `SPEC.md`, `CONTRACT.yaml`, `docs/plan.md` scope and task evidence.
