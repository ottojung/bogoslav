
from typing import Sequence

import pytest

from bogoslav.parser import parse, ParsedAIBlock

# Import the module under test.  It should be discoverable on PYTHONPATH when
# the package is installed in editable mode or when running from the repo root.
from bogoslav.unparser import serialize_ai_blocks, serialize_block


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _round_trip(original: str) -> Sequence[ParsedAIBlock]:
    """Parse → serialize → parse again → return second parse result."""

    first = parse(original)
    serialised: str = serialize_ai_blocks(first)
    ret: Sequence[ParsedAIBlock] = parse(serialised)
    return ret


# ---------------------------------------------------------------------------
# Smoke tests – examples inspired by the reference parser tests
# ---------------------------------------------------------------------------

def test_round_trip_single_block() -> None:
    doc = """#+begin_ai markdown
Hello, world!
#+end_ai
"""
    assert _round_trip(doc) == parse(doc)


def test_round_trip_with_params_and_headers() -> None:
    doc = """
#+begin_ai markdown :model "o3-mini" :temp 0
Some question here.
Can be multiline...
[AI]:
Some response here.
[ME]: Follow‑up?
#+end_ai
"""
    assert _round_trip(doc) == parse(doc)


def test_round_trip_multiple_blocks() -> None:
    doc = (
        "#+begin_ai a\nOne\n#+end_ai\n\n"
        "#+begin_ai b :foo \"bar\"\n[AI]:Two\n#+end_ai\n"
    )
    assert _round_trip(doc) == parse(doc)


# ---------------------------------------------------------------------------
# Formatting behaviour – specific expectations
# ---------------------------------------------------------------------------

def test_first_user_header_omitted() -> None:
    blocks = [
        ParsedAIBlock(
            language="txt",
            params={},
            messages=[
                ("user", "Hi there!\n"),
                ("assistant", "\nHello!\n"),
            ],
        )
    ]
    text = serialize_ai_blocks(blocks)

    # The very first message should appear without a [ME]: header
    assert "[ME]:" not in text.split("\n", 2)[1]  # second line is body

    # Round‑trip remains identical
    assert parse(text) == blocks


def test_param_quoting_and_ordering() -> None:
    blocks = [
        ParsedAIBlock(
            language="python",
            params={"z": 42, "a": "string with \"quotes\" inside"},
            messages=[("user", "print(\"hi\")\n")],
        )
    ]
    txt = serialize_ai_blocks(blocks)

    # Keys should appear sorted: a … z  (not insertion order)
    begin_line = txt.split("\n", 1)[0]
    assert begin_line.startswith("#+begin_ai python :a \"string with ")
    assert ":z 42" in begin_line

    # Embedded quotes must be escaped
    assert '\\"' in begin_line  # escaped quote pattern

    # Round‑trip equivalence
    assert parse(txt) == blocks


def test_preserves_leading_newline_in_body() -> None:
    blocks = [
        ParsedAIBlock(
            language="md",
            params={},
            messages=[
                ("assistant", "\nHello after newline\n"),
                ("user", "Inline reply.\n"),
            ],
        )
    ]

    txt = serialize_ai_blocks(blocks)

    # The assistant message should start with header on its own line followed by
    # an **empty** line (because body started with \n)
    assert "[AI]:\nHello after" in txt

    # Inline header form should be used for the user reply because body does not
    # start with newline
    assert "[ME]: Inline reply." in txt

    # Round‑trip equivalence
    assert parse(txt) == blocks
