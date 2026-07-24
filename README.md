# mapid-python

Python teaching module for geospatial analysis with [MAPID](https://mapid.io) custom polygon data. Session 1 focuses on **validation, correction, and before/after map comparison** using Shapely and GeoPandas.

## Sessions

| Session | Topic | Status |
|---------|-------|--------|
| 1 | Python for Spatial — validate & correct polygons | Available |
| 2 | Automation (pipeline + n8n) | Coming soon |

## What Session 1 teaches

- Fetch polygon data from MAPID API (or cached sample)
- Detect invalid geometries with Shapely (`is_valid`, `explain_validity`)
- Auto-fix fixable cases with `buffer(0)` only
- Flag overlap cases for manual review
- Compare **before vs after** with tables and maps
- Compute area, analyze, and visualize on a map

## Repository layout

```
mapid-python/
├── mapid_client.py          # Shared MAPID GeoServer API client
├── requirements.txt
├── .env.example
├── session-1/
│   ├── playground_mapid.py  # Main script (# %% cells for Shift+Enter)
│   ├── data/
│   │   └── mapid-polygons.json   # 25 teaching polygons (valid + invalid + overlap)
│   └── output/              # Generated maps and reports
└── session-2/               # Automation (planned)
```

## Setup

```bash
git clone git@github.com:radenpranantya/mapid-python.git
cd mapid-python

python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Verify install:

```bash
python -c "import geopandas, requests, matplotlib; print('OK')"
```

### MAPID credentials (optional — for live API)

```bash
cp .env.example .env
# Edit .env with your MAPID_API_KEY, MAPID_PROJECT_ID, MAPID_LAYER_ID
export $(grep -v '^#' .env | xargs)
```

## Run Session 1

### Full pipeline (CLI)

```bash
# Cached sample — no API key required
python session-1/playground_mapid.py --cached

# Live MAPID API
python session-1/playground_mapid.py --live
```

### Step-by-step in Cursor / VS Code

1. Open `session-1/playground_mapid.py`
2. Select interpreter: `.venv/bin/python`
3. Place cursor in a `# %%` cell
4. Press **Shift+Enter** to run that cell in the Interactive Window

### CLI options

| Flag | Description |
|------|-------------|
| `--cached` | Use `session-1/data/mapid-polygons.json` (default) |
| `--live` | Fetch from MAPID GeoServer API |
| `--output-dir PATH` | Output folder (default: `session-1/output/`) |
| `--area-threshold N` | Filter threshold in hectares (default: `5`) |
| `--extend-folium` | Save interactive HTML map |

## Outputs

After a run, check `session-1/output/`:

| File | Description |
|------|-------------|
| `comparison_report.csv` | Per-polygon before/after validity |
| `before_after_map.png` | Side-by-side correction map |
| `fixed_polygons_detail.png` | Zoom on each corrected polygon |
| `choropleth_area_ha.png` | Final map colored by area (hectares) |
| `map_interactive.html` | Optional Folium map (`--extend-folium`) |

## Sample data

`session-1/data/mapid-polygons.json` contains **25 polygons**:

| Group | Count | Shapely behavior |
|-------|-------|------------------|
| Valid | 8 | `is_valid = True` |
| Self-intersection / sliver | 10 | Invalid → fixable with `buffer(0)` |
| Overlap review | 7 | Valid geometry → human review |

## Dependencies

- GeoPandas, Shapely, PyProj — spatial processing
- Requests — MAPID API
- Matplotlib — static maps
- Folium — optional interactive map
- Pandas, PyYAML

## SOLI DEO GLORIA
