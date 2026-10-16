"""Reproduce full-window synthetic scenario results from the repository root."""
import hashlib
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import pandas as pd
from app import qc


def main():
    results=[]
    for name in ['normal_week','high_failure_week','improvement_week']:
        folder=ROOT/'data'/name
        frame=qc.prepare_snapshots(pd.read_csv(folder/'snapshots.csv.gz'))
        orders=pd.read_csv(folder/'work_orders.csv')
        episodes=qc.outage_episodes(frame)
        availability=qc.availability_summary(frame)
        cap=qc.capability(episodes.loc[episodes.completed.astype(bool),'duration_min'],15)
        reliability=qc.reliability_summary(frame,episodes)
        result=dict(scenario=name,rows=len(frame),availability_pct=round(availability['availability_pct'],6),
            coverage_pct=round(availability['coverage_pct'],6),unusable_minutes=availability['unusable_minutes'],
            episodes=len(episodes),completed_episodes=cap['n'],
            completed_mean_recovery_min=round(cap['mean'],6) if cap['mean'] is not None else None,
            within15_pct=round(cap['compliance']*100,6) if cap['compliance'] is not None else None,
            technical_tickets=len(orders),mtbf_hours=round(reliability['mtbf_hours'],6) if reliability['mtbf_hours'] is not None else None,
            snapshot_sha256=hashlib.sha256((folder/'snapshots.csv.gz').read_bytes()).hexdigest())
        results.append(result)
        print(json.dumps(result,sort_keys=False))
        replay=qc.ticket_summary(orders,frame.timestamp.max())
        assert len(replay['orders'])==len(orders)
    assert results[1]['availability_pct']<results[0]['availability_pct']<results[2]['availability_pct']
    assert [r['rows'] for r in results]==[120960]*3
    assert [r['technical_tickets'] for r in results]==[44,132,22]
    print('PASS: all three synthetic scenarios reproduce; failure < normal < simulated improvement availability.')


if __name__=='__main__': main()
