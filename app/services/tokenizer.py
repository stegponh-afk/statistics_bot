"""Message text -> Counter of words worth counting. The words are all that
ever gets stored about a message's content (per day, aggregated)."""

import re
from collections import Counter

from app.services.stopwords import STOPWORDS

MIN_LENGTH = 3
MAX_LENGTH = 64
MAX_DISTINCT_PER_MESSAGE = 100

_NOISE_RE = re.compile(r"(https?://\S+|www\.\S+|@\w+|#\w+|/\w+)", re.IGNORECASE)
_WORD_RE = re.compile(r"[a-zа-я]+(?:-[a-zа-я]+)?")


def tokenize(text: str | None) -> Counter[str]:
    if not text:
        return Counter()
    cleaned = _NOISE_RE.sub(" ", text).lower().replace("ё", "е")
    counts: Counter[str] = Counter()
    for word in _WORD_RE.findall(cleaned):
        if len(word) < MIN_LENGTH or word in STOPWORDS:
            continue
        if len(set(word)) == 1:  # "ааааа"
            continue
        counts[word[:MAX_LENGTH]] += 1
        if len(counts) >= MAX_DISTINCT_PER_MESSAGE:
            break
    return counts
