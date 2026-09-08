from app.services.markdown import has_markup, markdown_to_html


def test_inline_styles():
    assert markdown_to_html("**жирный** и *тоже*") == "<b>жирный</b> и <b>тоже</b>"
    assert markdown_to_html("_курсив_") == "<i>курсив</i>"
    assert markdown_to_html("__подчёркнутый__") == "<u>подчёркнутый</u>"
    assert markdown_to_html("~~зач~~ ~тоже~") == "<s>зач</s> <s>тоже</s>"
    assert markdown_to_html("||спойлер||") == "<tg-spoiler>спойлер</tg-spoiler>"


def test_code_and_links_are_protected_and_escaped():
    assert markdown_to_html("`a < b *x*`") == "<code>a &lt; b *x*</code>"
    assert markdown_to_html("```python\nprint(1 < 2)\n```") == (
        '<pre><code class="language-python">print(1 &lt; 2)</code></pre>'
    )
    assert markdown_to_html("[сайт *x*](https://example.com/?a=1&b=2)") == (
        '<a href="https://example.com/?a=1&amp;b=2">сайт *x*</a>'
    )


def test_blockquote_and_plain_text_escaping():
    assert markdown_to_html("> строка 1\n> строка 2\nобычная") == (
        "<blockquote>строка 1\nстрока 2</blockquote>\nобычная"
    )
    assert markdown_to_html("a < b & c") == "a &lt; b &amp; c"


def test_underscores_inside_words_are_left_alone():
    assert markdown_to_html("snake_case_name и 2*3*4") == "snake_case_name и 2*3*4"


def test_has_markup():
    assert has_markup("*x*") is True
    assert has_markup("просто текст") is False
