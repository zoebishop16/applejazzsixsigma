"""Plain BikeShare analysis functions. All time exposure uses five-minute polls.

Control limits are exploratory under temporal/station dependence. Ppu uses overall
sample SD, not within-process Cpk. Reliability models are illustrative constant
hazard/independence models. No web framework or plotting belongs in this module.
"""
import math
import numpy as np
import pandas as pd

POLL_MIN = 5
EPISODE_COLUMNS = ['station_id','start','end','duration_min','reason',
                   'left_censored','right_censored','completed']


def _numbers(values, empty=False):
    values = np.asarray(list(values), dtype=float)
    if (not empty and not len(values)) or not np.isfinite(values).all():
        raise ValueError('Provide finite numeric observations.')
    return values


def prepare_snapshots(df, stale_minutes=10):
    """Validate telemetry and derive occupancy (percent), known state and usability.

    Unknown heartbeat takes precedence over offline. A working station is unusable
    when no rentable bikes OR no open docks remain. Exact empty/full override bands.
    """
    required = ['timestamp','station_id','station_name','district','latitude','longitude',
                'total_docks','broken_docks','bikes','broken_bikes','service_status','last_reported']
    if not set(required) <= set(df.columns) or df.empty:
        raise ValueError('Upload nonempty telemetry with every documented column.')
    if not math.isfinite(stale_minutes) or stale_minutes < 0:
        raise ValueError('Freshness threshold must be nonnegative minutes.')
    result = df[required].copy()
    if result.isna().any().any():
        raise ValueError('Snapshot fields cannot be missing.')
    for col in ['timestamp','last_reported']:
        try: result[col] = pd.to_datetime(result[col],utc=True,format='mixed',errors='raise')
        except (ValueError,TypeError) as exc: raise ValueError(f'Invalid {col} timestamp.') from exc
    if ((result.timestamp.dt.minute%5!=0)|(result.timestamp.dt.second!=0)|(result.timestamp.dt.microsecond!=0)).any():
        raise ValueError('Poll timestamps must align to the five-minute schedule.')
    for col in ['total_docks','broken_docks','bikes','broken_bikes','latitude','longitude']:
        try: result[col] = pd.to_numeric(result[col],errors='raise')
        except (ValueError,TypeError) as exc: raise ValueError(f'{col} must be numeric.') from exc
        if not np.isfinite(result[col]).all(): raise ValueError(f'{col} must be finite.')
    for col in ['total_docks','broken_docks','bikes','broken_bikes']:
        if ((result[col] < 0) | (result[col] % 1 != 0)).any():
            raise ValueError('Asset counts must be nonnegative integers.')
    if (result.total_docks <= 0).any() or (result.broken_docks > result.total_docks).any():
        raise ValueError('Installed capacity must be positive; broken docks cannot exceed it.')
    if (~result.latitude.between(-90,90)).any() or (~result.longitude.between(-180,180)).any():
        raise ValueError('Coordinates out of range.')
    if not result.service_status.isin(['operational','offline']).all():
        raise ValueError('Service status must be operational or offline.')
    if result.duplicated(['station_id','timestamp']).any(): raise ValueError('Duplicate station timestamp.')
    for col in ['station_name','district','latitude','longitude','total_docks']:
        if (result.groupby('station_id')[col].nunique() > 1).any():
            raise ValueError(f'Station metadata {col} changes within this upload.')
    result['effective_capacity'] = result.total_docks - result.broken_docks
    result['open_docks'] = result.effective_capacity - result.bikes - result.broken_bikes
    if (result.open_docks < 0).any(): raise ValueError('Bike counts exceed working dock capacity.')
    result['age_min'] = (result.timestamp-result.last_reported).dt.total_seconds()/60
    if (result.age_min < 0).any(): raise ValueError('Last reported cannot be in the future.')
    result['known'] = result.age_min <= stale_minutes
    result['fill_pct'] = ((result.bikes+result.broken_bikes)/result.effective_capacity.replace(0,np.nan)*100)
    result['open_pct'] = result.open_docks/result.effective_capacity.replace(0,np.nan)*100
    result['status'] = np.select([~result.known,
        (result.service_status=='offline') | (result.effective_capacity==0),result.bikes==0,
        result.open_docks==0,result.fill_pct<30,result.fill_pct>=70],
        ['unknown','offline','empty','full','low','high'],default='medium')
    result['unusable'] = result.known & result.status.isin(['offline','empty','full'])
    return result.sort_values(['station_id','timestamp']).reset_index(drop=True)


