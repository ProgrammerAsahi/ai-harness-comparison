"""Read historical editorial inputs with explicit, reviewed prose revisions."""
import json
from pathlib import Path

REVISIONS = json.loads(Path(__file__).with_name("editorial-revisions.json").read_text())


def read_baseline(path):
    text = path.read_text()
    for edit in REVISIONS.get(path.name, []):
        if edit["before"] not in text:
            raise ValueError(f"Stale editorial revision in {path.name}: {edit['before']}")
        text = text.replace(edit["before"], edit["after"])
    return text
