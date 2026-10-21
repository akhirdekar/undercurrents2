"""Prepare an auditable browser snapshot from the supplied cleaned CSVs.

Run after fetch_sources.py. Uses pandas/numpy/matplotlib, no GIS account.
"""
from pathlib import Path
import argparse, json, math, hashlib
import numpy as np
import pandas as pd
from matplotlib.path import Path as PolygonPath

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / 'source_cache'
OUT = ROOT / 'dist' / 'data'
BOROUGHS = ['Unknown', 'Manhattan', 'Bronx', 'Brooklyn', 'Queens', 'Staten Island']
CATEGORIES = ['Clogged / flooding', 'Sunken / damaged / raised', 'Basin search', 'Missing grating', 'Broken connection']
RADIUS = math.sqrt(1_000_000 / (3 * math.sqrt(3) / 2))

def project(lon, lat):
    """Spherical Lambert azimuthal equal area, metres, NYC centred."""
    phi, lam = np.radians(lat), np.radians(lon)
    p0, l0 = np.radians(40.71), np.radians(-73.94)
    k = np.sqrt(2 / (1 + np.sin(p0)*np.sin(phi) + np.cos(p0)*np.cos(phi)*np.cos(lam-l0)))
    return (6371008.8*k*np.cos(phi)*np.sin(lam-l0),
            6371008.8*k*(np.cos(p0)*np.sin(phi)-np.sin(p0)*np.cos(phi)*np.cos(lam-l0)))

def hex_coordinates(x, y):
    q, r = (2/3*x)/RADIUS, (-x/3 + np.sqrt(3)*y/3)/RADIUS
    s = -q-r
    # JS Math.round compatibility for half ties; numerical half ties are rare.
    rq, rr, rs = np.floor(q+.5), np.floor(r+.5), np.floor(s+.5)
    dq, dr, ds = abs(rq-q), abs(rr-r), abs(rs-s)
    fixq, fixr = (dq>dr)&(dq>ds), (~((dq>dr)&(dq>ds)))&(dr>ds)
    rq[fixq] = -rr[fixq]-rs[fixq]
    rr[fixr] = -rq[fixr]-rs[fixr]
    return rq.astype(int), rr.astype(int)

def category(text):
    if 'Clogged/Flooding' in text: return 0
    if 'Sunken/Damaged/Raised' in text: return 1
    if 'Search' in text: return 2
    if 'Grating Missing' in text: return 3
    if 'Connection Broken' in text: return 4
    raise ValueError('Unmapped descriptor: '+text)

def simplify(points, tolerance=12):
    """Ramer-Douglas-Peucker in projected metres, for display only."""
    a=np.asarray(points)
    if len(a)<4: return a.tolist()
    # Closed rings use an open recursion with a stable non-identical endpoint.
    closed=np.linalg.norm(a[0]-a[-1])<.01
    if closed:a=a[:-1]
    def rdp(v):
        if len(v)<3:return v
        diff=v[-1]-v[0]; denom=np.linalg.norm(diff)
        dist=np.linalg.norm(v-v[0],axis=1) if denom==0 else np.abs(np.cross(diff,v-v[0]))/denom
        i=int(np.argmax(dist))
        if dist[i]<=tolerance:return v[[0,-1]]
        return np.concatenate([rdp(v[:i+1])[:-1],rdp(v[i:])])
    b=rdp(a)
    if closed:b=np.concatenate([b,b[:1]])
    return np.round(b,1).tolist()

def assign_boroughs(df, features):
    coords=df[['LONGITUDE','LATITUDE']].to_numpy()
    codes=np.zeros(len(df),dtype=int)
    for f in features:
        code=int(f['properties']['borocode'])
        for polygon in f['geometry']['coordinates']:
            outer=PolygonPath(np.asarray(polygon[0]))
            inside=outer.contains_points(coords)
            for hole in polygon[1:]:inside &= ~PolygonPath(np.asarray(hole)).contains_points(coords)
            codes[inside]=code
    return codes

def audit(df):
    return {'rows':len(df), 'columns':list(df.columns),
            'nulls':{k:int(v) for k,v in df.isna().sum().items()},
            'duplicate_ids':int(df.UNITID.duplicated().sum()),
            'duplicate_rows':int(df.duplicated().sum()),
            'distinct_coordinates':int(df[['LATITUDE','LONGITUDE']].drop_duplicates().shape[0])}