def availability_summary(df):
    """Known usable exposure / known exposure; scheduled gaps count as unknown.

    Schedule envelope spans the first to last poll in the entire selected panel
    for every station present. Uploads cannot establish stations absent entirely.
    """
    if df.empty:
        return dict(availability_pct=None,known_minutes=0,unknown_minutes=0,
                    unusable_minutes=0,usable_minutes=0,coverage_pct=None)
    expected = ((df.timestamp.max()-df.timestamp.min()).total_seconds()/60+POLL_MIN)*df.station_id.nunique()
    known = int(df.known.sum())*POLL_MIN
    bad = int(df.unusable.sum())*POLL_MIN
    return dict(availability_pct=100*(known-bad)/known if known else None,
                known_minutes=known,unknown_minutes=max(0,expected-known),
                unusable_minutes=bad,usable_minutes=known-bad,
                coverage_pct=100*known/expected if expected else None)


def outage_episodes(df):
    """Continuous unusable polls, irrespective of reason switches.

    Unknown polls/gaps terminate episodes with right censoring. Observed recovery
    completes an episode only when its onset was observed from a healthy poll.
    """
    records=[]
    for sid, group in df.groupby('station_id',sort=False):
        active=None
        previous=None
        prior_healthy=False
        for row in group.sort_values('timestamp').itertuples():
            adjacent = previous is not None and row.timestamp-previous==pd.Timedelta(minutes=POLL_MIN)
            if active is not None and (not adjacent or not row.known or not row.unusable):
                recovered = adjacent and row.known and not row.unusable
                active['right_censored'] = not recovered
                active['completed'] = recovered and not active['left_censored']
                records.append(active)
                active=None
            if row.known and row.unusable:
                if active is None:
                    active=dict(station_id=sid,start=row.timestamp,end=row.timestamp+pd.Timedelta(minutes=POLL_MIN),
                        duration_min=POLL_MIN,reason=row.status,left_censored=not(adjacent and prior_healthy),
                        right_censored=True,completed=False)
                else:
                    active['end']=row.timestamp+pd.Timedelta(minutes=POLL_MIN)
                    active['duration_min']+=POLL_MIN
            previous=row.timestamp
            prior_healthy=bool(row.known and not row.unusable)
        if active is not None: records.append(active)
    return pd.DataFrame(records,columns=EPISODE_COLUMNS)


def p_chart(counts, totals, baseline_mask=None):
    """Three-sigma point rule; freeze pooled baseline proportion; varying n."""
    k,n=_numbers(counts),_numbers(totals)
    if len(k)!=len(n) or (n<=0).any() or (k<0).any() or (k>n).any() or (k%1).any() or (n%1).any():
        raise ValueError('Counts and positive totals must be matching integer observations.')
    mask=np.ones(len(k),dtype=bool) if baseline_mask is None else np.asarray(baseline_mask,dtype=bool)
    if len(mask)!=len(k) or not mask.any(): raise ValueError('Select at least one baseline point.')
    center=k[mask].sum()/n[mask].sum()
    if center in (0,1):
        raise ValueError('Zero baseline variation: control limits undefined; collect varying baseline observations.')
    spread=3*np.sqrt(center*(1-center)/n)
    result=pd.DataFrame(dict(count=k,n=n,p=k/n,center=center,lower=np.maximum(0,center-spread),upper=np.minimum(1,center+spread)))
    result['signal']=(result.p<result.lower)|(result.p>result.upper)
    return result


def imr_chart(values, baseline_count=None):
    """I-MR limits using MRbar/1.128 and D4=3.267; three-sigma point rule.

    Recovery durations must be ordered by observed recovery time; pooling stations
    is descriptive, not evidence of a homogeneous independent process.
    """
    x=_numbers(values)
    count=len(x) if baseline_count is None else baseline_count
    if not isinstance(count,(int,np.integer)) or count<2 or count>len(x):
        raise ValueError('I-MR needs at least two baseline values.')
    center=float(x[:count].mean()); mr=np.abs(np.diff(x)); mrbar=float(mr[:count-1].mean())
    if mrbar==0:
        raise ValueError('Zero baseline variation: control limits undefined; collect varying baseline observations.')
    lower=center-3*mrbar/1.128; upper=center+3*mrbar/1.128
    return dict(center=center,lower=lower,upper=upper,mr_center=mrbar,mr_upper=3.267*mrbar,
                values=x.tolist(),moving_ranges=[None]+mr.tolist(),signal=((x<lower)|(x>upper)).tolist(),
                mr_signal=[False]+(mr>3.267*mrbar).tolist())


