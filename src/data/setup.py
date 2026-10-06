"""Download, verify, extract, and cache the FI-2010 source files."""

from __future__ import annotations

import hashlib
import json
import shutil
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

import numpy as np

from src.config import DEFAULT_CONFIG, load
from src.data.loader import (
    find_stock_boundaries,
    load_fi2010_file,
    period_log_returns,
    reconstruct_lob,
    segment_boundaries,
    sigma_min_floor,
)

DEFAULT_MANIFEST = Path(__file__).resolve().parents[2] / "data" / "manifest.json"
DEFAULT_ROOT = Path("data/raw/FI-2010")
DEFAULT_CACHE = Path("data/processed")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_manifest(path: Path = DEFAULT_MANIFEST) -> dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        manifest = json.load(stream)
    if not isinstance(manifest, dict) or not isinstance(manifest.get("files"), list):
        raise ValueError(f"invalid dataset manifest: {path}")
    return manifest


def verify_files(root: Path, manifest: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for entry in manifest["files"]:
        name = entry["name"]
        path = root / name
        if not path.is_file():
            errors.append(f"missing {name}")
            continue
        expected_size = entry.get("size")
        if expected_size is not None and path.stat().st_size != expected_size:
            errors.append(f"{name}: size {path.stat().st_size} != {expected_size}")
        expected_hash = entry.get("sha256")
        if expected_hash and sha256_file(path) != expected_hash:
            errors.append(f"{name}: SHA-256 mismatch")
    return errors


def _download(url: str, destination: Path, retries: int = 3) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(retries):
        try:
            existing = destination.stat().st_size if destination.exists() else 0
            request = urllib.request.Request(url)
            if existing:
                request.add_header("Range", f"bytes={existing}-")
            with urllib.request.urlopen(request, timeout=60) as response:
                mode = "ab" if existing and response.status == 206 else "wb"
                with destination.open(mode) as stream:
                    shutil.copyfileobj(response, stream, length=1024 * 1024)
            return
        except (OSError, urllib.error.URLError):
            if attempt == retries - 1:
                raise
            time.sleep(2**attempt)


def extract_archive(archive: Path, root: Path, names: set[str], force: bool = False) -> None:
    root.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as source:
        available = {Path(info.filename).name: info for info in source.infolist()}
        missing = sorted(names - available.keys())
        if missing:
            raise ValueError(f"archive does not contain required files: {', '.join(missing)}")
        for name in names:
            target = root / name
            if target.exists() and not force:
                continue
            with source.open(available[name]) as input_stream, target.open("wb") as output_stream:
                shutil.copyfileobj(input_stream, output_stream)


def build_cache(
    root: Path,
    cache_root: Path = DEFAULT_CACHE,
    *,
    scale_exponent: int = 6,
    rows_per_period: int = 20,
    force: bool = False,
) -> list[Path]:
    cache_root.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []
    for source in sorted(root.glob("*.txt")):
        destination = cache_root / f"{source.stem}.npz"
        if (
            destination.exists()
            and not force
            and destination.stat().st_mtime >= source.stat().st_mtime
        ):
            outputs.append(destination)
            continue
        X, _ = load_fi2010_file(source)
        lob = reconstruct_lob(X, k_decpre=scale_exponent)
        boundaries = segment_boundaries(find_stock_boundaries(lob["M"]), len(lob["M"]))
        returns = period_log_returns(lob["M"], rows_per_period)
        metadata = {
            "source": str(source),
            "boundaries": boundaries,
            "rows_per_period": rows_per_period,
            "sigma_min_floor": sigma_min_floor(returns),
            "n_samples": len(lob["M"]),
        }
        np.savez_compressed(destination, **lob)
        destination.with_suffix(".json").write_text(
            json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
        )
        outputs.append(destination)
    return outputs


def setup_dataset(
    *,
    archive: Path | None = None,
    url: str | None = None,
    root: Path = DEFAULT_ROOT,
    manifest_path: Path = DEFAULT_MANIFEST,
    cache_root: Path = DEFAULT_CACHE,
    verify_only: bool = False,
    force: bool = False,
) -> list[str]:
    manifest = read_manifest(manifest_path)
    names = {entry["name"] for entry in manifest["files"]}
    if archive is None and not verify_only:
        existing_files = all((root / name).is_file() for name in names)
        if existing_files:
            pass
        elif not url:
            raise ValueError("no complete dataset in the target directory; provide --zip or --url")
        else:
            archive = root.parent / "fi2010.zip"
            _download(url, archive)
    if archive is not None and not verify_only:
        extract_archive(archive, root, names, force=force)
    errors = verify_files(root, manifest)
    if errors:
        return errors
    if not verify_only:
        cfg = load(DEFAULT_CONFIG)
        dataset = cfg["dataset"]
        build_cache(
            root,
            cache_root,
            scale_exponent=int(dataset.get("scale_exponent", 6)),
            rows_per_period=int(cfg["period"]["rows_per_period"]),
            force=force,
        )
    return []
