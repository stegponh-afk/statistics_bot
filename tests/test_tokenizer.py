from app.services.tokenizer import MAX_DISTINCT_PER_MESSAGE, tokenize


def test_lowercases_and_folds_yo():
    assert tokenize("Ёлка ЁЛКА елка") == {"елка": 3}


def test_drops_short_words_and_stopwords():
    assert tokenize("я и ты — это привет мир") == {"мир": 1}
    assert tokenize("the cat and the dog") == {"cat": 1, "dog": 1}


def test_strips_urls_mentions_hashtags_and_commands():
    text = "смотри https://example.com/path @someone #тег /stats@bot слово"
    assert tokenize(text) == {"слово": 1, "смотри": 1}


def test_keeps_hyphenated_words_and_drops_digits():
    assert tokenize("что-нибудь 12345 a1b2 давно-давно") == {"что-нибудь": 1, "давно-давно": 1}


def test_drops_single_character_runs():
    assert tokenize("ааааа ммм ура") == {"ура": 1}


def test_caps_distinct_words_per_message():
    text = " ".join(f"word{i}abc" for i in range(200))
    # digits split the token, so use letters only
    text = " ".join("слово" + chr(0x430 + i % 30) * 2 + chr(0x430 + i // 30) for i in range(200))
    assert len(tokenize(text)) <= MAX_DISTINCT_PER_MESSAGE


def test_empty_and_none():
    assert tokenize(None) == {}
    assert tokenize("") == {}