def hourly_chart(df, baseline_end):
    """Station/hour open-dock percent means with pooled within-hour sample SD.

    Baseline includes subgroups with n>1 whose hour ends at/before boundary;
    partial hours are retained with their observed n, and missing polls not filled.
    Limits deliberately unbounded: they are analytical limits, not feasible stock.
    Repeated polls violate independence, so display as exploratory only.
    """
    x=df.loc[df.known & df.open_pct.notna()].copy()
    x['hour']=x.timestamp.dt.floor('h')
    out=x.groupby(['station_id','hour']).open_pct.agg(['mean','count','var']).reset_index().rename(columns={'count':'n'})
    cutoff=pd.to_datetime(baseline_end,utc=True)
    baseline=out.loc[(out.hour+pd.Timedelta(hours=1)<=cutoff)&(out.n>1)]
    if baseline.empty: raise ValueError('Need a baseline subgroup with two or more known readings.')
    sigma=math.sqrt(float(((baseline.n-1)*baseline['var']).sum()/(baseline.n-1).sum()))
    if sigma==0:
        raise ValueError('Zero baseline variation: control limits undefined; collect varying baseline observations.')
    center=float((baseline['mean']*baseline.n).sum()/baseline.n.sum())
    out['center']=center; out['pooled_sigma']=sigma
    out['lower']=center-3*sigma/np.sqrt(out.n);out['upper']=center+3*sigma/np.sqrt(out.n)
    out['signal']=(out['mean']<out.lower)|(out['mean']>out.upper)
    return out


def capability(values, usl):
    """Empirical duration <= USL fraction and descriptive Ppu using sample SD."""
    x=_numbers(values,empty=True)
    if not math.isfinite(usl) or usl<0 or (x<0).any(): raise ValueError('Durations/USL must be nonnegative finite minutes.')
    mean=float(x.mean()) if len(x) else None
    sd=float(x.std(ddof=1)) if len(x)>1 else None
    ppu=(usl-mean)/(3*sd) if sd is not None and sd>0 else None
    return dict(n=len(x),mean=mean,sd=sd,compliance=float((x<=usl).mean()) if len(x) else None,
                ppu=ppu,message='Descriptive Ppu; assumes stable normal durations. Empirical SLA is primary.' if ppu is not None
                else 'Ppu undefined: need at least two varying completed durations.')


def reliability_summary(df, episodes):
    """Observed onsets / usable station-hours; unknown exposure excluded.

    MTBF here is mean usable time per observed failure onset (not calendar cycle
    time). Left-censored episodes are excluded from onsets and completed MTTR.
    """
    avail=availability_summary(df)
    failures=int((~episodes.left_censored.astype(bool)).sum()) if len(episodes) else 0
    uptime=avail['usable_minutes']/60
    durations=episodes.loc[episodes.completed.astype(bool),'duration_min'] if len(episodes) else pd.Series(dtype=float)
    rate=failures/uptime if uptime>0 else None
    return dict(uptime_hours=uptime,failures=failures,failure_rate=rate,
                mtbf_hours=uptime/failures if failures and uptime>0 else None,
                mttr_min=float(durations.mean()) if len(durations) else None,
                availability=avail['availability_pct']/100 if avail['availability_pct'] is not None else None,
                message='No failures observed; finite MTBF cannot be estimated.' if not failures else
                'Exposure rate; dependent recurrent outages, not validated constant hazard.')


def exponential_reliability(rate,t):
    if not all(math.isfinite(v) and v>=0 for v in [rate,t]): raise ValueError('Rate and time must be finite and nonnegative.')
    return math.exp(-rate*t)


def system_reliability(probabilities,structure):
    p=_numbers(probabilities)
    if (p<0).any() or (p>1).any(): raise ValueError('Reliabilities must lie in [0,1].')
    if structure=='series': return float(np.prod(p))
    if structure=='parallel': return float(1-np.prod(1-p))
    raise ValueError('Choose series or parallel; independent components assumed.')


def fmea(scores):
    """Editable judgment scores S/O/D 1..10; descending RPN, cumulative percent."""
    out=pd.DataFrame(scores).copy()
    if out.empty: return pd.DataFrame(columns=['cause','severity','occurrence','detection','RPN','cumulative_pct'])
    for key in ['severity','occurrence','detection']:
        if key not in out: raise ValueError('FMEA requires severity, occurrence and detection.')
        x=_numbers(out[key])
        if (x<1).any() or (x>10).any() or (x%1).any(): raise ValueError('FMEA scores are integers 1 through 10.')
    out['RPN']=out.severity*out.occurrence*out.detection
    out=out.sort_values('RPN',ascending=False).reset_index(drop=True)
    out['cumulative_pct']=100*out.RPN.cumsum()/out.RPN.sum()
    return out


