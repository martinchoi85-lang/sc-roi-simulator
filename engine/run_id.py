"""run_id calculation utility strictly adhering to SPEC_v9_1 Section 0-3.

Format: YYYYMMDDTHHMMSS_<git_short_hash>_<config_input_sha8>
- git_short_hash: 7-character commit hash of HEAD (appends -dirty if working tree is dirty).
- config_input_sha8: First 8 characters of SHA-256 of sorted concatenation of
  korea/config/*.yaml + korea/source/kosis/*.csv.
"""

from datetime import datetime
import hashlib
from pathlib import Path
import subprocess


def compute_run_id(country_dir: Path) -> str:
    """Computes run_id adhering strictly to Section 0-3."""
    ts = datetime.now().strftime("%Y%m%dT%H%M%S")

    # git short hash
    try:
        git_hash = subprocess.check_output(
            ["git", "rev-parse", "--short=7", "HEAD"], text=True
        ).strip()
        status = subprocess.check_output(
            ["git", "status", "--porcelain"], text=True
        ).strip()
        if status:
            git_hash += "-dirty"
    except Exception:
        git_hash = "unknown"

    # config_input_sha8
    h = hashlib.sha256()
    config_files = sorted((country_dir / "config").glob("*.yaml"))
    kosis_files = sorted((country_dir / "source" / "kosis").glob("*.csv"))
    for f in config_files + kosis_files:
        h.update(f.name.encode("utf-8"))
        h.update(f.read_bytes())
    sha8 = h.hexdigest()[:8]

    return f"{ts}_{git_hash}_{sha8}"

