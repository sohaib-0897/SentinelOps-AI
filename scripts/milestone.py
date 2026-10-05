"""Append milestone context inside the associated implementation commit."""
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

phase, change, checks, *limitations = sys.argv[1:]
previous = subprocess.check_output([shutil.which("git") or "git", "rev-parse", "--short", "HEAD"], text=True).strip()  # noqa: S603 -- fixed Git read operation
entry = f"| {phase} | {datetime.now(UTC).date()} | This commit; parent `{previous}` | {change} | {checks} | {limitations[0] if limitations else 'None for this milestone.'} |\n"
with Path("docs/DEVELOPMENT_LOG.md").open("a", encoding="utf-8") as log:
    log.write(entry)
