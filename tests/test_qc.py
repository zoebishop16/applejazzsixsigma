import math
import pandas as pd
import pytest
from app import qc


def fixture(bikes=(5, 0, 0, 5), minutes=(0, 5, 10, 15)):
    return pd.DataFrame([dict(timestamp=f"2026-09-07T00:{m:02d}:00Z", station_id="S01",
        station_name="Demo", district="Residential", latitude=42., longitude=-76.,
        total_docks=10, broken_docks=0, bikes=b, broken_bikes=0,
        service_status="operational", last_reported=f"2026-09-07T00:{m:02d}:00Z")
        for b, m in zip(bikes, minutes)])


def test_p_known_and_shift():
    result = qc.p_chart([2, 2, 19], [20]*3, [True, True, False])
    assert result.upper.iloc[0] == pytest.approx(.301246117975)
    assert result.lower.iloc[0] == 0
    assert result.signal.tolist() == [False, False, True]
    with pytest.raises(ValueError): qc.p_chart([], [], [])


def test_imr_known_constant_and_short():
    result = qc.imr_chart([10,12,11,13,14], 5)
    assert result['lower'] == pytest.approx(8.0106382979)
    assert result['upper'] == pytest.approx(15.9893617021)
    assert result['mr_upper'] == pytest.approx(4.9005)
    with pytest.raises(ValueError,match='Zero baseline variation'): qc.imr_chart([2,2,2], 3)
    with pytest.raises(ValueError): qc.imr_chart([2], 1)


def test_capability_known_degenerate():
    result = qc.capability([5,10,15], 10)
    assert result['mean'] == 10 and result['sd'] == 5
    assert result['compliance'] == pytest.approx(2/3)
    assert result['ppu'] == 0
    assert qc.capability([5,5], 10)['ppu'] is None
    assert qc.capability([], 10)['mean'] is None
    with pytest.raises(ValueError): qc.capability([float('nan')], 10)


def test_reliability_formulas_and_limits():
    assert qc.exponential_reliability(.1,5) == pytest.approx(.6065306597)
    assert qc.exponential_reliability(0,5) == 1
    assert qc.system_reliability([.9,.8], 'series') == pytest.approx(.72)
    assert qc.system_reliability([.9,.8], 'parallel') == pytest.approx(.98)
    with pytest.raises(ValueError): qc.system_reliability([], 'series')
    with pytest.raises(ValueError): qc.exponential_reliability(-1,5)


def test_fmea_and_pareto():
    result = qc.fmea(pd.DataFrame([dict(cause='x',severity=8,occurrence=9,detection=3)]))
    assert result.RPN.iloc[0] == 216
    with pytest.raises(ValueError): qc.fmea(pd.DataFrame([dict(severity=0,occurrence=9,detection=3)]))
    assert qc.fmea(pd.DataFrame()).empty
    result = qc.pareto(['a','b','a'])
    assert result['value'].tolist() == [2,1]
    assert result.cumulative_pct.iloc[-1] == 100
    assert qc.pareto([]).empty


def test_prepare_and_validation():
    result = qc.prepare_snapshots(fixture())
    assert result.status.tolist() == ['medium','empty','empty','medium']
    assert result.open_docks.tolist() == [5,10,10,5]
    for change in ({'bikes':11}, {'bikes':float('nan')}, {'service_status':'nonsense'},
                   {'last_reported':'2027-01-01Z'}, {'broken_docks':-1}):
        frame = fixture()
        for key,value in change.items(): frame.loc[0,key] = value
        with pytest.raises(ValueError): qc.prepare_snapshots(frame)
    with pytest.raises(ValueError): qc.prepare_snapshots(pd.concat([fixture(),fixture()]))


def test_episodes_exposure_censor_and_gaps():
    frame = qc.prepare_snapshots(fixture())
    episode = qc.outage_episodes(frame).iloc[0]
    assert episode.duration_min == 10 and episode.completed
    result = qc.reliability_summary(frame, qc.outage_episodes(frame))
    assert result['uptime_hours'] == pytest.approx(10/60)
    assert result['failures'] == 1 and result['mttr_min'] == 10
    assert result['mtbf_hours'] == pytest.approx(10/60)
    boundary = qc.outage_episodes(qc.prepare_snapshots(fixture((0,0,5,0))))
    assert boundary.left_censored.tolist() == [True,False]
    assert boundary.right_censored.tolist() == [False,True]
    assert not boundary.completed.any()
    missing = qc.prepare_snapshots(fixture((5,0,0,5),(0,5,20,25)))
    assert qc.outage_episodes(missing).right_censored.iloc[0]
    assert qc.availability_summary(missing)['unknown_minutes'] == 10
    nofail = qc.prepare_snapshots(fixture((5,5,5,5)))
    assert qc.reliability_summary(nofail,qc.outage_episodes(nofail))['mtbf_hours'] is None


