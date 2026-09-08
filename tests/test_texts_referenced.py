"""Guards on app/texts/ru.py for the kinds of breakage that only show up
at runtime, on the one screen nobody reopened."""

import re
from pathlib import Path

from app.texts import ru

_RE = re.compile(r"\bru\.([A-Z][A-Z0-9_]+)")
# callback.answer(ru.NAME, ..., show_alert=True), possibly wrapped over lines.
_ALERT_RE = re.compile(r"answer\(\s*ru\.([A-Z][A-Z0-9_]+)[^)]*show_alert=True", re.S)
# answerCallbackQuery.text is capped at 200 characters, and Telegram cuts
# the rest off mid-sentence — worst of all for the texts that exist to
# explain how to fix something.
ALERT_LIMIT = 200


def test_all_referenced_strings_exist():
    missing = set()
    for path in Path("app").rglob("*.py"):
        for name in _RE.findall(path.read_text(encoding="utf-8")):
            if not hasattr(ru, name):
                missing.add(f"{path}: {name}")
    assert not missing, sorted(missing)


def test_every_constant_is_a_string():
    """A stray trailing comma turns a screen into a one-element tuple, and
    the failure surfaces as garbled output on that screen only."""
    wrong = {
        name: type(getattr(ru, name)).__name__
        for name in dir(ru)
        if name.isupper() and not isinstance(getattr(ru, name), str | dict)
    }
    assert not wrong, wrong


def test_alert_texts_fit_in_a_popup():
    too_long = {}
    for path in Path("app").rglob("*.py"):
        for name in _ALERT_RE.findall(path.read_text(encoding="utf-8")):
            text = getattr(ru, name, "")
            if isinstance(text, str) and len(text) > ALERT_LIMIT:
                too_long[name] = len(text)
    assert not too_long, too_long
