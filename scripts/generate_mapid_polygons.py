from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = ROOT / "session-1" / "data" / "mapid-polygons.json"

CATEGORIES = ["commercial", "residential", "industrial", "mixed", "green"]

LON_MIN, LON_MAX = 106.75, 107.05
LAT_MIN, LAT_MAX = -6.35, -6.05

# Teaching mix ratios (from original 25-polygon Session 1 design)
RATIO_VALID = 8 / 25
RATIO_FIXABLE = 10 / 25
RATIO_OVERLAP = 7 / 25
RATIO_SEVERE = 6 / 10  # share of fixable that are severe invalid
RATIO_MILD = 4 / 10


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


def _kink_ring(lon: float, lat: float, half: float) -> list:
    return [
        [lon - half, lat - half],
        [lon, lat + half],
        [lon + half, lat - half],
        [lon - half, lat],
        [lon + half, lat + half],
        [lon - half, lat - half],
    ]


def _duplicate_vertex_ring(lon: float, lat: float, half: float) -> list:
    ring = _square_ring(lon, lat, half)
    ring.insert(2, ring[2][:])
    return ring


def _spike_ring(lon: float, lat: float, half: float) -> list:
    return [
        [lon - half, lat - half],
        [lon + half, lat - half],
        [lon + half, lat + half],
        [lon - half, lat + half],
        [lon, lat + half * 3],
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
            lon = LON_MIN + lon_step * (col + 1) + rng.uniform(-lon_step * 0.1, lon_step * 0.1)
            lat = LAT_MIN + lat_step * (row + 1) + rng.uniform(-lat_step * 0.1, lat_step * 0.1)
            centers.append((lon, lat))
    return centers[:count]


def _split_counts(total: int) -> tuple[int, int, int]:
    valid = max(1, round(total * RATIO_VALID))
    fixable = max(1, round(total * RATIO_FIXABLE))
    overlap = total - valid - fixable
    if overlap < 1:
        overlap = 1
        if fixable > 1:
            fixable -= 1
        elif valid > 1:
            valid -= 1
    return valid, fixable, overlap


def _feature(
    idx: int,
    coords: list,
    category: str,
    *,
    qa_flag: str = "none",
    fixable: bool = False,
    fix_method: str = "none",
    invalid_severity: str | None = None,
    expected_mapid_upload: bool = True,
    overlap_with: list[str] | None = None,
    overlap_pct: float | None = None,
    instructor_note: str = "",
) -> dict:
    feature_id = f"poly-{idx:03d}"
    return {
        "type": "Feature",
        "id": feature_id,
        "geometry": {"type": "Polygon", "coordinates": [coords]},
        "properties": {
            "id": feature_id,
            "name": f"Zone {idx:02d}",
            "category": category,
            "qa_flag": qa_flag,
            "fixable": fixable,
            "fix_method": fix_method,
            "invalid_severity": invalid_severity,
            "expected_mapid_upload": expected_mapid_upload,
            "overlap_with": overlap_with,
            "overlap_pct": overlap_pct,
            "instructor_note": instructor_note,
        },
    }


def _severe_ring(lon: float, lat: float, variant: int, half: float = 0.005) -> tuple[str, list, str]:
    variants = [
        ("self_intersection", _bowtie_ring(lon, lat, half), "Severe bowtie — fix with buffer(0)"),
        ("self_intersection", _kink_ring(lon, lat, half), "Severe kink — fix with buffer(0)"),
        ("sliver", _spike_ring(lon, lat, half * 0.8), "Severe spike — fix with buffer(0)"),
    ]
    return variants[variant % len(variants)]


def _mild_ring(lon: float, lat: float, variant: int, half: float = 0.004) -> tuple[str, list, str]:
    variants = [
        ("sliver", _duplicate_vertex_ring(lon, lat, half), "Mild duplicate vertex — fix with buffer(0)"),
        ("self_intersection", _bowtie_ring(lon, lat, half * 0.4), "Mild small bowtie — fix with buffer(0)"),
    ]
    return variants[variant % len(variants)]


def build_collection(count: int = 50, seed: int = 42) -> dict:
    if count < 10:
        raise ValueError("count must be at least 10 to preserve teaching mix")

    rng = random.Random(seed)
    valid_n, fixable_n, overlap_n = _split_counts(count)
    severe_n = max(1, round(fixable_n * RATIO_SEVERE))
    mild_n = fixable_n - severe_n

    centers = _grid_centers(valid_n + fixable_n + overlap_n + 5, rng)
    center_iter = iter(centers)

    features: list[dict] = []
    idx = 1

    for _ in range(valid_n):
        lon, lat = next(center_iter)
        features.append(
            _feature(
                idx,
                _square_ring(lon, lat, 0.004),
                rng.choice(CATEGORIES),
                qa_flag="none",
                fixable=False,
                invalid_severity=None,
                expected_mapid_upload=True,
                instructor_note="Valid geometry — no correction needed",
            )
        )
        idx += 1

    for i in range(severe_n):
        lon, lat = next(center_iter)
        qa_flag, ring, note = _severe_ring(lon, lat, i)
        features.append(
            _feature(
                idx,
                ring,
                rng.choice(CATEGORIES),
                qa_flag=qa_flag,
                fixable=True,
                fix_method="buffer_0",
                invalid_severity="severe",
                expected_mapid_upload=False,
                instructor_note=note,
            )
        )
        idx += 1

    for i in range(mild_n):
        lon, lat = next(center_iter)
        qa_flag, ring, note = _mild_ring(lon, lat, i)
        features.append(
            _feature(
                idx,
                ring,
                rng.choice(CATEGORIES),
                qa_flag=qa_flag,
                fixable=True,
                fix_method="buffer_0",
                invalid_severity="mild",
                expected_mapid_upload=True,
                instructor_note=note,
            )
        )
        idx += 1

    major_clusters = overlap_n // 3
    minor_pairs = (overlap_n - major_clusters * 3) // 2

    for cluster in range(major_clusters):
        lon, lat = next(center_iter)
        ids = [f"poly-{idx + j:03d}" for j in range(3)]
        halves = [0.008, 0.006, 0.004]
        cats = ["industrial", "mixed", "green"]
        for j, (half, cat) in enumerate(zip(halves, cats)):
            others = [x for k, x in enumerate(ids) if k != j]
            features.append(
                _feature(
                    idx,
                    _square_ring(lon, lat, half),
                    cat,
                    qa_flag="major_overlap",
                    fixable=False,
                    fix_method="manual_review",
                    invalid_severity=None,
                    expected_mapid_upload=True,
                    overlap_with=others,
                    overlap_pct=50.0,
                    instructor_note="Major overlap — manual review required",
                )
            )
            idx += 1

    for pair in range(minor_pairs):
        lon, lat = next(center_iter)
        half = 0.005
        id_a, id_b = f"poly-{idx:03d}", f"poly-{idx + 1:03d}"
        pct = 12.0 + (pair % 3) * 5
        features.append(
            _feature(
                idx,
                _square_ring(lon, lat, half),
                rng.choice(CATEGORIES),
                qa_flag="minor_overlap",
                fixable=False,
                fix_method="manual_review",
                invalid_severity=None,
                expected_mapid_upload=True,
                overlap_with=[id_b],
                overlap_pct=pct,
                instructor_note="Minor overlap — valid geometry, needs human decision",
            )
        )
        idx += 1
        features.append(
            _feature(
                idx,
                _square_ring(lon + 0.0088, lat, half),
                rng.choice(CATEGORIES),
                qa_flag="minor_overlap",
                fixable=False,
                fix_method="manual_review",
                invalid_severity=None,
                expected_mapid_upload=True,
                overlap_with=[id_a],
                overlap_pct=pct,
                instructor_note="Minor overlap — valid geometry, needs human decision",
            )
        )
        idx += 1

    assert len(features) == count, f"Expected {count} features, got {len(features)}"

    props = [f["properties"] for f in features]
    return {
        "type": "FeatureCollection",
        "total": count,
        "features": features,
        "metadata": {
            "description": f"Session 1 teaching sample: {valid_n} valid + {fixable_n} fixable + {overlap_n} overlap",
            "valid_count": sum(1 for p in props if p["qa_flag"] == "none"),
            "fixable_count": sum(1 for p in props if p["fixable"]),
            "severe_invalid_count": sum(1 for p in props if p.get("invalid_severity") == "severe"),
            "mild_invalid_count": sum(1 for p in props if p.get("invalid_severity") == "mild"),
            "overlap_review_count": sum(1 for p in props if "overlap" in p["qa_flag"]),
            "expected_mapid_upload_raw": sum(1 for p in props if p.get("expected_mapid_upload")),
            "seed": seed,
        },
    }


def print_summary(data: dict) -> None:
    meta = data["metadata"]
    print(f"  Total: {data['total']}")
    print(f"  Valid (qa_flag=none): {meta['valid_count']}")
    print(
        f"  Fixable: {meta['fixable_count']} "
        f"(severe={meta['severe_invalid_count']}, mild={meta['mild_invalid_count']})"
    )
    print(f"  Overlap review: {meta['overlap_review_count']}")
    print(f"  Expected raw upload: {meta['expected_mapid_upload_raw']}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Session 1 mapid-polygons.json")
    parser.add_argument("--count", type=int, default=50, help="Total polygons (default: 50)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Output JSON path",
    )
    args = parser.parse_args()

    data = build_collection(count=args.count, seed=args.seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    print(f"Wrote {args.output} ({data['total']} features)")
    print_summary(data)


if __name__ == "__main__":
    main()
