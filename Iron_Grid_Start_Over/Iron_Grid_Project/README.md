# The Iron Grid: NYC Stormwater Explorer

A D3.js interactive prototype by Abhijeet Khirdekar, Cooper Union. Midterm Part 2, theme **Undercurrents**. Extended deadline supplied by the student: October 28, 2026.

## Start here

The working static website is in `dist/`. It needs no build, API key, npm installation or map subscription. D3 7.9.0 is bundled locally. The app uses real data, not synthetic samples.

- Local viewing: open a terminal in `dist/`, run `python -m http.server 8000`, then visit `http://localhost:8000`.
- GitHub Pages: upload the **contents of `dist/`** to the root of a public repository. Settings > Pages > Deploy from a branch > main > /(root) > Save. Keep `index.html`, `app.mjs`, `logic.mjs`, `styles.css`, `vendor/` and `data/` together.
- Do not double-click `index.html`: browsers may block local JSON requests on `file://`.

The existing ChatGPT Sites preview is a convenient demo. The assignment explicitly names GitHub Pages or Observable; publish the provided static files to GitHub Pages for that hosting requirement.

## Research question

Where do mapped catch basins and reported catch basin problems overlap, and how do report patterns change around wet periods? The primary audience is civil engineers and environmental planners preparing questions for field investigation. The tool is accessible to residents and community boards, too.

## Interactions

1. Optional three-screen onboarding guide.
2. Borough and report-type filters linked to map, counts, rankings and comparisons.
3. D3 pan/zoom and a switch between 1 km² equal-area hexagons and individual records.
4. Basin counts, report counts, and reports per 100 mapped basins; all denominators are explicit.
5. D3 time brushing with keyboard-accessible date inputs; the timeline retains the full context.
6. Wet-day shortcuts from real Central Park observations, showing two days before and four after.
7. Cell inspection, asset/request record inspection, two pinned cells with shared filters.
8. Keyboard-operable ranked cell list and filtered summary CSV export.

## Data

Supplied inputs are preserved in `source_data/`:

| File | Rows | Retained source fields | Duplicate IDs | Null cells |
|---|---:|---:|---:|---:|
| clean_basins.csv | 154,212 | 3 | 0 | 0 |
| clean_complaints.csv | 58,965 | 4 | 0 | 0 |

The original slideshow described a six-column basin export. The supplied cleaned version has three columns. Basin records have 154,196 distinct coordinate pairs; separate asset IDs sharing coordinates remain in the inventory. Reports have 36,992 distinct coordinate pairs; repeated locations are not deduplicated because service requests are distinct records.

All 58,965 request dates were restored from NYC's 311 dataset by exact service-request key; coverage is 2020-01-01 through 2026-07-28. A query for candidate source records returned 65,104 records within the uploaded ID range; the visualization intentionally retains only the 58,965 supplied report IDs. The supplied cleaning history and original export timestamp were not provided. Treat the uploaded file as a provided subset, not a proven census of all requests.

**The UNITID columns do not share an identifier system.** Basin UNITID identifies a mapped asset; complaint UNITID identifies a 311 request and is renamed REQUEST_ID in the enriched export. Do not merge those columns together.

Sources:

