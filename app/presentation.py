"""Safe HTML and plotting helpers. Statistical values are supplied by qc.py."""
import base64
import html
import io
import json
import math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

COLORS={'empty':'#c54d4d','low':'#bd792d','medium':'#2a806d','high':'#477ab1',
        'full':'#8262a7','offline':'#4b515c','unknown':'#717887'}
CSS='''
:root{--ink:#233c43;--muted:#70818a;--line:#e0e7e9;--paper:#f3f6f7;--accent:#246d61}
body{font-family:"Segoe UI",Arial,sans-serif;color:var(--ink);background:var(--paper);font-size:14px}
.bslib-sidebar-layout>.main{padding:25px 32px!important}.bslib-sidebar-layout>.sidebar{background:#fff;border-right:1px solid var(--line)}
.brand{display:flex;align-items:center;gap:11px;font-size:21px;font-weight:750;letter-spacing:-.7px;margin:18px 0 28px}.brand-mark{background:#246d61;color:white;border-radius:12px;width:38px;height:38px;display:grid;place-items:center;font-size:25px}
.eyebrow{text-transform:uppercase;letter-spacing:1.8px;font-size:10px;font-weight:750;color:#748a8e}.sidebar-note{font-size:11px;line-height:1.7;color:var(--muted);padding:16px 3px;border-top:1px solid var(--line);margin-top:24px}
.nav-pages .shiny-options-group{display:flex;flex-direction:column;gap:5px}.nav-pages .radio{margin:0}.nav-pages .radio label{display:block;width:100%;padding:11px 13px;border-radius:8px;color:#63777d;font-weight:550;cursor:pointer}.nav-pages input{position:absolute;opacity:0}.nav-pages label:has(input:checked){background:#e8f2ee;color:#246d61;font-weight:700}.nav-pages label:focus-within{outline:2px solid #246d61}.nav-pages label:hover{background:#f0f5f4}
.topbar{display:flex;justify-content:space-between;align-items:center;gap:16px;margin:0 0 20px}.topbar h1{font-size:27px;font-weight:720;letter-spacing:-.9px;margin:5px 0}.topbar p{margin:0;color:var(--muted)}
.filterbar,.replaybar{background:white;border:1px solid var(--line);border-radius:10px;padding:14px 18px;margin-bottom:15px}.filterbar .shiny-input-container{margin-bottom:0}.replaybar{background:#edf3f1}
.kpis{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:15px;margin:18px 0}.kpi{background:#fff;border:1px solid var(--line);border-radius:11px;padding:19px 20px;min-height:112px}.kpi-label{color:#71848a;font-size:12px;font-weight:600}.kpi-value{font-size:29px;font-weight:720;letter-spacing:-1px;margin:7px 0 3px}.kpi-note{font-size:11px;color:#7a898e}
.panel{background:white;border:1px solid var(--line);border-radius:11px;padding:20px;margin-bottom:17px;min-width:0}.panel-head{margin-bottom:17px}.panel-head h3{font-size:16px;font-weight:700;margin:0 0 5px}.panel-head p{font-size:12px;color:var(--muted);margin:0}.split{display:grid;grid-template-columns:minmax(0,2fr) minmax(270px,1fr);gap:18px}.three-col{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:17px}.muted,.small{color:var(--muted);font-size:12px}.small{font-size:11px}.note,.warning{padding:12px 15px;border-radius:7px;background:#edf4f1;color:#476e64;line-height:1.6;font-size:12px;margin:11px 0}.warning{background:#fff5e6;color:#8b622b;border-left:3px solid #d5a44c}
.table-wrap{overflow:auto;max-height:570px}table{width:100%;border-collapse:collapse;font-size:12px}th{text-align:left;font-size:10px;text-transform:uppercase;letter-spacing:.6px;color:#75878c;background:#f6f8f8;position:sticky;top:0;padding:11px 10px;white-space:nowrap}td{padding:11px 10px;border-bottom:1px solid #edf1f2;white-space:nowrap}tbody tr:hover{background:#fafcfb}.empty-state{padding:40px 18px;text-align:center;color:#7b8a8f;background:#f8faf9;border-radius:8px}
.badge{display:inline-flex;align-items:center;gap:5px;padding:4px 8px;border-radius:5px;font-size:11px;font-weight:650;background:#edf2f3;color:#65767d}.status-empty{color:#c54d4d;background:#fbecec}.status-low{color:#bd792d;background:#fff2df}.status-medium{color:#2a806d;background:#e6f3ed}.status-high{color:#477ab1;background:#eaf1fa}.status-full{color:#8262a7;background:#f1ebf7}.status-offline{color:#4b515c;background:#e9ebee}.status-unknown{color:#717887;background:#eef0f3}
.dock-grid{display:flex;gap:6px;flex-wrap:wrap;margin:15px 0}.dock{display:grid;place-items:center;width:29px;height:33px;border-radius:4px;border:1px solid #cbd7d9;font-size:15px;font-weight:700}.dock.occupied{background:#dceee6;color:#2a806d}.dock.broken-bike{background:#f8e4e1;color:#c54d4d}.dock.broken{background:repeating-linear-gradient(45deg,#eee,#eee 3px,#ddd 3px,#ddd 5px);color:#666}.dock.open{color:#9eafb3;background:white}.legend{display:flex;flex-wrap:wrap;gap:13px;font-size:11px;color:#728389;margin:11px 0}.legend span{white-space:nowrap}.section-title{font-size:18px;font-weight:700;margin:23px 0 15px}.task{border:1px solid var(--line);border-left:3px solid #246d61;border-radius:7px;padding:14px;margin-bottom:12px}.task h4{font-size:14px;font-weight:700}.plot-image{width:100%;height:auto;display:block}.station-map{width:100%;height:auto;border-radius:8px;background:#f5f8f7}.station-map .station-node:focus{outline:3px solid #246d61}.btn-primary{background:#246d61;border-color:#246d61}.form-control,.form-select{border-color:#d6e0e2;font-size:13px;border-radius:6px}
@media(max-width:1100px){.kpis{grid-template-columns:repeat(2,minmax(0,1fr))}.split{grid-template-columns:1fr}.three-col{grid-template-columns:1fr 1fr}}
@media(max-width:650px){.bslib-sidebar-layout>.main{padding:15px!important}.topbar{align-items:flex-start;flex-direction:column}.topbar h1{font-size:23px}.kpis{gap:8px}.kpi{padding:13px}.kpi-value{font-size:24px}.three-col{grid-template-columns:1fr}.panel{padding:14px}}
'''


