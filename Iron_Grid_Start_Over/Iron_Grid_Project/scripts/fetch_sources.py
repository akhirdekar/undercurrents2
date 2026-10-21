import urllib.request, urllib.parse, json, concurrent.futures, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CACHE=ROOT/'source_cache'; CACHE.mkdir(exist_ok=True)

def fetch(name,url):
 p=CACHE/name
 if p.exists(): return print(name,'cached',p.stat().st_size,flush=True)
 for attempt in range(3):
  try:
   with urllib.request.urlopen(url,timeout=90) as response: b=response.read()
   p.write_bytes(b);print(name,len(b),flush=True);return
  except Exception as e:
   print(name,type(e).__name__,str(e)[:100],flush=True)
   if attempt==2:raise
query={'$select':'unique_key,created_date,closed_date,status,descriptor,borough,latitude,longitude',
 '$where':"unique_key >= '45286304' AND unique_key <= '69879960' AND descriptor like '%Catch Basin%'",'$limit':'150000','$order':'unique_key'}
jobs=[
 ('311_metadata.json','https://data.cityofnewyork.us/api/views/erm2-nwe9.json'),
 ('basins_metadata.json','https://data.cityofnewyork.us/api/views/2w2g-fk3i.json'),
 ('boundaries_metadata.json','https://data.cityofnewyork.us/api/views/gthc-hcne.json'),
 ('boroughs.geojson','https://data.cityofnewyork.us/resource/gthc-hcne.geojson?$limit=5'),
 ('311_dates.json','https://data.cityofnewyork.us/resource/erm2-nwe9.json?'+urllib.parse.urlencode(query)),
 ('central_park.csv.gz','https://www.ncei.noaa.gov/pub/data/ghcn/daily/by_station/USW00094728.csv.gz'),
 ('stations.txt','https://www.ncei.noaa.gov/pub/data/ghcn/daily/ghcnd-stations.txt'),
 ('ghcn_readme.txt','https://www.ncei.noaa.gov/pub/data/ghcn/daily/readme.txt'),
 ('ghcn_csv_readme.txt','https://www.ncei.noaa.gov/pub/data/ghcn/daily/readme-by_station.txt'),
 ('d3.min.js','https://cdn.jsdelivr.net/npm/d3@7.9.0/dist/d3.min.js')]
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
 for future in [pool.submit(fetch,*job) for job in jobs]: future.result()
