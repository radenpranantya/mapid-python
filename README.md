# mapid-python

Python teaching module for geospatial analysis with [MAPID](https://mapid.io) custom polygon data.

## Sessions

| Session | Topic                                            | Format               | Status      |
| ------- | ------------------------------------------------ | -------------------- | ----------- |
| 1       | Python for Spatial — validate & correct polygons | **Jupyter notebook** | Available   |
| 2       | Automation (pipeline + n8n)                      | Native Python        | Available   |

## What Session 1 teaches

- Load local polygon sample data (no API key required)
- Detect invalid geometries with Shapely (`is_valid`, `explain_validity`)
- Auto-fix fixable cases with `buffer(0)` only
- Flag overlap cases for manual review
- Compare **before vs after** with tables and maps
- Visualize on **matplotlib** and **Folium** interactive maps
- Compute area, analyze, and choropleth

## What Session 2 teaches

- Generate 100–200 polygons for batch processing
- **Drop JSON into inbox** — file-based data input
- **Validate** polygons, **auto-fix** with `buffer(0)`, flag remaining issues
- Export **QA report** (`report.txt`, `report.json`, `summary.csv`)
- Orchestrate with **n8n** (schedule → pipeline → email report)

## Repository layout

```
mapid-python/
├── mapid_client.py              # Optional MAPID API client (Session 1 notebook)
├── scripts/
│   ├── generate_mapid_polygons.py   # Session 1 sample data
│   └── generate_batch_polygons.py   # Session 2 batch + upload GeoJSON
├── requirements.txt
├── .env.example                 # MAPID credentials for Session 2 live API
├── session-1/
│   ├── playground_mapid.ipynb   # Session 1 — primary teaching notebook
│   ├── playground_mapid.py      # Optional instructor CLI reference
│   ├── data/mapid-polygons.json
│   └── output/
└── session-2/
    ├── pipeline.py              # Inbox → validate → fix → report
    ├── pipeline_template.py     # Mentee starter template
    ├── config.example.yaml
    ├── inbox/                   # Drop GeoJSON here for processing
    ├── processed/               # Archived inbox files after run
    ├── data/
    │   └── generate_batch_polygons_*.json  # Auto-increment batch files
    ├── output/                  # summary.csv, report.txt, GPKG, run.log
    └── n8n/
        ├── mapid_polygon_pipeline.json
        └── README.md
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

## Run Session 2 (Inbox pipeline + n8n)

### Step 1 — Generate batch data

```bash
python scripts/generate_batch_polygons.py              # 150 polygons (default)
python scripts/generate_batch_polygons.py --count 200
```

Outputs:
- `session-2/data/generate_batch_polygons_N.json` — batch with valid + invalid polygons

### Step 2 — Drop file in inbox and run pipeline

```bash
cp "$(ls -t session-2/data/generate_batch_polygons_*.json | head -1)" session-2/inbox/
cd session-2
cp config.example.yaml config.yaml   # input.mode: inbox (default)
python pipeline.py --config config.yaml
```

Expected outputs in `session-2/output/`:

| File | Description |
|------|-------------|
| `summary.csv` | Per-polygon validity, fix status, area, centroids |
| `report.json` | Run statistics (invalid, fixed, still invalid) |
| `report.txt` | Human-readable report for email |
| `polygons_processed.gpkg` | Processed geometries |
| `run.log` | Pipeline audit log |

Inbox file moves to `session-2/processed/` after success.

**Cached mode:** set `input.mode: cached` and `cached_file: data/generate_batch_polygons_*.json` (uses latest batch).

**Full test checklist:** [`session-2/TEST_GUIDE.md`](session-2/TEST_GUIDE.md)

### Step 3 — n8n automation (schedule + email)

See [`session-2/n8n/README.md`](session-2/n8n/README.md):

1. Import `session-2/n8n/mapid_polygon_pipeline.json` into n8n
2. Configure Set Variables (`pipeline_dir`, `python_bin`, `report_email`)
3. Configure SMTP on **Send Email Report**
4. Drop GeoJSON in `inbox/` → **Test workflow** or activate daily 08:00 schedule

**Pattern:** n8n schedules and delivers; Python validates, fixes, and reports.

## Dependencies

- GeoPandas, Shapely, PyProj — spatial processing
- Matplotlib — static maps
- Folium — interactive web maps
- Pandas
- Requests, PyYAML — Session 2 / optional API use

## SOLI DEO GLORIA