def fmt(value,digits=1,suffix=''):
    if value is None or pd.isna(value): return '—'
    if isinstance(value,(float,int,np.number)):
        if not math.isfinite(float(value)): return '—'
        return f'{value:,.{digits}f}{suffix}'
    return html.escape(str(value))+html.escape(suffix)


def card(title,body,subtitle=''):
    return f'<section class="panel"><div class="panel-head"><h3>{html.escape(str(title))}</h3><p>{html.escape(str(subtitle))}</p></div>{body}</section>'


def note(text,kind='note'):
    return f'<div class="{"warning" if kind=="warning" else "note"}">{html.escape(str(text))}</div>'


def html_table(df,max_rows=100):
    if df is None or df.empty: return '<div class="empty-state">No observations match these filters.</div>'
    headers=''.join(f'<th>{html.escape(str(c).replace("_"," "))}</th>' for c in df.columns)
    rows=[]
    for row in df.head(max_rows).itertuples(index=False,name=None):
        cells=[]
        for value in row:
            if value is None or pd.isna(value): text='—'
            elif isinstance(value,pd.Timestamp): text=value.strftime('%b %d %H:%M UTC')
            elif isinstance(value,(float,np.floating)): text=f'{value:,.3g}'
            else: text=str(value)
            cells.append('<td>'+html.escape(text)+'</td>')
        rows.append('<tr>'+''.join(cells)+'</tr>')
    extra=f'<p class="small">Showing {min(len(df),max_rows)} of {len(df)} rows.</p>'
    return '<div class="table-wrap"><table><thead><tr>'+headers+'</tr></thead><tbody>'+''.join(rows)+'</tbody></table></div>'+extra


def legend():
    symbols={'empty':'●','low':'▲','medium':'■','high':'◆','full':'⬟','offline':'×','unknown':'?'}
    return '<div class="legend">'+''.join(f'<span style="color:{COLORS[s]}">{shape} {s.title()}</span>' for s,shape in symbols.items())+'</div>'


