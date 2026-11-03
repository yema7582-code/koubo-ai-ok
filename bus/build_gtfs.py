# GTFS-JP -> compact JSON for the big-type next-bus page. Works for any GTFS-JP feed.
import csv, json, sys, os, collections
src = sys.argv[1]; out = sys.argv[2]
def rd(n):
    p = os.path.join(src, n)
    if not os.path.exists(p): return []
    with open(p, encoding='utf-8-sig') as f: return list(csv.DictReader(f))
tr = collections.defaultdict(dict)
for r in rd('translations.txt'):
    if r['table_name']=='stops' and r['field_name']=='stop_name':
        key = r['record_id'] or r.get('field_value','')
        tr[key][r['language']] = r['translation']
routes = {r['route_id']: r for r in rd('routes.txt')}
trips = {t['trip_id']: t for t in rd('trips.txt')}
stops = {s['stop_id']: s for s in rd('stops.txt') if s.get('location_type','0') in ('','0')}
# group platforms by stop name
groups = collections.OrderedDict()
for sid, s in stops.items():
    g = groups.setdefault(s['stop_name'], {'n': s['stop_name'], 'k': '', 'e': '', 'ids': [], 'lat': [], 'lon': []})
    g['ids'].append(sid); g['lat'].append(float(s['stop_lat'])); g['lon'].append(float(s['stop_lon']))
    t = tr.get(sid) or tr.get(s['stop_name']) or {}
    g['k'] = g['k'] or t.get('ja-Hrkt', ''); g['e'] = g['e'] or t.get('en', '')
id2g = {}
glist = []
for i, g in enumerate(groups.values()):
    for sid in g['ids']: id2g[sid] = i
    glist.append({'n': g['n'], 'k': g['k'], 'e': g['e'], 'la': round(sum(g['lat'])/len(g['lat']), 6), 'lo': round(sum(g['lon'])/len(g['lon']), 6)})
# last stop per trip (to skip arrivals-only at terminus)
st = collections.defaultdict(list)
for r in rd('stop_times.txt'): st[r['trip_id']].append(r)
rl = {}; rlist = []
def rix(rid):
    if rid not in rl:
        r = routes[rid]; rl[rid] = len(rlist)
        rlist.append({'n': r['route_long_name'] or r['route_short_name'], 'c': r.get('route_color') or '333333', 't': r.get('route_text_color') or 'FFFFFF'})
    return rl[rid]
svc = {}; slist = []
def six(s):
    if s not in svc: svc[s] = len(slist); slist.append(s)
    return svc[s]
hs = {}; hlist = []
def hix(h):
    if h not in hs: hs[h] = len(hlist); hlist.append(h)
    return hs[h]
dep = collections.defaultdict(list)  # group -> [min, route, headsign, service]
for tid, rows in st.items():
    rows.sort(key=lambda r: int(r['stop_sequence']))
    t = trips.get(tid)
    if not t: continue
    last = rows[-1]['stop_id']
    for r in rows[:-1]:
        if r.get('pickup_type') == '1': continue
        h, m, *_ = (r['departure_time'] or r['arrival_time']).split(':')
        mins = int(h)*60 + int(m)
        head = r.get('stop_headsign') or t.get('trip_headsign') or stops.get(last, {}).get('stop_name', '')
        g = id2g.get(r['stop_id'])
        if g is None: continue
        dep[g].append([mins, rix(t['route_id']), hix(head), six(t['service_id'])])
for g in dep: dep[g].sort()
cal = {}
for c in rd('calendar.txt'):
    if c['service_id'] in svc:
        cal[c['service_id']] = {'d': [int(c[d]) for d in ['monday','tuesday','wednesday','thursday','friday','saturday','sunday']], 's': c['start_date'], 'e': c['end_date']}
ex = collections.defaultdict(dict)
for c in rd('calendar_dates.txt'):
    if c['service_id'] in svc: ex[c['date']][c['service_id']] = int(c['exception_type'])
fi = (rd('feed_info.txt') or [{}])[0]; ag = (rd('agency.txt') or [{}])[0]
data = {'agency': ag.get('agency_name',''), 'phone': ag.get('agency_phone',''), 'url': ag.get('agency_url',''),
        'version': fi.get('feed_version','').split('-')[0], 'start': fi.get('feed_start_date',''), 'end': fi.get('feed_end_date',''),
        'stops': glist, 'routes': rlist, 'heads': hlist, 'svc': slist, 'cal': cal, 'ex': ex,
        'dep': {str(k): v for k, v in dep.items()}}
with open(out, 'w', encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
print(len(glist), 'stops', sum(len(v) for v in dep.values()), 'departures', os.path.getsize(out), 'bytes')
