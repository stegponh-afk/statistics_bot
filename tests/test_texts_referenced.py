"""Every `ru.NAME` used anywhere in app/ must exist — a missing string
only blows up at runtime on the screen that uses it."""

import re
from pathlib import Path

from app.texts import ru

_RE = re.compile(r"\bru\.([A-Z][A-Z0-9_]+)")


def test_all_referenced_strings_exist():
    missing = set()
    for path in Path("app").rglob("*.py"):
        for name in _RE.findall(path.read_text(encoding="utf-8")):
            if not hasattr(ru, name):
                missing.add(f"{path}: {name}")
    assert not missing, sorted(missing)