def test_unknown_priority_and_zero_capacity():
    frame = fixture()
    frame.loc[3,'last_reported'] = frame.loc[0,'timestamp']
    frame.loc[3,'service_status'] = 'offline'
    assert qc.prepare_snapshots(frame).status.iloc[-1] == 'unknown'
    frame = fixture()
    frame.loc[0,['bikes','broken_docks']] = [0,10]
    assert qc.prepare_snapshots(frame).status.iloc[0] == 'offline'


def test_hourly_pooled_known():
    frame = pd.DataFrame(dict(timestamp=pd.to_datetime(['2026-01-01T00:00Z','2026-01-01T00:05Z',
        '2026-01-01T01:00Z','2026-01-01T01:05Z']),station_id=['a']*4,open_pct=[0,2,2,4],known=[True]*4))
    result = qc.hourly_chart(frame, pd.Timestamp('2026-01-02',tz='UTC'))
    assert result.center.iloc[0] == 2
    assert result.pooled_sigma.iloc[0] == pytest.approx(math.sqrt(2))
    assert result.lower.iloc[0] == -1 and result.upper.iloc[0] == 5
    with pytest.raises(ValueError): qc.hourly_chart(frame.iloc[:1],pd.Timestamp('2026-01-02',tz='UTC'))
    frame['open_pct']=2
    with pytest.raises(ValueError,match='Zero baseline variation'):
        qc.hourly_chart(frame,pd.Timestamp('2026-01-02',tz='UTC'))


def test_forecast_no_future_leakage():
    frame = qc.prepare_snapshots(fixture())
    now = pd.Timestamp('2026-09-07T00:10Z')
    result = qc.forecast(frame, now, 5)
    assert result.samples.iloc[0] == 0
    assert pd.isna(result.predicted_fill_pct.iloc[0])
    extra = fixture()
    extra['timestamp'] = pd.to_datetime(extra.timestamp) + pd.Timedelta(days=7)
    extra['last_reported'] = extra.timestamp
    history = qc.prepare_snapshots(pd.concat([fixture(),extra],ignore_index=True))
    result = qc.forecast(history,pd.Timestamp('2026-09-14T00:10Z'),5)
    assert result.predicted_fill_pct.iloc[0] == 50
    assert result.samples.iloc[0] == 1


def test_dispatch_empty_and_priority():
    frame = qc.prepare_snapshots(fixture())
    assert qc.dispatch_recommendations(frame.iloc[:0],frame,qc.outage_episodes(frame))['ranked'].empty
    result = qc.dispatch_recommendations(frame.iloc[[1]],frame,qc.outage_episodes(frame))
    assert result['ranked'].action.iloc[0] == 'Deliver bikes'
    with pytest.raises(ValueError): qc.dispatch_recommendations(frame,frame,qc.outage_episodes(frame),weights=(0,0,0,0))


def test_summaries_and_ticket_no_future_leakage():
    frame=qc.prepare_snapshots(fixture())
    episodes=qc.outage_episodes(frame)
    assert qc.heatmap_data(frame).unusable_fraction.iloc[0] == .5
    summary=qc.station_summary(frame,episodes)
    assert summary.availability_pct.iloc[0] == 50
    assert summary.compliance.iloc[0] == 1
    orders=pd.DataFrame([dict(ticket_id='1',station_id='S01',opened_at='2026-09-07T00:00Z',
        assigned_at='2026-09-07T00:10Z',resolved_at='2026-09-07T01:00Z',cause='offline',response_min=10)])
    replay=qc.ticket_summary(orders,'2026-09-07T00:05Z')
    assert replay['backlog']==1 and replay['mean_response_min'] is None
    assert replay['orders'].assigned_at.isna().all() and replay['orders'].resolved_at.isna().all()
    counts=qc.failure_counts(frame,episodes,orders,pd.Timestamp('2026-09-07T00:15Z'))
    assert counts.loc[counts['mode']=='offline','downtime_min'].iloc[0] == 15
    assert qc.default_fmea(counts).RPN.max() <= 1000


def test_episode_reason_switch_not_split():
    x=fixture((5,0,10,5))
    episodes=qc.outage_episodes(qc.prepare_snapshots(x))
    assert len(episodes)==1 and episodes.duration_min.iloc[0]==10
    assert episodes.reason.iloc[0]=='empty'


def test_constant_charts_and_invalid_empty():
    with pytest.raises(ValueError,match='Zero baseline variation'): qc.p_chart([0,0],[20,20])
    with pytest.raises(ValueError,match='Zero baseline variation'): qc.p_chart([20,20],[20,20])
    with pytest.raises(ValueError): qc.prepare_snapshots(pd.DataFrame())
    with pytest.raises(ValueError): qc.p_chart([2],[1])
    with pytest.raises(ValueError): qc.imr_chart([1,float('nan')])
    assert qc.availability_summary(pd.DataFrame())['availability_pct'] is None
