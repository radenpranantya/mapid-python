
from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATA_DIR = ROOT / "session-2" / "data"
OUTPUT_PREFIX = "generate_batch_polygons"
# DEFAULT_GEOJSON = ROOT / "session-2" / "data" / "upload_batch.geojson"

CATEGORIES = ["commercial", "residential", "industrial", "mixed", "green"]
LON_MIN, LON_MAX = 106.75, 107.05
LAT_MIN, LAT_MAX = -6.35, -6.05


def next_output_path(data_dir: Path = DEFAULT_DATA_DIR) -> Path:
    data_dir.mkdir(parents=True, exist_ok=True)
    next_n = 1
    for path in data_dir.glob(f"{OUTPUT_PREFIX}_*.json"):
        suffix = path.stem.removeprefix(f"{OUTPUT_PREFIX}_")
        if suffix.isdigit():
            next_n = max(next_n, int(suffix) + 1)
    return data_dir / f"{OUTPUT_PREFIX}_{next_n}.json"


def _square_ring(lon: float, lat: float, half: float) -> list:
    return [
        [lon - half, lat - half],
        [lon + half, lat - half],
        [lon + half, lat + half],
        [lon - half, lat + half],
        [lon - half, lat - half],
    ]


def _bowtie_ring(lon: float, lat: float, half: float) -> list:
    return [
        [lon - half, lat - half],
        [lon + half, lat + half],
        [lon + half, lat - half],
        [lon - half, lat + half],
        [lon - half, lat - half],
    ]


def _grid_centers(count: int, rng: random.Random) -> list[tuple[float, float]]:
    cols = math.ceil(math.sqrt(count))
    rows = math.ceil(count / cols)
    lon_step = (LON_MAX - LON_MIN) / (cols + 1)
    lat_step = (LAT_MAX - LAT_MIN) / (rows + 1)
    centers: list[tuple[float, float]] = []
    for row in range(rows):
        for col in range(cols):
            if len(centers) >= count:
                return centers
            lon = LON_MIN + lon_step * (col + 1) + rng.uniform(-lon_step * 0.08, lon_step * 0.08)
            lat = LAT_MIN + lat_step * (row + 1) + rng.uniform(-lat_step * 0.08, lat_step * 0.08)
            centers.append((lon, lat))
    return centers[:count]


def make_feature(idx: int, coords: list, category: str, *, invalid: bool = False) -> dict:
    feature_id = f"poly-{idx:03d}"
    return {
        "type": "Feature",
        "id": feature_id,
        "geometry": {"type": "Polygon", "coordinates": [coords]},
        "properties": {
            "id": feature_id,
            "name": f"Zone {idx:03d}",
            "category": category,
            "qa_flag": "self_intersection" if invalid else "none",
            "fixable": invalid,
            "fix_method": "buffer_0" if invalid else "none",
            "invalid_severity": "severe" if invalid else None,
            "expected_mapid_upload": not invalid,
        },
    }


def build_batch_collection(count: int, invalid_count: int, seed: int) -> dict:
    rng = random.Random(seed)
    invalid_count = min(invalid_count, count)
    invalid_indices = set(rng.sample(range(count), invalid_count))
    centers = _grid_centers(count, rng)

    features: list[dict] = []
    for i in range(count):
        lon, lat = centers[i]
        size = rng.uniform(0.002, 0.006)
        invalid = i in invalid_indices
        coords = _bowtie_ring(lon, lat, size / 2) if invalid else _square_ring(lon, lat, size / 2)
        features.append(make_feature(i + 1, coords, rng.choice(CATEGORIES), invalid=invalid))

    return {
        "type": "FeatureCollection",
        "total": count,
        "features": features,
        "metadata": {
            "description": f"Session 2 batch: {count - invalid_count} valid + {invalid_count} fixable invalid",
            "valid_count": count - invalid_count,
            "invalid_count": invalid_count,
            "seed": seed,
        },
    }


def build_upload_geojson(batch: dict) -> dict:
    """Valid-only geometries for manual MAPID UI upload (buffer(0) on fixable in pipeline)."""
    from shapely.geometry import mapping, shape

    upload_features = []
    for feature in batch["features"]:
        geom = shape(feature["geometry"])
        props = dict(feature["properties"])
        if props.get("fixable"):
            geom = geom.buffer(0)
            props["qa_flag"] = "none"
            props["fixable"] = False
        upload_features.append(
            {
                "type": "Feature",
                "id": feature["id"],
                "geometry": mapping(geom),
                "properties": props,
            }
        )

    return {
        "type": "FeatureCollection",
        "total": len(upload_features),
        "features": upload_features,
        "metadata": {
            "description": "Upload to MAPID web UI — all geometries valid",
            "source": "generate_batch_polygons.py",
        },
    }


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"Wrote {path} ({data['total']} features)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Session 2 batch polygon data")
    parser.add_argument("--count", type=int, default=150, help="Total polygons (default: 150)")
    parser.add_argument("--invalid", type=int, default=5, help="Invalid/fixable count (default: 5)")
    parser.add_argument("--seed", type=int, default=123, help="Random seed")
    parser.add_argument(
        "--json-output",
        type=Path,
        default=None,
        help="Output path (default: session-2/data/generate_batch_polygons_N.json, auto-increment)",
    )
    # parser.add_argument("--geojson-output", type=Path, default=DEFAULT_GEOJSON)
    args = parser.parse_args()

    json_output = args.json_output or next_output_path()
    batch = build_batch_collection(args.count, args.invalid, args.seed)
    write_json(json_output, batch)

    # try:
    #     upload = build_upload_geojson(batch)
    #     write_json(args.geojson_output, upload)
    # except ImportError:
    #     print("Skipped upload_batch.geojson (install shapely)")

    meta = batch["metadata"]
    print(f"  Valid: {meta['valid_count']}  Invalid (fixable): {meta['invalid_count']}")


if __name__ == "__main__":
    main()