def station_map(current,selected=None):
    if current.empty: return '<div class="empty-state">No stations to map.</div>'
    x=current.copy()
    west,east=float(x.longitude.min()),float(x.longitude.max())
    south,north=float(x.latitude.min()),float(x.latitude.max())
    sx=lambda v: 80+(float(v)-west)/max(east-west,.001)*640
    sy=lambda v: 440-(float(v)-south)/max(north-south,.001)*340
    parts=['<svg class="station-map" viewBox="0 0 800 540" role="img" aria-label="Synthetic station coordinate schematic, not a street map"><title>Synthetic coordinate schematic — not a street map</title><rect x="50" y="60" width="710" height="410" rx="8" fill="#edf3f0"/>']
    for district,group in x.groupby('district'):
        # Annotation positions use the first actual station in each district.
        anchor=group.iloc[0]
        parts.append(f'<text x="{sx(anchor.longitude):.1f}" y="{max(45,sy(anchor.latitude)-35):.1f}" fill="#83978e" font-size="12">{html.escape(str(district))}</text>')
    for row in x.itertuples():
        px,py=sx(row.longitude),sy(row.latitude);status=row.status;color=COLORS.get(status,COLORS['unknown'])
        sid=html.escape(str(row.station_id));label=html.escape(f'{row.station_name}: {status}, {row.bikes} rentable bikes, {row.open_docks} open docks')
        command=html.escape("Shiny.setInputValue('map_station',"+json.dumps(str(row.station_id))+",{priority:'event'})",quote=True)
        parts.append(f'<g class="station-node" tabindex="0" role="button" aria-label="{label}" onclick="{command}" onkeydown="if(event.key===\'Enter\'){{{command}}}"><title>{label}</title>')
        if str(row.station_id)==str(selected): parts.append(f'<circle cx="{px}" cy="{py}" r="22" fill="none" stroke="#163f36" stroke-width="2"/>')
        style=f'fill="{color}" stroke="white" stroke-width="2"'
        if status=='low': shape=f'<polygon points="{px},{py-15} {px-14},{py+12} {px+14},{py+12}" {style}/>'
        elif status=='medium': shape=f'<rect x="{px-12}" y="{py-12}" width="24" height="24" rx="3" {style}/>'
        elif status=='high': shape=f'<polygon points="{px},{py-16} {px+15},{py} {px},{py+16} {px-15},{py}" {style}/>'
        elif status=='full':
            points=' '.join(f'{px+16*math.cos(-math.pi/2+i*2*math.pi/5):.1f},{py+16*math.sin(-math.pi/2+i*2*math.pi/5):.1f}' for i in range(5))
            shape=f'<polygon points="{points}" {style}/>'
        else:
            shape=f'<circle cx="{px}" cy="{py}" r="14" {style}/>'
            if status in ('offline','unknown'): shape+=f'<text x="{px}" y="{py+5}" text-anchor="middle" fill="white" font-size="19" font-weight="700">{"×" if status=="offline" else "?"}</text>'
        parts.append(shape+f'<text x="{px}" y="{py+31}" text-anchor="middle" fill="#536d66" font-size="11" font-weight="650">{sid}</text></g>')
    parts.append(f'<text x="50" y="506" fill="#758b81" font-size="11">Longitude {west:.3f} to {east:.3f}° · Latitude {south:.3f} to {north:.3f}°</text><text x="50" y="524" fill="#758b81" font-size="11">Invented station geometry · select a marker for station details</text></svg>')
    return ''.join(parts)+legend()


def dock_grid(row):
    get=lambda key: row[key] if isinstance(row,(dict,pd.Series)) else getattr(row,key)
    groups=[('occupied',int(get('bikes')),'●','Rentable bike'),('broken-bike',int(get('broken_bikes')),'×','Broken bike'),
            ('open',int(get('open_docks')),'□','Open dock'),('broken',int(get('broken_docks')),'/','Broken dock')]
    body='<div class="dock-grid">'+''.join(f'<span class="dock {kind}" title="{label}" aria-label="{label}">{symbol}</span>'*count for kind,count,symbol,label in groups)+'</div>'
    body+='<p class="small">Illustrative positions from aggregate counts; individual dock IDs are not measured.</p>'
    body+='<div class="legend"><span>● Rentable bike</span><span>× Broken bike</span><span>□ Open dock</span><span>/ Broken dock</span></div>'
    if int(get('broken_docks')): body+=note('Broken docks reduce effective capacity; occupancy is based on working docks.','warning')
    return body


def figure_html(fig,alt):
    buffer=io.BytesIO()
    fig.savefig(buffer,format='png',dpi=140,bbox_inches='tight',facecolor='white')
    plt.close(fig)
    return f'<img class="plot-image" alt="{html.escape(str(alt),quote=True)}" src="data:image/png;base64,{base64.b64encode(buffer.getvalue()).decode()}"/>'


