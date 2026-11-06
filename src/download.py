"""
Phase 1 -- Reproducible download of raw TLC files.

What it does
  * Downloads each requested month of yellow-taxi trip data plus the taxi
    zone lookup CSV into data/raw/.
  * Never overwrites an existing file unless --force is passed (raw data
    is treated as immutable).
  * Writes data/raw/manifest.json recording, for every file: source URL,
    local path, size in bytes, SHA-256 checksum, and UTC download time.

Why the manifest matters
  Anyone (an interviewer, a teammate, future you) can see exactly which
  files the analysis was built from, and the checksum proves a file was not
  altered or partially downloaded. If TLC republishes a month, the checksum
  changes and you will notice.

Usage (run from the project root):
  python -m src.download                    # sample (2024-01 only)
  python -m src.download --full             # 2024-01 .. 2024-06
  python -m src.download --months 2024-01 2024-02
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

from src import config

MONTH_PATTERN = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
CHUNK = 1024 * 1024  # 1 MB


def sha256_of(path: Path) -> str:
    """Hash a file in chunks so large files never load fully into memory."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(CHUNK), b""):
            h.update(block)
    return h.hexdigest()


def validate_months(months: list[str]) -> list[str]:
    """Reject badly formatted months early, return them sorted and de-duplicated."""
    bad = [m for m in months if not MONTH_PATTERN.match(m)]
    if bad:
        raise ValueError(f"Months must look like YYYY-MM; got {bad}")
    return sorted(set(months))


def download_file(url: str, dest: Path, force: bool = False, timeout: int = 60) -> bool:
    """
    Stream `url` to `dest`. Returns True if a download happened, False if
    the file already existed and was skipped.

    Downloads go to a temporary '.part' file first and are renamed only on
    success, so an interrupted download never leaves a truncated file that
    looks complete.
    """
    if dest.exists() and not force:
        print(f"  skip (exists): {dest.name}")
        return False

    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    print(f"  downloading: {url}")
    with requests.get(url, stream=True, timeout=timeout) as resp:
        resp.raise_for_status()  # 403/404 -> exception, not a silent bad file
        with tmp.open("wb") as f:
            for block in resp.iter_content(chunk_size=CHUNK):
                f.write(block)
    tmp.replace(dest)
    print(f"  saved: {dest.name} ({dest.stat().st_size / 1e6:.1f} MB)")
    return True


def manifest_entry(url: str, path: Path, downloaded_now: bool, previous: dict | None) -> dict:
    """Build one manifest record. Keeps the original download time if we skipped."""
    entry = {
        "source_url": url,
        "local_path": str(path.relative_to(config.PROJECT_ROOT)),
        "size_bytes": path.stat().st_size,
        "sha256": sha256_of(path),
    }
    if downloaded_now or not previous:
        entry["downloaded_at_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    else:
        entry["downloaded_at_utc"] = previous.get("downloaded_at_utc")
    if previous and previous.get("sha256") not in (None, entry["sha256"]):
        print(f"  WARNING: checksum changed for {path.name} (file was re-published or altered)")
    return entry


def load_manifest(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text())
    return {"files": {}}


def run(months: list[str], force: bool = False) -> dict:
    months = validate_months(months)
    manifest = load_manifest(config.MANIFEST_PATH)
    manifest["data_dictionary_url"] = config.DATA_DICTIONARY_URL
    manifest["landing_page"] = config.TLC_LANDING_PAGE

    targets = [(config.ZONE_LOOKUP_URL, config.RAW_DIR / "taxi_zone_lookup.csv")]
    targets += [(config.trip_url(m), config.RAW_DIR / config.trip_filename(m)) for m in months]

    for url, dest in targets:
        did_download = download_file(url, dest, force=force)
        manifest["files"][dest.name] = manifest_entry(
            url, dest, did_download, manifest["files"].get(dest.name)
        )

    config.MANIFEST_PATH.write_text(json.dumps(manifest, indent=2))
    print(f"Manifest written: {config.MANIFEST_PATH.relative_to(config.PROJECT_ROOT)}")
    return manifest


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Download NYC TLC yellow taxi data.")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--full", action="store_true", help="download all months in MONTHS_FULL")
    g.add_argument("--months", nargs="+", help="explicit months, e.g. 2024-01 2024-02")
    p.add_argument("--force", action="store_true", help="re-download even if file exists")
    args = p.parse_args(argv)

    months = args.months or (config.MONTHS_FULL if args.full else config.MONTHS_SAMPLE)
    try:
        run(months, force=args.force)
    except requests.HTTPError as e:
        print(f"Download failed: {e}. Check the month is published on {config.TLC_LANDING_PAGE}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