def pareto(causes,values=None):
    if values is None: values=np.ones(len(causes))
    if len(causes)!=len(values): raise ValueError('Causes and weights must match.')
    weights=_numbers(values,empty=True)
    if (weights<0).any(): raise ValueError('Weights must be nonnegative.')
    out=pd.DataFrame({'cause':list(causes),'value':weights}).groupby('cause',as_index=False).value.sum().sort_values('value',ascending=False)
    out['cumulative_pct']=100*out.value.cumsum()/out.value.sum() if out.value.sum()>0 else 0
    return out.reset_index(drop=True)


def forecast(df,current,horizon_min=30):
    """Historical target-slot mean occupancy. No records at/after current time.

    Same weekday preferred; weekday/weekend fallback. No history yields unknown,
    never a fabricated forecast. Percent occupancy does not predict rentable bikes.
    """
    now=pd.to_datetime(current,utc=True)
    if horizon_min not in (5,30,60): raise ValueError('Choose a 30 or 60 minute horizon (5 allowed for checks).')
    target=now+pd.Timedelta(minutes=horizon_min)
    past=df.loc[(df.timestamp<now)&df.known&df.fill_pct.notna()&
                (df.service_status=='operational')&(df.effective_capacity>0)]
    slot=past.loc[(past.timestamp.dt.hour==target.hour)&(past.timestamp.dt.minute==target.minute)]
    records=[]
    for sid in df.station_id.unique():
        candidates=slot.loc[slot.station_id==sid]
        exact=candidates.loc[candidates.timestamp.dt.dayofweek==target.dayofweek]
        match=exact if len(exact) else candidates.loc[(candidates.timestamp.dt.dayofweek<5)==(target.dayofweek<5)]
        records.append(dict(station_id=sid,predicted_fill_pct=float(match.fill_pct.mean()) if len(match) else None,
                            samples=len(match),horizon_min=horizon_min,
                            message='Same weekday historical mean' if len(exact) else
                            'Weekday/weekend fallback' if len(match) else 'Insufficient historical target-slot data'))
    return pd.DataFrame(records)


def dispatch_recommendations(current,history,episodes,weights=(.35,.25,.2,.2),target_min=15):
    """Editable priority heuristic; nearest donor/recipient pairs, no route optimum.

    Score weights: current severity, elapsed outage, historic unusable frequency,
    and observed absolute inventory change proxy (not trips). All factors 0..1.
    """
    w=_numbers(weights)
    if len(w)!=4 or (w<0).any() or w.sum()<=0 or not math.isfinite(target_min) or target_min<=0: raise ValueError('Four nonnegative weights with positive sum and target required.')
    out=current.copy()
    if out.empty: return {'ranked':pd.DataFrame(),'pairs':pd.DataFrame()}
    out=out.sort_values('timestamp').drop_duplicates('station_id',keep='last')
    now=out.timestamp.max()
    history=history.loc[history.timestamp<=now]
    freq=history.groupby('station_id').apply(lambda g: float(g.loc[g.known,'unusable'].mean()) if g.known.any() else 0)
    changes=history.sort_values(['station_id','timestamp']).groupby('station_id').bikes.apply(lambda s: float(s.diff().abs().mean()) if len(s)>1 else 0)
    scores=[];actions=[];elapsed_values=[]
    for row in out.itertuples():
        active=episodes.loc[(episodes.station_id==row.station_id)&(episodes.start<=row.timestamp)&(episodes.end>row.timestamp)]
        elapsed=(row.timestamp-active.start.iloc[-1]).total_seconds()/60+POLL_MIN if len(active) else 0
        severity={'empty':1,'full':1,'offline':1,'unknown':.9,'low':.5,'high':.5,'medium':0}[row.status]
        action='Check telemetry' if row.status=='unknown' else 'Repair station' if row.status=='offline' else 'Deliver bikes' if row.status in ('empty','low') else 'Collect bikes' if row.status in ('full','high') else 'Monitor'
        factors=[severity,min(1,elapsed/target_min),freq.get(row.station_id,0),min(1,changes.get(row.station_id,0)/max(1,row.total_docks)*5)]
        scores.append(float(np.dot(w/w.sum(),factors)*100));actions.append(action);elapsed_values.append(elapsed)
    out['priority_score']=scores;out['action']=actions;out['elapsed_min']=elapsed_values
    out=out.sort_values('priority_score',ascending=False).reset_index(drop=True)
    donors=out.loc[out.action=='Collect bikes'].copy();pairs=[]
    for receiver in out.loc[out.action=='Deliver bikes'].itertuples():
        if donors.empty: break
        distances=(donors.latitude-receiver.latitude)**2+(donors.longitude-receiver.longitude)**2
        donor=donors.loc[distances.idxmin()]
        bikes=max(0,min(int(donor.bikes)-int(donor.effective_capacity*.5),int(receiver.open_docks),max(0,int(receiver.effective_capacity*.5)-receiver.bikes)))
        if bikes>0: pairs.append(dict(from_station=donor.station_id,to_station=receiver.station_id,bikes=bikes))
        donors=donors.drop(donor.name)
    return {'ranked':out,'pairs':pd.DataFrame(pairs,columns=['from_station','to_station','bikes'])}