def _axes(title='',ylabel=''):
    fig,ax=plt.subplots(figsize=(9,3.2))
    ax.spines[['top','right']].set_visible(False)
    ax.spines[['left','bottom']].set_color('#dbe4e4')
    ax.tick_params(colors='#73858b',labelsize=9)
    ax.grid(axis='y',color='#edf1f0',linewidth=.8)
    ax.set_axisbelow(True);ax.set_title(title,loc='left',fontsize=11,color='#334e53',pad=16)
    ax.set_ylabel(ylabel,fontsize=9,color='#73858b')
    return fig,ax


def line_chart(x,values,center=None,lower=None,upper=None,signals=None,ylabel='',title=''):
    if len(values)==0: return '<div class="empty-state">Not enough observations to plot.</div>'
    fig,ax=_axes(title,ylabel)
    ax.plot(x,values,color='#367d70',linewidth=1.5,label='Observed')
    for data,label,color,style in [(center,'Baseline center','#7a8d91','--'),(lower,'Lower limit','#c47c73','--'),(upper,'Upper limit','#c47c73','--')]:
        if data is not None:
            if np.isscalar(data): ax.axhline(data,color=color,linestyle=style,linewidth=1,label=label)
            else: ax.plot(x,data,color=color,linestyle=style,linewidth=1,label=label)
    if signals is not None:
        flags=np.asarray(signals,dtype=bool)
        ax.scatter(np.asarray(x)[flags],np.asarray(values)[flags],s=23,color='#c54d4d',zorder=4,label='Three-sigma signal')
    ax.legend(frameon=False,fontsize=8,loc='best');fig.autofmt_xdate(rotation=25)
    return figure_html(fig,title or ylabel)


def heatmap_chart(frame):
    if frame.empty: return '<div class="empty-state">No known observations in this window.</div>'
    matrix=frame.pivot(index='weekday',columns='hour',values='unusable_fraction').reindex(index=range(7),columns=range(24))
    fig,ax=plt.subplots(figsize=(10,3.1))
    cmap=plt.get_cmap('YlOrRd').copy();cmap.set_bad('#e9eeee')
    image=ax.imshow(matrix.to_numpy(dtype=float)*100,aspect='auto',vmin=0,vmax=100,cmap=cmap)
    ax.set_yticks(range(7),['Mon','Tue','Wed','Thu','Fri','Sat','Sun']);ax.set_xticks(range(0,24,2),[f'{h:02d}' for h in range(0,24,2)])
    ax.set_xlabel('Hour · demonstration UTC clock',fontsize=9);ax.tick_params(labelsize=9,length=0)
    fig.colorbar(image,ax=ax,label='Unusable known observations (%)',shrink=.85)
    for spine in ax.spines.values(): spine.set_visible(False)
    return figure_html(fig,'Weekday and hour unusable percentage heatmap. Gray cells have no known observations.')


def pareto_chart(frame,value_col='value',label_col='cause',title=''):
    if frame.empty: return '<div class="empty-state">No recorded causes in this window.</div>'
    fig,ax=_axes(title,value_col.replace('_',' ').title())
    positions=np.arange(len(frame))
    ax.bar(positions,frame[value_col],color='#4a8c7d',width=.65)
    ax.set_xticks(positions,frame[label_col].astype(str),rotation=25,ha='right')
    if 'cumulative_pct' in frame:
        second=ax.twinx();second.plot(positions,frame.cumulative_pct,color='#bb8a45',marker='o',markersize=4)
        second.set_ylim(0,105);second.set_ylabel('Cumulative %',color='#8c8068',fontsize=9)
        second.spines[['top','left']].set_visible(False);second.tick_params(labelsize=8,colors='#8c8068')
    return figure_html(fig,title or 'Pareto chart of recorded causes')


def histogram(values,usl):
    if not len(values): return '<div class="empty-state">No completed recoveries in this window.</div>'
    fig,ax=_axes('Completed recovery durations','Completed episodes')
    ax.hist(values,bins='auto',color='#78aa99',edgecolor='white')
    ax.axvline(usl,color='#c47b51',linestyle='--',label=f'Editable SLA: {usl:g} min')
    ax.set_xlabel('Recovery duration (minutes)',fontsize=9);ax.legend(frameon=False,fontsize=9)
    return figure_html(fig,'Distribution of completed recovery durations with editable service target')


def reliability_plot(times,probabilities):
    fig,ax=_axes('Illustrative constant-hazard reliability','Reliability R(t)')
    ax.plot(times,probabilities,color='#477ab1',linewidth=2)
    ax.set_ylim(0,1.03);ax.set_xlabel('Time (hours)',fontsize=9)
    return figure_html(fig,'Exponential reliability illustration; constant hazard is assumed')
