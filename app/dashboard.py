"""BikeShare Operations: Python Shiny interface over the reviewed qc functions.

Run via testme.py. For Connect, use entrypoint dashboard:app from this folder.
No chart estimators or quality-control formulas live in this interface.
"""
from pathlib import Path
from functools import lru_cache
import sys
import html
import json

import pandas as pd
from shiny import App, reactive, render, ui

# Shiny and Connect both support an explicit application directory.
APP_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(APP_DIR))
import qc
import presentation as view

SCENARIOS = {"normal_week": "Normal operations", "high_failure_week": "High failure",
             "improvement_week": "Simulated improvement", "upload": "Upload telemetry"}
PAGES = {"map": "Live Map", "stockouts": "Stockouts & Heatmap", "docks": "Dock Health",
         "forecast": "Forecast & At-Risk", "dispatch": "Dispatch", "maintenance": "Maintenance",
         "analysis": "Data Analysis"}
ORDER_COLS = ["ticket_id", "station_id", "opened_at", "assigned_at", "resolved_at", "cause", "response_min"]


def data_dir():
    bundled = APP_DIR / "data"
    return bundled if bundled.exists() else APP_DIR.parent / "data"


@lru_cache(maxsize=3)
def load_scenario(name):
    folder = data_dir() / name
    snapshots = qc.prepare_snapshots(pd.read_csv(folder / "snapshots.csv.gz"))
    orders = pd.read_csv(folder / "work_orders.csv")
    return snapshots, orders


def esc(value):
    return html.escape(str(value))


def box(label, value, detail=""):
    return f'<div class="kpi"><div class="kpi-label">{esc(label)}</div><div class="kpi-value">{esc(value)}</div><div class="kpi-note">{esc(detail)}</div></div>'


def window_data(frame, window):
    hours = frame.timestamp.dt.hour
    if window == "am": return frame.loc[hours.between(7, 8)]
    if window == "pm": return frame.loc[hours.between(16, 17)]
    if window == "off": return frame.loc[~(hours.between(7, 8) | hours.between(16, 17))]
    return frame