def heatmap_data(df):
    """Known-only unusable percent by weekday/hour; absent cells remain absent."""
    x=df.loc[df.known].copy()
    x['weekday']=x.timestamp.dt.dayofweek
    x['hour']=x.timestamp.dt.hour
    return x.groupby(['weekday','hour'],as_index=False).unusable.mean().rename(columns={'unusable':'unusable_fraction'})


def station_summary(df,episodes,usl=15):
    records=[]
    for sid,group in df.groupby('station_id'):
        ep=episodes.loc[episodes.station_id==sid]
        cap=capability(ep.loc[ep.completed.astype(bool),'duration_min'],usl)
        avail=availability_summary(group)
        records.append(dict(station_id=sid,station_name=group.station_name.iloc[0],district=group.district.iloc[0],
                            availability_pct=avail['availability_pct'],events=len(ep),
                            mean_recovery_min=cap['mean'],compliance=cap['compliance'],
                            unknown_minutes=avail['unknown_minutes']))
    return pd.DataFrame(records)


def ticket_summary(orders,as_of):
    """Replay-safe ticket view; hide assignments/resolutions in the future."""
    now=pd.to_datetime(as_of,utc=True)
    x=orders.copy()
    for col in ['opened_at','assigned_at','resolved_at']:
        x[col]=pd.to_datetime(x[col],utc=True,format='mixed',errors='raise')
    if ((x.assigned_at<x.opened_at)|(x.resolved_at<x.assigned_at)).any(): raise ValueError('Ticket times are inconsistent.')
    x=x.loc[x.opened_at<=now].copy()
    x.loc[x.assigned_at>now,'assigned_at']=pd.NaT
    x.loc[x.resolved_at>now,'resolved_at']=pd.NaT
    x['response_min']=(x.assigned_at-x.opened_at).dt.total_seconds()/60
    x['repair_min']=(x.resolved_at-x.opened_at).dt.total_seconds()/60
    repeat=x.groupby('station_id',as_index=False).size().rename(columns={'size':'tickets'}).sort_values('tickets',ascending=False)
    return dict(backlog=int(x.resolved_at.isna().sum()),
                mean_response_min=float(x.response_min.mean()) if x.response_min.notna().any() else None,
                mean_repair_min=float(x.repair_min.mean()) if x.repair_min.notna().any() else None,
                repeat_offenders=repeat,orders=x)


def failure_counts(df,episodes,orders,as_of):
    """Separate inventory outage episodes from technical tickets; never sum both
    into a purported unique-failure count because they can overlap in time.
    """
    now=pd.to_datetime(as_of,utc=True)
    records=[]
    ep=episodes.loc[episodes.start<=now]
    for reason in ['empty','full']:
        matched=ep.loc[ep.reason==reason]
        duration=sum(min(float(row.duration_min),max(0,(now-row.start).total_seconds()/60+POLL_MIN)) for row in matched.itertuples())
        records.append(dict(mode=reason,category='inventory',count=len(matched),downtime_min=duration))
    tickets=ticket_summary(orders,now)['orders']
    for cause,group in tickets.groupby('cause'):
        durations=(group.resolved_at.fillna(now)-group.opened_at).dt.total_seconds()/60
        records.append(dict(mode=cause,category='technical',count=len(group),downtime_min=float(durations.sum())))
    return pd.DataFrame(records,columns=['mode','category','count','downtime_min'])


def default_fmea(counts):
    """Proposed editable judgments; occurrence is a relative count scale, not probability."""
    if counts.empty: return fmea(pd.DataFrame())
    out=counts[['mode','count']].rename(columns={'mode':'cause'}).copy()
    maximum=max(1,out['count'].max())
    out['severity']=8
    out['occurrence']=np.maximum(1,np.ceil(10*out['count']/maximum)).astype(int)
    out['detection']=3
    return fmea(out)
