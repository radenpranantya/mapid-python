from __future__ import annotations

import argparse
import json
import logging
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import geopandas as gpd
import yaml
from shapely.validation import explain_validity

logger = logging.getLogger(__name__)
SESSION_DIR = Path(__file__).resolve().parent
INBOX_EXTENSIONS = (".geojson", ".json")
BATCH_GLOB = "generate_batch_polygons_*.json"


def resolve_session_path(path_value: str | Path) -> Path:
    path = Path(path_value)
    if not path.is_absolute():
        path = SESSION_DIR / path
    return path.resolve()


def load_config(config_path: str) -> dict:
    with open(config_path, encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return normalize_config(config)


def normalize_config(config: dict) -> dict:
    """Support legacy api.use_cached config shape."""
    if "input" in config:
        return config

    api_cfg = config.setdefault("api", {})
    config["input"] = {
        "mode": "cached" if api_cfg.get("use_cached", True) else "inbox",
        "cached_file": api_cfg.get("cached_file", f"data/{BATCH_GLOB}"),
        "inbox_dir": "./inbox",
        "processed_dir": "./processed",
        "move_after_process": True,
    }
    return config


def setup_logging(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(output_dir / "run.log", mode="w", encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
        force=True,
    )


def load_features_from_file(path: Path) -> tuple[list, str]:
    logger.info("Loading data from %s", path)
    with path.open(encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict) and data.get("type") == "FeatureCollection":
        return data.get("features") or [], path.name
    if isinstance(data, dict) and "features" in data:
        return data["features"], path.name
    if isinstance(data, list):
        return data, path.name

    raise ValueError(f"Unsupported JSON shape in {path}")


def find_latest_file(directory: Path, *, glob_pattern: str) -> Path | None:
    if not directory.is_dir():
        return None
    candidates = sorted(directory.glob(glob_pattern), key=lambda path: path.stat().st_mtime)
    return candidates[-1] if candidates else None


def find_latest_inbox_file(inbox_dir: Path) -> Path | None:
    if not inbox_dir.is_dir():
        return None
    candidates = [
        path
        for path in inbox_dir.iterdir()
        if path.is_file() and path.suffix.lower() in INBOX_EXTENSIONS
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime)


def resolve_cached_file(cached_file: str | Path) -> Path:
    path = resolve_session_path(cached_file)
    if path.exists():
        return path

    if "*" in path.name:
        latest = find_latest_file(path.parent, glob_pattern=path.name)
        if latest is not None:
            logger.info("Using latest cached batch: %s", latest.name)
            return latest

    raise FileNotFoundError(f"Cached input file not found: {path}")


def load_input_features(input_cfg: dict) -> tuple[list, str, Path | None]:
    mode = input_cfg.get("mode", "inbox")
    source_path: Path | None = None

    if mode == "inbox":
        inbox_dir = resolve_session_path(input_cfg.get("inbox_dir", "./inbox"))
        source_path = find_latest_inbox_file(inbox_dir)
        if source_path is None:
            raise FileNotFoundError(
                f"No GeoJSON/JSON files found in inbox: {inbox_dir}. "
                "Drop a batch file there or set input.mode to cached."
            )
        features, source_name = load_features_from_file(source_path)

    elif mode == "cached":
        cached_file = resolve_cached_file(
            input_cfg.get("cached_file", f"data/{BATCH_GLOB}")
        )
        features, source_name = load_features_from_file(cached_file)
        source_path = cached_file

    else:
        raise ValueError(f"Unknown input.mode: {mode!r} (use inbox or cached)")

    if not features:
        raise ValueError(f"No features found in input source: {source_name}")

    return features, source_name, source_path


def archive_inbox_file(source_path: Path, processed_dir: Path) -> Path:
    processed_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    destination = processed_dir / f"{stamp}_{source_path.name}"
    shutil.move(str(source_path), str(destination))
    logger.info("Moved processed inbox file to %s", destination)
    return destination


def features_to_gdf(features: list, crs: str = "EPSG:4326") -> gpd.GeoDataFrame:
    gdf = gpd.GeoDataFrame.from_features(features, crs=crs)
    logger.info("Created GeoDataFrame with %d rows", len(gdf))
    return gdf


def process_gdf(gdf: gpd.GeoDataFrame, target_crs: str) -> gpd.GeoDataFrame:
    gdf = gdf[gdf.geometry.notna()].copy()
    logger.info("Rows after dropping null geometry: %d", len(gdf))

    gdf["was_invalid"] = ~gdf.geometry.is_valid
    gdf["issue"] = gdf.geometry.apply(
        lambda geom: "" if geom.is_valid else explain_validity(geom)
    )

    invalid_before = int(gdf["was_invalid"].sum())
    if invalid_before:
        logger.warning("Fixing %d invalid geometries with buffer(0)", invalid_before)
        gdf.loc[gdf["was_invalid"], "geometry"] = gdf.loc[gdf["was_invalid"], "geometry"].buffer(0)

    gdf["geometry_valid"] = gdf.geometry.is_valid
    gdf["fixed_by_pipeline"] = gdf["was_invalid"] & gdf["geometry_valid"]

    gdf_proj = gdf.to_crs(target_crs)
    gdf["area_ha"] = gdf_proj.geometry.area / 10_000

    centroids = gdf_proj.geometry.centroid.to_crs(4326)
    gdf["centroid_lat"] = centroids.y
    gdf["centroid_lon"] = centroids.x

    logger.info(
        "Processed: area_ha min=%.2f max=%.2f mean=%.2f",
        gdf["area_ha"].min(),
        gdf["area_ha"].max(),
        gdf["area_ha"].mean(),
    )
    return gdf


def build_report(gdf: gpd.GeoDataFrame, source_name: str, input_mode: str) -> dict:
    total = len(gdf)
    invalid_before = int(gdf["was_invalid"].sum())
    fixed = int(gdf["fixed_by_pipeline"].sum())
    still_invalid = int((~gdf["geometry_valid"]).sum())
    valid_final = total - still_invalid

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input_mode": input_mode,
        "source": source_name,
        "total_polygons": total,
        "invalid_before_fix": invalid_before,
        "fixed_by_pipeline": fixed,
        "still_invalid": still_invalid,
        "valid_final": valid_final,
        "area_ha": {
            "min": round(float(gdf["area_ha"].min()), 4),
            "max": round(float(gdf["area_ha"].max()), 4),
            "mean": round(float(gdf["area_ha"].mean()), 4),
        },
    }


def format_report_text(report: dict) -> str:
    return (
        "Polygon QA Report\n"
        "=================\n"
        f"Generated : {report['generated_at']}\n"
        f"Source    : {report['source']} ({report['input_mode']} mode)\n"
        f"Total     : {report['total_polygons']}\n"
        f"Invalid (before fix) : {report['invalid_before_fix']}\n"
        f"Auto-fixed           : {report['fixed_by_pipeline']}\n"
        f"Still invalid        : {report['still_invalid']}\n"
        f"Valid (final)        : {report['valid_final']}\n"
        f"Area (ha) min/mean/max : "
        f"{report['area_ha']['min']} / {report['area_ha']['mean']} / {report['area_ha']['max']}\n"
    )


def export_outputs(gdf: gpd.GeoDataFrame, output_dir: Path, report: dict) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    summary_cols = [
        "id",
        "name",
        "was_invalid",
        "fixed_by_pipeline",
        "geometry_valid",
        "issue",
        "area_ha",
        "centroid_lat",
        "centroid_lon",
    ]
    available = [c for c in summary_cols if c in gdf.columns]
    summary_path = output_dir / "summary.csv"
    gdf[available].to_csv(summary_path, index=False)
    logger.info("Wrote %s (%d rows)", summary_path, len(gdf))

    gpkg_path = output_dir / "polygons_processed.gpkg"
    gdf.to_file(gpkg_path, driver="GPKG")
    logger.info("Wrote %s", gpkg_path)

    report_json = output_dir / "report.json"
    report_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    logger.info("Wrote %s", report_json)

    report_txt = output_dir / "report.txt"
    report_txt.write_text(format_report_text(report), encoding="utf-8")
    logger.info("Wrote %s", report_txt)


def run_pipeline(config: dict) -> gpd.GeoDataFrame:
    input_cfg = config["input"]
    output_cfg = config["output"]
    output_dir = resolve_session_path(output_cfg["dir"])
    target_crs = output_cfg["target_crs"]
    input_mode = input_cfg.get("mode", "inbox")

    setup_logging(output_dir)

    features, source_name, source_path = load_input_features(input_cfg)
    gdf = features_to_gdf(features)
    gdf = process_gdf(gdf, target_crs)

    report = build_report(gdf, source_name, input_mode)
    export_outputs(gdf, output_dir, report)

    if (
        input_mode == "inbox"
        and source_path is not None
        and input_cfg.get("move_after_process", True)
    ):
        processed_dir = resolve_session_path(input_cfg.get("processed_dir", "./processed"))
        archive_inbox_file(source_path, processed_dir)

    logger.info(
        "Pipeline complete. %d polygons | %d fixed | %d still invalid",
        report["total_polygons"],
        report["fixed_by_pipeline"],
        report["still_invalid"],
    )
    return gdf


def main() -> None:
    parser = argparse.ArgumentParser(description="Session 2 polygon QA pipeline")
    parser.add_argument("--config", required=True, help="Path to config.yaml")
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.is_absolute():
        if config_path.is_file():
            config_path = config_path.resolve()
        else:
            config_path = (SESSION_DIR / config_path).resolve()

    run_pipeline(load_config(str(config_path)))


if __name__ == "__main__":
    main()