app_ui = ui.page_sidebar(
    ui.sidebar(
        ui.div(ui.span("◉", class_="brand-mark"), ui.div(ui.strong("BikeShare"), ui.div("OPERATIONS", class_="eyebrow")), class_="brand"),
        ui.div("ApPLe JaZz · Urban systems", class_="sidebar-note"),
        ui.div(ui.input_radio_buttons("page", None, PAGES, selected="map"), class_="nav-pages"),
        ui.hr(),
        ui.input_select("scenario", "DEMONSTRATION DATA", SCENARIOS, selected="high_failure_week"),
        ui.panel_conditional("input.scenario === 'upload'",
            ui.input_file("telemetry", "Station snapshots (.csv / .csv.gz)", accept=[".csv", ".gz"]),
            ui.input_file("orders_file", "Optional work orders (.csv)", accept=[".csv"]),
            ui.p("Use the codebook schema. Uploads stay in this session.", class_="small muted")),
        ui.input_select("focus", "STATION DETAIL / ANALYSIS SCOPE", {"all": "All stations"}),
        ui.input_numeric("sla", "Recovery target (minutes)", 15, min=1, max=1440),
        ui.input_numeric("availability_target", "Availability target (%)", 95, min=0, max=100),
        ui.hr(),
        ui.download_button("export_snapshot", "↓ Export filtered snapshot"),
        ui.div("SYNTHETIC DATA\nReplay, not a live city feed.\nAll clocks are UTC.", class_="sidebar-note"),
        width=242, open="desktop", id="navigation", bg="#fafbfc", gap="6px", padding="16px",
    ),
    ui.tags.head(ui.tags.style(view.CSS + '''
      .filterbar{display:flex;flex-wrap:wrap;gap:12px;align-items:end}
      .filterbar>.shiny-input-container{width:170px;flex:1 1 150px}
      .filterbar>.btn{align-self:end;margin-bottom:2px}
      .replaybar{display:grid;grid-template-columns:minmax(0,1fr) 225px;gap:22px;align-items:center}
      .replaybar .shiny-input-container{width:100%;margin:0}
      .freshness{display:flex;align-items:center;gap:12px;font-size:12px;color:#70818a}
      .footer-note{font-size:11px;color:#70818a;padding:16px 0}
      .sidebar-note{white-space:pre-line}.workspace{min-width:0}
      .brand{margin:8px 0 14px}.sidebar-note{padding:8px 3px;margin-top:10px}
      .analysis-tabs{background:white;border-bottom:1px solid #e0e7e9;padding:14px 16px;margin-bottom:14px}
      @media(max-width:700px){.replaybar{grid-template-columns:1fr}.filterbar>.shiny-input-container{width:100%}}
    ''')),
    ui.output_ui("header"),
    ui.div(
        ui.div(ui.input_slider("replay", "REPLAY · FIVE-MINUTE POLLS", min=0, max=6047, value=4995, step=1, ticks=False),
               ui.output_text("replay_label"), class_="replaybar"),
        ui.div(
            ui.input_select("district", "District", {"all": "All districts"}),
            ui.input_select("status", "Status", {"all": "All statuses", **{v: v.title() for v in ["empty", "low", "medium", "high", "full", "offline", "unknown"]}}),
            ui.input_select("freshness", "Last report", {"all": "Any age", "fresh": "≤ 10 min", "stale": "> 10 min"}),
            ui.input_numeric("min_open", "Minimum open docks", 0, min=0, max=10000),
            ui.input_checkbox("problems", "Problem stations only", False),
            class_="filterbar",
        ),
        ui.output_ui("metrics"),
        ui.panel_conditional("input.page === 'forecast'",
            ui.input_radio_buttons("horizon", "Forecast horizon", {"30": "30 minutes", "60": "60 minutes"}, selected="30", inline=True)),
        ui.panel_conditional("input.page === 'analysis'",
            ui.div(ui.input_radio_buttons("analysis_tab", None, {"control": "Control Charts", "capability": "Capability & SLA", "reliability": "Reliability", "fmea": "Failure Analysis / FMEA"}, inline=True), class_="analysis-tabs"),
            ui.panel_conditional("input.analysis_tab === 'control'",
                ui.div(ui.input_select("chart_type", "Chart", {"p": "p-chart · unusable proportion", "imr": "I-MR · completed outage duration", "hourly": "Hourly mean · open docks (%)"}),
                    ui.input_select("window", "Time window (chart only)", {"all": "All hours", "am": "07:00–09:00", "pm": "16:00–18:00", "off": "Off peak"}),
                    ui.input_select("baseline", "Baseline boundary", {"tuesday": "First Tuesday (through Wednesday 00:00)", "week": "First seven days"}), class_="filterbar")),
            ui.panel_conditional("input.analysis_tab === 'fmea'",
                ui.div(ui.input_select("fmea_mode", "Failure mode to edit", {"empty": "Station empty", "full": "Station full", "dock_fault": "Dock fault", "bike_fault": "Bike fault", "offline": "Offline / kiosk failure", "stale": "Silent feed", "slow_van": "Slow van response (manual judgment)"}),
                    ui.input_numeric("severity", "Severity (1–10)", 8, min=1, max=10, step=1),
                    ui.input_numeric("occurrence", "Occurrence (1–10)", 5, min=1, max=10, step=1),
                    ui.input_numeric("detection", "Detection difficulty (1–10)", 3, min=1, max=10, step=1),
                    ui.input_action_button("save_fmea", "Apply scores"), class_="filterbar"))),
        ui.panel_conditional("input.page === 'dispatch' || input.page === 'maintenance'",
            ui.div(ui.input_select("task_station", "Station", {}),
                ui.input_select("task_type", "Task type", {"Rebalancing": "Rebalancing", "Repair": "Repair", "Telemetry": "Check telemetry"}),
                ui.input_select("van", "Assign van", {"Van 01": "Van 01 · 18-bike capacity", "Van 02": "Van 02 · 18-bike capacity"}),
                ui.input_action_button("add_task", "Add to queue"),
                ui.input_select("queue_id", "Queued task", {"none": "No queued tasks"}),
                ui.input_action_button("assign_task", "Assign"),
                ui.input_action_button("complete_task", "Confirm completed"),
                ui.download_button("export_queue", "Export queue"), class_="filterbar"),
            ui.div(ui.input_radio_buttons("queue_tab", "Queue", {"all": "All", "Rebalancing": "Rebalancing", "Repair": "Repair", "Telemetry": "Telemetry"}, inline=True), class_="small"),
            ui.p("Demo actions are stored per session and reset on refresh. Export to keep them. Completion does not change station telemetry.", class_="small muted")),
        ui.panel_conditional("input.page === 'dispatch'",
            ui.div(ui.input_numeric("weight_severity", "Severity weight", 0.35, min=0, max=1, step=.05),
                ui.input_numeric("weight_elapsed", "Elapsed outage weight", .25, min=0, max=1, step=.05),
                ui.input_numeric("weight_frequency", "Failure frequency weight", .20, min=0, max=1, step=.05),
                ui.input_numeric("weight_change", "Inventory change weight", .20, min=0, max=1, step=.05), class_="filterbar")),
        ui.output_ui("body"),
        ui.HTML(view.legend()),
        ui.p("ApPLe JaZz · Cornell Six Sigma Hackathon · Invented station data and coordinates · UTC demonstration clock", class_="footer-note"),
        class_="workspace",
    ),
    title=None, window_title="BikeShare Operations | ApPLe JaZz", fillable=False,
)