def write_json(name, data):
    (OUT/name).write_text(json.dumps(data,separators=(',',':'),allow_nan=False))

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--inputs', type=Path,default=ROOT/'source_data')
    args=parser.parse_args();OUT.mkdir(exist_ok=True,parents=True)
    basins=pd.read_csv(args.inputs/'clean_basins.csv',dtype={'UNITID':str})
    reports=pd.read_csv(args.inputs/'clean_complaints.csv',dtype={'UNITID':str})
    features=json.loads((CACHE/'boroughs.geojson').read_text())['features']
    profiles={'basins':audit(basins),'complaints':audit(reports)}
    for df in [basins,reports]:
        if not df.UNITID.is_unique:raise ValueError('Duplicate source IDs')
        if not np.isfinite(df[['LATITUDE','LONGITUDE']]).all().all():raise ValueError('Invalid coordinates')
        if not (df.LATITUDE.between(40.45,40.95)&df.LONGITUDE.between(-74.30,-73.65)).all():raise ValueError('Outside NYC envelope')

    source=json.loads((CACHE/'311_dates.json').read_text())
    if len(source)>=150000:raise ValueError('API limit reached; paginate before using this snapshot')
    meta={str(row['unique_key']):row for row in source}
    reports['created_date']=[meta.get(i,{}).get('created_date','')[:10] for i in reports.UNITID]
    reports['category']=reports['Problem Detail (formerly Descriptor)'].map(category)
    restored=int(reports.created_date.ne('').sum())
    if restored!=len(reports):print('WARNING: unmatched report dates',len(reports)-restored)
    profiles['date_restoration']={'matched':restored,'unmatched':len(reports)-restored,'fetched_source_rows':len(source),'join':'complaint UNITID = 311 unique_key; never a join to basin UNITID'}
    profiles['source_descriptor_changes']=sum(meta.get(i,{}).get('descriptor',d)!=d for i,d in zip(reports.UNITID,reports['Problem Detail (formerly Descriptor)']))
    outputs=[]
    for df, name in [(basins,'basins'),(reports,'reports')]:
        df['borough']=assign_boroughs(df,features)
        x,y=project(df.LONGITUDE.to_numpy(),df.LATITUDE.to_numpy())
        q,r=hex_coordinates(x,y)
        df['x']=np.round(x,1);df['y']=np.round(y,1);df['q']=q;df['r']=r
        profiles[name+'_boroughs']={BOROUGHS[int(k)]:int(v) for k,v in df.borough.value_counts().items()}
        rows=[]
        for row in df.itertuples(index=False):
            v=row._asdict()
            vals=[v['UNITID'],round(float(v['LONGITUDE']),8),round(float(v['LATITUDE']),8),int(v['borough']),float(v['x']),float(v['y']),int(v['q']),int(v['r'])]
            if name=='reports':vals += [int(v['category']),v['created_date']]
            rows.append(vals)
        write_json(name+'.json',rows)
        outputs.append(rows)

    borough_map=[]
    for f in features:
        polygons=[]
        for polygon in f['geometry']['coordinates']:
            rings=[]
            for ring in polygon:
                ar=np.asarray(ring);x,y=project(ar[:,0],ar[:,1]);rings.append(simplify(np.column_stack([x,y])))
            polygons.append(rings)
        borough_map.append({'code':int(f['properties']['borocode']),'name':f['properties']['boroname'],'polygons':polygons})
    write_json('boroughs.json',borough_map)

    # GHCN by_station CSV: ID,DATE,ELEMENT,DATA_VALUE,M_FLAG,Q_FLAG,S_FLAG,OBS_TIME
    rain=pd.read_csv(CACHE/'central_park.csv.gz',header=None,
        names=['id','date','element','value','mflag','qflag','sflag','obstime'],dtype={'date':str},keep_default_na=False)
    dated=reports.loc[reports.created_date.ne(''),'created_date']
    start, end=dated.min(),dated.max()
    rain=rain[rain.element.eq('PRCP')].copy()
    rain['date']=pd.to_datetime(rain.date,format='%Y%m%d').dt.strftime('%Y-%m-%d')
    rain=rain[rain.date.between(start,end)]
    rain['mm']=np.where(rain.qflag.eq('')&rain.value.ge(0),rain.value/10,np.nan)
    all_days=pd.DataFrame({'date':pd.date_range(start,end).strftime('%Y-%m-%d')})
    rain=all_days.merge(rain[['date','mm','mflag','qflag']],on='date',how='left',validate='one_to_one')
    rainrows=[[row.date,round(row.mm,1) if pd.notna(row.mm) else None,
               str(row.mflag) if pd.notna(row.mflag) else '',str(row.qflag) if pd.notna(row.qflag) else 'missing'] for row in rain.itertuples()]
    write_json('rainfall.json',rainrows)
    station=next(line for line in (CACHE/'stations.txt').read_text().splitlines() if line.startswith('USW00094728'))
    profiles['rainfall']={'station':'USW00094728','metadata':station,'total_days':len(rainrows),'usable_days':int(rain.mm.notna().sum()),'missing_or_flagged_days':int(rain.mm.isna().sum()),'units':'mm per observation day; PRCP data_value / 10','quality_rule':'exclude nonblank Q_FLAG and negative sentinel values; trace flags retained as zero with annotation'}
    profiles['category_counts']={CATEGORIES[int(k)]:int(v) for k,v in reports.category.value_counts().items()}
    profiles['date_range']=[str(start),str(end)]
    sources=[
        {'name':'NYCDEP Citywide Catch Basins','url':'https://data.cityofnewyork.us/Environment/NYCDEP-Citywide-Catch-Basins/2w2g-fk3i','role':'Uploaded inventory snapshot; 154,212 assets. Original export date not supplied.'},
        {'name':'311 Service Requests from 2020 to Present','url':'https://data.cityofnewyork.us/Social-Services/311-Service-Requests-from-2020-to-Present/erm2-nwe9','role':'Dates restored by exact service-request key. Uploaded descriptors and coordinates retained.'},
        {'name':'Borough Boundaries','url':'https://data.cityofnewyork.us/City-Government/Borough-Boundaries/gthc-hcne','role':'Full-resolution spatial join; simplified only for display.'},
        {'name':'NOAA GHCN-Daily, Central Park','url':'https://www.ncei.noaa.gov/pub/data/ghcn/daily/by_station/USW00094728.csv.gz','role':'Single-station precipitation context; not rainfall across every neighborhood.'},
        {'name':'NOAA GHCN-Daily documentation','url':'https://www.ncei.noaa.gov/pub/data/ghcn/daily/readme.txt','role':'Units, quality and trace flags.'}
    ]
    hashes={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in [args.inputs/'clean_basins.csv',args.inputs/'clean_complaints.csv']}
    manifest={'prepared_on':'2026-10-17','boroughs':BOROUGHS,'categories':CATEGORIES,'profiles':profiles,'sources':sources,'input_sha256':hashes,'hexagon_area_km2':1,'hexagon_radius_m':RADIUS,'projection':'Spherical Lambert azimuthal equal area, center 40.71 N, 73.94 W; earth radius 6371008.8 m','basin_schema':['id','longitude','latitude','borough_code','x_m','y_m','hex_q','hex_r'],'report_schema':['request_id','longitude','latitude','borough_code','x_m','y_m','hex_q','hex_r','category_index','created_day'],'rain_schema':['observation_day','precipitation_mm_or_null','measurement_flag','quality_flag']}
    write_json('manifest.json',manifest)
    pd.DataFrame([{'dataset':k,'row_count':v['rows'],'columns':len(v['columns']),'null_values':sum(v['nulls'].values()),'duplicate_ids':v['duplicate_ids'],'distinct_coordinates':v['distinct_coordinates']} for k,v in profiles.items() if isinstance(v,dict) and 'rows' in v]).to_csv(OUT/'cleaning_audit.csv',index=False)
    # Preserve the original source fields and make identifier meaning explicit.
    reports.rename(columns={'UNITID':'REQUEST_ID'}).to_csv(OUT/'enriched_complaints.csv',index=False)
    print(json.dumps(profiles,indent=2))

if __name__=='__main__':main()
