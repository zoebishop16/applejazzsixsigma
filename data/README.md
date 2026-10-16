# Synthetic bikeshare demonstration data

All records, station names, coordinates, faults, tickets and improvements are invented.
These are repeatable test cases, not observed municipal performance or evidence of
an intervention's effectiveness. Each folder covers **21 days**, despite retaining
the requested `week` folder names: September 7–27, 2026, at five-minute intervals.
All timestamps use UTC. Rush-hour patterns are defined in that same demonstration
clock; no local daylight-saving conversion is implied.

| Folder | Intended demonstration | Seed |
|---|---|---|
| `normal_week/` | Weekday residential morning depletion/downtown accumulation, reversed at evening rush; occasional technical faults | 401 |
| `high_failure_week/` | Stronger inventory imbalance and more, longer technical faults; S07 is a planted problem station | 402 |
| `improvement_week/` | Simulated reduced imbalance and shorter/fewer faults, using the same station geometry | 403 |

Each folder contains `snapshots.csv.gz` (120,960 rows; pandas reads gzip directly)
and `work_orders.csv`. The three scenarios are separate synthetic processes;
they are not matched experimental before/after observations. Weekend activity
peaks around daylight hours, with accumulation at Riverside. Docks range from
10 to 20 across 20 stations in Residential, Downtown, University and Riverside.
Weekday peaks center on 08:00 and 17:00 (approximately 07–09 and 16–18).

## Snapshot codebook

| Variable | Units / allowed values | Meaning and real collection source |
|---|---|---|
| `timestamp` | ISO 8601 UTC timestamp, `Z` suffix | Scheduled poll time; record when polling station telemetry |
| `station_id` | Text, S01–S20 | Stable station identifier from the asset register |
| `station_name` | Text | Public station name from the asset register |
| `district` | Text, four districts above | Operational district from the dispatcher station list |
| `latitude` | Decimal degrees north | Synthetic schematic coordinate; real value from station GPS/register |
| `longitude` | Decimal degrees east (negative west) | Synthetic schematic coordinate; real value from station GPS/register |
| `total_docks` | Count, 10–20 | Installed dock count, including broken docks; asset register |
| `broken_docks` | Count, 0 to total_docks | Dock positions unavailable for any bike; maintenance/telemetry |
| `bikes` | Count, nonnegative | Rentable bikes physically docked; station telemetry |
| `broken_bikes` | Count, nonnegative | Unrentable bikes occupying otherwise working docks; maintenance/telemetry |
| `service_status` | `operational` or `offline` | Station controller communication/service state |
| `last_reported` | ISO 8601 UTC timestamp | Last station heartbeat; compare with poll time to flag stale data |

Effective capacity = `total_docks - broken_docks`. Open docks = effective
capacity minus `bikes + broken_bikes`; it is derived, never independently sampled.
All rows satisfy nonnegative counts and `bikes + broken_bikes <= effective capacity`.
An operational row may still be stale: always inspect heartbeat age. Offline
and stale counts are synthetic retained readings; they must not be interpreted
as verified current inventory. Offline does not imply an empty station.

## Work-order codebook

| Variable | Units / allowed values | Meaning and real collection source |
|---|---|---|
| `ticket_id` | Text, unique within scenario | Maintenance system ticket identifier |
| `station_id` | Text, matches snapshots | Asset linked to the ticket |
| `opened_at` | ISO 8601 UTC timestamp | First five-minute poll of a synthetic technical failure |
| `assigned_at` | ISO 8601 UTC timestamp | Dispatch assignment timestamp, at or after opening |
| `resolved_at` | ISO 8601 UTC timestamp, blank if unresolved | First healthy poll after technical episode; blank means right-censored at dataset end |
| `cause` | `dock_fault`, `bike_fault`, `offline`, `stale` | Invented technical root-cause label; real value confirmed by technician |
| `response_min` | Minutes, nonnegative | Assignment delay = assigned_at minus opened_at; this is **not** recovery duration |

Tickets are generated directly from nonoverlapping technical fault episodes at
each station. Inventory empty/full conditions are demand imbalance and do not
automatically create maintenance tickets. Fault durations are measured only to
five-minute resolution. A broken dock/bike episode can reduce capacity without
making the whole station unusable; do not equate every ticket to station downtime.
The current generator places all technical episodes within the observation window;
the schema supports unresolved tickets but does not guarantee one in these files.

## Reproduce and validate

From the repository root run `py scripts/generate_data.py` (or
`python scripts/generate_data.py` on macOS/Linux). No external package is needed.
The command regenerates all six files and checks counts, capacity bounds, cadence,
heartbeat ordering and ticket ordering. It prints each compressed snapshot SHA-256.
Seeds and gzip metadata are fixed, so repeated runs on the same Python version
produce identical bytes. Python versions can differ in random implementation;
record the interpreter version when comparing externally generated files.

The generator uses only measurable inventory, station heartbeat and maintenance
timestamps. Demand is a simulation mechanism, not a measured ridership input or
a claim of observed trip counts. Real deployments should collect snapshot polls
and maintenance logs, retain gaps instead of inventing readings, and validate
clock synchronization, identifiers and maintenance diagnosis before analysis.