def server(input, output, session):
    queue = reactive.value([])
    score_overrides = reactive.value({})

    @reactive.calc
    def source():
        try:
            if input.scenario() != "upload":
                snapshots, orders = load_scenario(input.scenario())
            else:
                files = input.telemetry()
                if not files: return None, None, "Upload a snapshot CSV or choose a demonstration scenario."
                if files[0]["size"] > 50_000_000: raise ValueError("Upload is larger than 50 MB; use compressed CSV.")
                compression = "gzip" if files[0]["name"].endswith(".gz") else None
                raw = pd.read_csv(files[0]["datapath"], compression=compression, nrows=500_001)
                if len(raw) > 500_000: raise ValueError("Maximum 500,000 snapshot rows per upload.")
                snapshots = qc.prepare_snapshots(raw)
                order_file = input.orders_file()
                orders = pd.read_csv(order_file[0]["datapath"]) if order_file else pd.DataFrame(columns=ORDER_COLS)
                qc.ticket_summary(orders, snapshots.timestamp.max())
            return snapshots, orders, None
        except (ValueError, KeyError, OSError, pd.errors.ParserError) as exc:
            return None, None, f"Data could not be loaded: {exc}"

    @reactive.effect
    def update_choices():
        frame, _, error = source()
        if error: return
        dates = frame.timestamp.drop_duplicates().sort_values()
        ui.update_slider("replay", max=max(1, len(dates)-1), value=min(4995, len(dates)-1))
        names = frame.drop_duplicates("station_id").sort_values("station_id")
        choices = {r.station_id: f"{r.station_id} · {r.station_name}" for r in names.itertuples()}
        ui.update_select("focus", choices={"all": "All stations", **choices}, selected="all")
        ui.update_select("task_station", choices=choices)
        ui.update_select("district", choices={"all": "All districts", **{v: v for v in sorted(frame.district.unique())}}, selected="all")
        queue.set([])
        score_overrides.set({})

    @reactive.calc
    def clock():
        frame, _, error = source()
        if error: return None
        dates = frame.timestamp.drop_duplicates().sort_values().reset_index(drop=True)
        return dates.iloc[min(int(input.replay()), len(dates)-1)]

    @reactive.calc
    def current():
        frame, _, error = source()
        if error: return pd.DataFrame()
        now = clock()
        result = frame.loc[frame.timestamp == now]
        if input.district() != "all": result = result.loc[result.district == input.district()]
        if input.status() != "all": result = result.loc[result.status == input.status()]
        if input.freshness() == "fresh": result = result.loc[result.age_min <= 10]
        if input.freshness() == "stale": result = result.loc[result.age_min > 10]
        result = result.loc[result.open_docks >= (input.min_open() or 0)]
        if input.problems(): result = result.loc[result.unusable | ~result.known | (result.broken_docks > 0) | (result.broken_bikes > 0)]
        return result

    @reactive.calc
    def history():
        frame, _, error = source()
        if error: return pd.DataFrame()
        # The replay snapshot defines a fixed station cohort for historical views.
        return frame.loc[(frame.timestamp <= clock()) & frame.station_id.isin(current().station_id)]

    @reactive.calc
    def episodes():
        return qc.outage_episodes(history())

    @reactive.calc
    def scoped():
        frame = history()
        return frame if input.focus() == "all" else frame.loc[frame.station_id == input.focus()]

    @reactive.calc
    def scoped_episodes():
        return qc.outage_episodes(scoped())

    @reactive.effect
    @reactive.event(input.map_station)
    def select_marker():
        ui.update_select("focus", selected=input.map_station())

    @render.text
    def replay_label():
        return clock().strftime("%a %d %b %Y · %H:%M UTC") if clock() is not None else "Waiting for data"

    @render.ui
    def header():
        now = clock()
        label = now.strftime("%d %b · %H:%M UTC") if now is not None else "No data"
        return ui.HTML(f'<header class="topbar"><div><div class="eyebrow">MUNICIPAL NETWORK / SYNTHETIC REPLAY</div><h1>{esc(PAGES[input.page()])}</h1></div><div class="freshness"><span class="badge">DEMO</span><span>Last poll · {esc(label)}</span></div></header>')

    @render.ui
    def metrics():
        if source()[2]: return ui.HTML(view.note(source()[2], "warning"))
        current_frame = current()
        if current_frame.empty: return ui.HTML(view.note("No stations match these filters. Widen the district, status or open-dock filters.", "warning"))
        summary = qc.availability_summary(history())
        return ui.HTML('<div class="kpis">' +
            box("STATIONS IN VIEW", str(len(current_frame)), "At the selected replay poll") +
            box("UNUSABLE NOW", str(int(current_frame.unusable.sum())), "No rentable bikes, no open docks or offline") +
            box("OBSERVED AVAILABILITY", view.fmt(summary['availability_pct'], 1, "%"), "Usable / known station-minutes to replay") +
            box("TELEMETRY COVERAGE", view.fmt(summary['coverage_pct'], 1, "%"), f"{view.fmt(summary['unknown_minutes'], 0)} unknown station-minutes") + '</div>')

    @reactive.effect
    @reactive.event(input.add_task)
    def enqueue():
        if source()[2] or not input.task_station(): return
        tasks = list(queue())
        tasks.append(dict(task_id=f"Q{len(tasks)+1:03d}", station_id=input.task_station(),
            task_type=input.task_type(), status="Open", van="Unassigned", opened_at=clock().isoformat(),
            assigned_at="", completed_at="", resolution_min=None))
        queue.set(tasks)
        ui.notification_show("Task added to this session's demo queue.", type="message")

    @reactive.effect
    def update_queue_choices():
        tasks = queue()
        ui.update_select("queue_id", choices={t['task_id']: f"{t['task_id']} · {t['station_id']} · {t['status']}" for t in tasks} or {"none": "No queued tasks"})

    def edit_task(complete):
        tasks = [dict(t) for t in queue()]
        selected = next((t for t in tasks if t['task_id'] == input.queue_id()), None)
        if selected is None:
            ui.notification_show("Add and select a task first.", type="warning"); return
        if selected['status'] == "Completed":
            ui.notification_show("This task is already completed.", type="warning"); return
        opened = pd.Timestamp(selected['opened_at'])
        if clock() < opened:
            ui.notification_show("Replay time precedes this task. Move the timeline forward.", type="warning"); return
        if complete:
            if selected['status'] != "Assigned":
                ui.notification_show("Assign the task before confirming completion.", type="warning"); return
            if clock() < pd.Timestamp(selected['assigned_at']):
                ui.notification_show("Replay time precedes assignment.", type="warning"); return
            selected['status'] = "Completed"
            selected['completed_at'] = clock().isoformat()
            # This is session workflow elapsed time, not a QC estimate.
            selected['resolution_min'] = (clock()-opened).total_seconds()/60
        else:
            selected.update(status="Assigned", van=input.van(), assigned_at=clock().isoformat())
        queue.set(tasks)

    @reactive.effect
    @reactive.event(input.assign_task)
    def assign(): edit_task(False)

    @reactive.effect
    @reactive.event(input.complete_task)
    def complete(): edit_task(True)

    @reactive.effect
    @reactive.event(input.save_fmea)
    def save_scores():
        try:
            proposed = dict(cause=input.fmea_mode(), severity=input.severity(), occurrence=input.occurrence(), detection=input.detection())
            qc.fmea(pd.DataFrame([proposed]))
            scores = dict(score_overrides()); scores[input.fmea_mode()] = proposed; score_overrides.set(scores)
            ui.notification_show("FMEA scores updated for this session.", type="message")
        except ValueError as exc: ui.notification_show(str(exc), type="warning")

    @render.download(filename="bikeshare-snapshot.csv")
    def export_snapshot():
        yield current().to_csv(index=False)

    @render.download(filename="bikeshare-demo-queue.csv")
    def export_queue():
        yield pd.DataFrame(queue(), columns=["task_id", "station_id", "task_type", "status", "van", "opened_at", "assigned_at", "completed_at", "resolution_min"]).to_csv(index=False)

    def station_detail(frame, hist, eps):
        sid = input.focus()
        if sid == "all":
            return view.card("Station detail", view.note("Select a marker or station in the sidebar to inspect its equipment, history and service targets."))
        match = frame.loc[frame.station_id == sid]
        if match.empty: return view.card("Station detail", view.note("Selected station is outside the current filters."))
        row = match.iloc[0]
        subset = hist.loc[hist.station_id == sid]
        sub_eps = eps.loc[eps.station_id == sid]
        summary = qc.availability_summary(subset)
        cap = qc.capability(sub_eps.loc[sub_eps.completed.astype(bool), 'duration_min'], input.sla())
        detail = f'<h3>{esc(row.station_name)}</h3><span class="badge status-{esc(row.status)}">{esc(row.status.upper())}</span><p>{esc(row.district)} · {esc(sid)}</p>'
        detail += view.html_table(pd.DataFrame({"Measure": ["Occupied effective capacity", "Rentable bikes", "Open docks", "Broken docks", "Broken bikes", "Heartbeat age (min)", "Observed availability (%)", "Mean completed recovery (min)", "Recovery within target (%)"],
            "Value": [view.fmt(row.fill_pct, 1, "%"), row.bikes, row.open_docks, row.broken_docks, row.broken_bikes, row.age_min,
                      view.fmt(summary['availability_pct']), view.fmt(cap['mean']), view.fmt(cap['compliance']*100 if cap['compliance'] is not None else None)]}))
        detail += view.note("Occupancy includes broken bikes, which block returns but cannot be rented. A stale heartbeat means availability is unknown.")
        reliability = qc.reliability_summary(subset, sub_eps)
        detail += f'<p class="small">Usable time per observed failure: {view.fmt(reliability["mtbf_hours"], 2, " h")} · Censored onsets excluded.</p>'
        tickets = source()[1]
        tickets = qc.ticket_summary(tickets.loc[tickets.station_id == sid], clock())['orders']
        detail += '<h4>Recent technical tickets</h4>' + view.html_table(tickets.tail(5))
        return view.card("Station detail", detail)

    def analysis_content(hist, eps, orders):
        if hist.empty: return view.note("The selected station is outside the current filters.", "warning")
        tab = input.analysis_tab()
        now = clock()
        complete_eps = eps.loc[eps.completed.astype(bool)].sort_values('end')
        cap = qc.capability(complete_eps.duration_min, input.sla())
        if tab == "control":
            filtered = window_data(hist, input.window())
            if filtered.empty: return view.note("No observations in this time window.", "warning")
            first = source()[0].timestamp.min().normalize()
            # First Tuesday is a proposed Phase-I baseline, never claimed validated.
            first_tuesday = first + pd.Timedelta(days=(1-first.dayofweek) % 7)
            boundary = first_tuesday + pd.Timedelta(days=1) if input.baseline() == "tuesday" else first + pd.Timedelta(days=7)
            if now < boundary: return view.note("Replay has not reached the selected baseline boundary. Advance the timeline.", "warning")
            warning = view.note("Exploratory limits: repeated station polls, pooled stations and rush-hour cycles violate independence. A signal means investigate; it is not proof of a new cause. Only the three-sigma point rule is applied. First-Tuesday baseline is proposed, not certified in control.", "warning")
            baseline_note = f"Frozen baseline boundary: {boundary.strftime('%d %b %Y %H:%M UTC')} · station scope: {input.focus()}"
            if input.chart_type() == "p":
                points = filtered.groupby('timestamp').agg(count=('unusable', 'sum'), n=('known', 'sum')).reset_index()
                points = points.loc[points.n > 0]
                mask = (points.timestamp >= first_tuesday) & (points.timestamp < boundary) if input.baseline() == 'tuesday' else points.timestamp < boundary
                chart = qc.p_chart(points['count'], points.n, mask)
                return warning + view.card("Unusable station observations", view.line_chart(points.timestamp, chart.p, center=chart.center, lower=chart.lower, upper=chart.upper, signals=chart.signal, ylabel="Unusable proportion", title="p-chart"), baseline_note) + view.note("p = unusable known station observations / all known station observations per poll. Unknown stations are excluded, never counted healthy.")
            if input.chart_type() == "imr":
                # Episode starts determine window selection; durations stay intact.
                durations = window_data(complete_eps.rename(columns={'start': 'timestamp'}), input.window())
                baseline_count = int((durations.end < boundary).sum())
                result = qc.imr_chart(durations.duration_min, baseline_count)
                n = list(range(1, len(result['values'])+1))
                chart = view.line_chart(n, result['values'], center=result['center'], lower=result['lower'], upper=result['upper'], signals=result['signal'], ylabel="Recovery (min)", title="Individuals")
                chart += view.line_chart(n, result['moving_ranges'], center=result['mr_center'], lower=0, upper=result['mr_upper'], signals=result['mr_signal'], ylabel="Moving range (min)", title="Moving range")
                return warning + view.card("Recovery consistency · I-MR", chart, baseline_note) + view.note("Ordered by observed recovery time. Boundary-censored episodes are excluded. Pooling station recoveries is descriptive; negative analytical lower limits are retained.")
            if input.focus() == 'all':
                return warning + view.note("Choose a single station in the sidebar for the hourly means chart. Each station-hour is a subgroup; mixing stations into one connected line would be misleading.")
            chart = qc.hourly_chart(filtered, boundary)
            if input.baseline() == 'tuesday':
                # Restrict baseline calculation to Tuesday; then evaluate all hours.
                baseline_rows = filtered.loc[(filtered.timestamp >= first_tuesday) & (filtered.timestamp < boundary)]
                chart = qc.hourly_chart(pd.concat([baseline_rows, filtered.loc[filtered.timestamp >= boundary]]), boundary)
            return warning + view.card("Hourly open-dock averages", view.line_chart(chart.hour, chart['mean'], center=chart.center, lower=chart.lower, upper=chart.upper, signals=chart.signal, ylabel="Open effective docks (%)", title="Station-hour means"), baseline_note) + view.note("Subgroup = station × clock hour; pooled within-hour sample variance, actual subgroup n. Mixed stations may differ in their means. Use a station scope for a more coherent chart; limits do not model seasonality.")
        if tab == "capability":
            summary = qc.station_summary(hist, eps, input.sla())
            panel = '<div class="kpis">' + box("RECOVERY TARGET", f"≤ {input.sla()} min", "Proposed, editable project setting") + box("WITHIN TARGET", view.fmt(cap['compliance']*100 if cap['compliance'] is not None else None, 1, "%"), "Completed, fully observed recoveries") + box("MEAN RECOVERY", view.fmt(cap['mean'], 1, " min"), f"n = {cap['n']} completed episodes") + box("DESCRIPTIVE Ppu", view.fmt(cap['ppu'], 3), "Overall sample SD; not Cpk") + '</div>'
            panel += view.card("Recovery distribution", view.histogram(complete_eps.duration_min.tolist(), input.sla()))
            panel += view.note("Outage durations are discrete and often skewed. Empirical SLA compliance is primary. Ppu assumes stable, normal durations and is descriptive only; no capability certification or normal-tail defect estimate is made. Censored outages are excluded from recovery averages but included in exposure.", "warning")
            panel += view.card("Station service scorecard", view.html_table(summary), f"Availability target {input.availability_target()}%; recovery duration target ≤ {input.sla()} min. Compliance is a fraction, 0–1.")
            comparisons = []
            for name in list(SCENARIOS)[:3]:
                other, _ = load_scenario(name)
                other = other.loc[other.timestamp <= now]
                if input.focus() != 'all': other = other.loc[other.station_id == input.focus()]
                if input.district() != 'all': other = other.loc[other.district == input.district()]
                comparisons.append({'scenario': SCENARIOS[name], **qc.availability_summary(other)})
            panel += view.card("Simulated scenario comparison", view.html_table(pd.DataFrame(comparisons)[['scenario', 'availability_pct', 'unusable_minutes', 'coverage_pct']]), "Same replay cutoff, district and station scope; current-state filters are intentionally omitted for comparable cohorts. Independent scenarios, not causal before/after evidence.")
            return panel
        if tab == "reliability":
            result = qc.reliability_summary(hist, eps)
            panel = '<div class="kpis">' + box("OBSERVED FAILURE STARTS", str(result['failures']), "Excludes unknown/left-censored onsets") + box("USABLE TIME / FAILURE", view.fmt(result['mtbf_hours'], 2, " h"), "Exposure-based MTBF") + box("MEAN RECOVERY", view.fmt(result['mttr_min'], 1, " min"), "Fully observed recoveries only") + box("EXPOSURE FAILURE RATE", view.fmt(result['failure_rate'], 3, "/h"), "Starts per usable station-hour") + '</div>'
            times = list(range(13))
            if result['failure_rate'] is not None:
                probabilities = [qc.exponential_reliability(result['failure_rate'], t) for t in times]
                panel += view.card("Illustrative usable-period survival", view.reliability_plot(times, probabilities), "R(t) = exp(−λt); no parameter uncertainty shown.")
            panel += view.note(result['message'] + " Inventory and equipment failures have different mechanisms. Reported recurrent events do not establish constant hazard; the exponential curve is an illustration, not a validated prediction.", "warning")
            # Explicit independent block-model examples; never pretend network topology.
            series = qc.system_reliability([.9, .8], 'series')
            parallel = qc.system_reliability([.9, .8], 'parallel')
            panel += view.card("Station as a system · teaching model", '<p>Series: [kiosk works, R=0.90] → [dock access works, R=0.80]</p><p>Parallel: [alternative station A, R=0.90] ∥ [alternative station B, R=0.80]</p>' + f'<p>Independent series reliability: <strong>{series:.2f}</strong> · Independent parallel reliability: <strong>{parallel:.2f}</strong></p>' + view.note("Component probabilities are illustrative inputs, not estimates from these snapshots. A station needs service access AND usable inventory; nearby stations are not automatically interchangeable. Common demand and power failures violate independence."))
            return panel
        counts = qc.failure_counts(hist, eps, orders, now)
        scores = qc.default_fmea(counts)
        for cause, override in score_overrides().items():
            if cause not in scores.cause.values:
                scores = pd.concat([scores, pd.DataFrame([{**override, 'count': 0}])], ignore_index=True)
            else:
                for col in ['severity', 'occurrence', 'detection']: scores.loc[scores.cause == cause, col] = override[col]
        scores = qc.fmea(scores)
        panel = view.note("FMEA scores are judgments, not measured probabilities. Default severity=8 and detection=3; occurrence=ceil(10×mode count/max mode count), minimum 1. Edit scores above. Silent feeds deserve explicit detection review. RPN alone cannot rank all safety risks.", "warning")
        panel += view.card("FMEA risk screening", view.html_table(scores))
        panel += view.card("RPN ranking", view.pareto_chart(scores, value_col='RPN', label_col='cause', title='Judgment-based risk priority'))
        # Keep overlapping technical ticket counts and inventory incidents separate.
        for category in ['inventory', 'technical']:
            group = counts.loc[counts.category == category]
            if not group.empty:
                by_count = qc.pareto(group['mode'].tolist(), group['count'].tolist())
                by_time = qc.pareto(group['mode'].tolist(), group.downtime_min.tolist())
                panel += '<div class="split">' + view.card(category.title() + " incident Pareto", view.pareto_chart(by_count, title='Recorded events')) + view.card(category.title() + " time Pareto", view.pareto_chart(by_time, title='Observed duration (min)')) + '</div>'
        return panel + view.note("Inventory episodes and technical tickets can overlap. Charts are separate and must not be summed into a unique network downtime total. Ongoing durations are bounded by replay time.")

    @render.ui
    def body():
        frame, orders, error = source()
        if error: return ui.HTML(view.card("Choose data to begin", view.note(error, "warning")))
        cur, hist, eps = current(), history(), episodes()
        if cur.empty: return ui.HTML(view.card("No matching stations", view.note("Reset the filters to see the network.")))
        page = input.page()
        try:
            if page == "map":
                content = '<div class="split">' + view.card("Network snapshot", view.station_map(cur, None if input.focus() == 'all' else input.focus()), "Select a station marker · Synthetic coordinates, not a street map") + station_detail(cur, hist, eps) + '</div>'
                priorities = qc.dispatch_recommendations(cur, hist, eps, target_min=input.sla())['ranked']
                content += view.card("Next stations to review", view.html_table(priorities[['station_id', 'station_name', 'status', 'action', 'priority_score', 'elapsed_min']].head(5)), "Transparent heuristic; review on the Dispatch page before creating a demo task.")
            elif page == "stockouts":
                content = view.card("When does the network become unusable?", view.heatmap_chart(qc.heatmap_data(hist)), "Hour × day of week · known-only unusable percentage · shared filters choose a station cohort at replay")
                inventory = eps.loc[eps.reason.isin(['empty', 'full'])].sort_values('start', ascending=False)
                content += view.card("Stockout & fullout log", view.html_table(inventory), "Five-minute resolution. Reason is the state at episode onset; changing reason does not split a continuous outage. Censor flags retain incomplete episodes.")
            elif page == "docks":
                rows = ''.join(view.card(f"{r.station_id} · {r.station_name}", view.dock_grid(r)) for r in cur.itertuples())
                content = view.note("Per-dock squares reconstruct aggregate counts. No physical dock ID or specific failure subtype is measured; positions are illustrative. Occupancy includes broken bikes. Effective capacity = installed docks − broken docks.") + rows
            elif page == "forecast":
                predicted = qc.forecast(hist, clock(), int(input.horizon()))
                predicted = predicted.merge(cur[['station_id', 'station_name', 'status', 'fill_pct']], on='station_id')
                low = predicted.loc[predicted.predicted_fill_pct < 30].sort_values('predicted_fill_pct')
                high = predicted.loc[predicted.predicted_fill_pct >= 70].sort_values('predicted_fill_pct', ascending=False)
                content = view.note("Historical target-slot mean occupancy: prior same weekdays, with weekday/weekend fallback. No future observations are used. Low (<30%) and high (≥70%) are screening thresholds, not failure probabilities. Broken bikes and sudden faults can invalidate inventory predictions; current unknown stations need telemetry checks.", "warning")
                content += '<div class="split">' + view.card("At risk of running low", view.html_table(low), "Ranked from lowest predicted occupancy") + view.card("At risk of filling up", view.html_table(high), "Ranked from highest predicted occupancy") + '</div>'
                content += view.card("All station forecasts", view.html_table(predicted), "samples counts historical observations at the target five-minute slot; a missing prediction means insufficient history.")
            elif page in ['dispatch', 'maintenance']:
                tsummary = qc.ticket_summary(orders, clock())
                task_frame = pd.DataFrame(queue())
                if not task_frame.empty and input.queue_tab() != 'all': task_frame = task_frame.loc[task_frame.task_type == input.queue_tab()]
                if page == 'dispatch':
                    result = qc.dispatch_recommendations(cur, hist, eps, weights=(input.weight_severity(), input.weight_elapsed(), input.weight_frequency(), input.weight_change()), target_min=input.sla())
                    content = view.note("Priority combines current severity, elapsed outage/target, historical unusable fraction and inventory-change proxy using the editable weights above (normalized to sum to 1). Factors clipped to 0–1. Weights are proposed design choices; inventory change is not measured trips. Nearby pairing is a heuristic, not optimized routing.")
                    content += '<div class="three-col">' + view.card("Suggested bike moves", view.html_table(result['pairs']), "Nearest eligible donor/recipient; target half effective capacity. Verify capacity and load before dispatch.") + view.card("Session task queue", view.html_table(task_frame))
                    van_text = ''
                    for van, location in [('Van 01', 'Residential 3'), ('Van 02', 'Downtown 2')]:
                        assigned = [t for t in queue() if t['van'] == van and t['status'] == 'Assigned']
                        van_text += f'<div class="task"><strong>{van}</strong><p>Simulated base: {location}</p><p>Initial load: 6 bikes / capacity: 18</p><p>{len(assigned)} assigned demo tasks</p></div>'
                    content += view.card("Van status · simulated", van_text, "Base positions and initial loads are examples; no GPS or load updates are inferred from completing tasks.") + '</div>'
                    content += view.card("Dispatch reasoning", view.html_table(result['ranked'][['station_id', 'status', 'action', 'priority_score', 'elapsed_min']]))
                else:
                    # Limit tickets to current filter cohort before summary.
                    selected_orders = orders.loc[orders.station_id.isin(cur.station_id)]
                    if input.focus() != 'all': selected_orders = selected_orders.loc[selected_orders.station_id == input.focus()]
                    tsummary = qc.ticket_summary(selected_orders, clock())
                    content = '<div class="kpis">' + box("OBSERVED BACKLOG", str(tsummary['backlog']), "Technical tickets opened but not resolved at replay") + box("MEAN REPAIR TIME", view.fmt(tsummary['mean_repair_min'], 1, " min"), "Opened to resolved; completed technical tickets") + box("MEAN RESPONSE", view.fmt(tsummary['mean_response_min'], 1, " min"), "Opened to assigned; observed assignments only") + '</div>'
                    content += view.card("Technical maintenance tickets", view.html_table(tsummary['orders']), "Future assignments/resolutions are hidden at replay. These measured-ticket metrics differ from inventory-outage recoveries.")
                    content += '<div class="split">' + view.card("Repeat offenders", view.html_table(tsummary['repeat_offenders'])) + view.card("Session task queue", view.html_table(task_frame)) + '</div>'
            else:
                scoped_orders = orders.loc[orders.station_id.isin(scoped().station_id)]
                content = analysis_content(scoped(), scoped_episodes(), scoped_orders)
            return ui.HTML(content)
        except (ValueError, KeyError, TypeError) as exc:
            return ui.HTML(view.card("Analysis needs more information", view.note(str(exc), "warning")))


app = App(app_ui, server)