- [NYCDEP Citywide Catch Basins](https://data.cityofnewyork.us/Environment/NYCDEP-Citywide-Catch-Basins/2w2g-fk3i)
- [311 Service Requests from 2020 to Present](https://data.cityofnewyork.us/Social-Services/311-Service-Requests-from-2020-to-Present/erm2-nwe9)
- [Borough Boundaries](https://data.cityofnewyork.us/City-Government/Borough-Boundaries/gthc-hcne)
- [NOAA GHCN-Daily, Central Park USW00094728](https://www.ncei.noaa.gov/pub/data/ghcn/daily/by_station/USW00094728.csv.gz)
- [NOAA GHCN-Daily units and flags](https://www.ncei.noaa.gov/pub/data/ghcn/daily/readme.txt)
- [NOAA station CSV layout](https://www.ncei.noaa.gov/pub/data/ghcn/daily/readme-by_station.txt)

`dist/data/manifest.json` includes schemas, source links, input SHA-256 hashes, projection, row counts, quality rules and limitations. It is downloadable from About > How the data was prepared.

## Reproduce the preparation

Python 3 with pandas, NumPy and Matplotlib is needed **only for reprocessing**, not viewing or deploying. Install those packages in your own environment if needed:

```sh
python -m pip install pandas numpy matplotlib
python scripts/fetch_sources.py
python scripts/prepare_data.py --inputs source_data
```

The downloader caches files in `source_cache/` (ignored by Git). It fetches public data. Remove only a chosen cached source file if you intentionally want to refresh it. Source systems can change, so a fresh run may produce different metadata. Preparation retains the uploaded ID cohort and source descriptors. Inspect unmatched dates before using a new output. After preparation, copy `source_cache/d3.min.js` to `dist/vendor/d3.min.js` if needed; the delivered bundle already contains this file.

Processing steps: profile IDs/nulls/coordinate ranges; restore request dates by unique_key; classify the five supplied descriptors; assign boroughs using full polygons; project points to a spherical Lambert azimuthal equal-area system centered on NYC; assign regular 1 km² hexagons; simplify boundaries for drawing only; parse NOAA PRCP, convert tenths of mm to mm, preserve quality/trace handling; write the manifest and enriched export.

29 basins and 8 reports are not inside a borough polygon. They remain in the citywide view and are excluded from individual borough filters. Basin inventory is fixed while report dates change. The ratio is a spatial count ratio, not an asset failure rate. Edge cells are not normalized by land area, population or road length.

## Validation

If Node.js is available, run:

```sh
node --check dist/app.mjs
node scripts/validate.mjs
```

Checks passed on the delivered snapshot: conservation of counts, type/borough/date filters, shared ID interpretation, fixed inventory denominators, missing-denominator handling, daily totals, hexagon area and membership, nonnegative precipitation, required assets and HTML element references. One-day filtering for 2021-09-02 yields 309 supplied requests.

The interface was checked in a managed desktop browser. Borough and date filters, the rainfall drawer, table-to-map selection, comparison, reset and the map layout were verified. A separate mobile device test was not performed.

## Interpretation and ethics

No hydraulic capacity, terrain height, inlet condition or maintenance outcome is inferred. Reports may be repeated or delayed; reporting access and public awareness affect the record. No complainant identity, address or contact information is included. Exact public infrastructure coordinates remain visible.

Central Park daily precipitation is historical context, not a citywide rainfall surface or hourly intensity measurement. Observation-day conventions can differ from 311 calendar days. Precipitation includes liquid equivalents of frozen precipitation. Quality-flagged and missing values are unavailable, not zero. Trace observations are marked.

The earlier proposal's suggestions about old streams, modern neighborhoods and equity are **hypotheses to investigate**, not findings established by these datasets. Do not present drain density as drainage adequacy or report totals as neighborhood neglect.

## Feasible next additions

Start with [NYC Stormwater Flood Maps](https://data.cityofnewyork.us/Environment/NYC-Stormwater-Flood-Maps/9i7c-xyvv), preserving the scenario labels, modeled rainfall and sea-level assumptions. It is a more informative next spatial layer than assigning arbitrary elevations to points. A terrain layer needs a documented DEM resolution, date, projection and vertical datum. Multiple rain gauges or a documented radar product would improve geographic rainfall context.

## Attribution

D3.js is distributed under the ISC license. See `dist/vendor/D3-LICENSE.txt`. The locally bundled Barlow Condensed Black title font is distributed under the SIL Open Font License; see `dist/vendor/Barlow-OFL.txt`. NYC and NOAA data attribution is provided above. This student project is not endorsed by either agency.

## October 21 map interface update

The map fills the viewport with a deep navy background, bright cyan basin points, orange report colors, simple sans-serif labels and a Barlow Condensed wordmark. The initial view shows individual catch basins. Borough and measure selectors sit at the top; extra layer controls stay in one menu. Rainfall and date filtering open in a bottom drawer. Area details appear on selection. The report breakdown, area table, onboarding guide, methods, limitations and sources are available in About. All data and calculations are retained.

Browser checks performed on the revised interface: citywide totals; Queens filter (66,387 basins and 23,910 reports); single-day filter for September 2, 2021 (309 reports, fixed inventory); all three help steps; area-table selection; and adding an area for comparison. The desktop layout was reviewed in the supported preview. Mobile layout rules were inspected in code; a separate mobile device test was not performed.
