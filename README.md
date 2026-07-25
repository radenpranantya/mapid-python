# mapid-python

Python teaching module for geospatial analysis with [MAPID](https://mapid.io) custom polygon data.

## Sessions

| Session | Topic                                            | Format               | Status      |
| ------- | ------------------------------------------------ | -------------------- | ----------- |
| 1       | Python for Spatial — validate & correct polygons | **Jupyter notebook** | Available   |
| 2       | Automation (pipeline + n8n)                      | Native Python        | Coming soon |

## What Session 1 teaches

- Load local polygon sample data (no API key required)
- Detect invalid geometries with Shapely (`is_valid`, `explain_validity`)
- Auto-fix fixable cases with `buffer(0)` only
- Flag overlap cases for manual review
- Compare **before vs after** with tables and maps
- Visualize on **matplotlib** and **Folium** interactive maps
- Compute area, analyze, and choropleth

## Repository layout

```
mapid-python/
├── mapid_client.py              # MAPID API client (Session 2 / optional reference)
├── scripts/
│   └── generate_mapid_polygons.py   # Generate session-1 sample data
├── requirements.txt
├── .env.example                 # Only needed for Session 2 live API
├── session-1/
│   ├── playground_mapid.ipynb   # Session 1 — primary teaching notebook
│   ├── playground_mapid.py    # Optional instructor CLI reference
│   ├── data/
│   │   └── mapid-polygons.json
│   └── output/                # Generated maps and reports
└── session-2/                   # Automation (planned)
```

## Setup

```bash
git clone git@github.com:radenpranantya/mapid-python.git
cd mapid-python

python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt notebook
```

Verify install:

```bash
python -c "import geopandas, folium, matplotlib; print('OK')"
```

## Run Session 1 (Jupyter)

No MAPID credentials needed — the notebook uses local sample data.

```bash
cd session-1
jupyter notebook playground_mapid.ipynb
```

Or open `session-1/playground_mapid.ipynb` in Cursor/VS Code and select the `.venv` Python kernel. Run cells top-to-bottom with **Shift+Enter**.

### Optional CLI reference

[`session-1/playground_mapid.py`](session-1/playground_mapid.py) is kept as an instructor reference with CLI support:

```bash
python session-1/playground_mapid.py --cached
```

## Notebook outputs

After running all cells, check `session-1/output/`:

| File                        | Description                                       |
| --------------------------- | ------------------------------------------------- |
| `comparison_report.csv`     | Per-polygon before/after validity                 |
| `before_after_map.png`      | Side-by-side matplotlib correction map            |
| `fixed_polygons_detail.png` | Zoom on each corrected polygon                    |
| `choropleth_area_ha.png`    | Area choropleth (matplotlib)                      |
| `map_final.html`            | Folium map — corrected polygons on basemap        |
| `map_before_after.html`     | Folium map — layer control (before/after/overlap) |

## Sample data

`session-1/data/mapid-polygons.json` — default **50 polygons** (regenerate anytime):

```bash
python scripts/generate_mapid_polygons.py              # 50 polygons (default)
python scripts/generate_mapid_polygons.py --count 25   # original teaching size
python scripts/generate_mapid_polygons.py --count 50 --seed 42
```

| Group                      | Count (@ 50) | Shapely behavior                   |
| -------------------------- | ------------ | ---------------------------------- |
| Valid                      | 16           | `is_valid = True`                  |
| Self-intersection / sliver | 20           | Invalid → fixable with `buffer(0)` |
| Overlap review             | 14           | Valid geometry → human review      |

Teaching mix scales proportionally from the original 25-polygon design (8 / 10 / 7).

## Dependencies

- GeoPandas, Shapely, PyProj — spatial processing
- Matplotlib — static maps
- Folium — interactive web maps
- Pandas
- Requests, PyYAML — Session 2 / optional API use

## SOLI DEO GLORIA
