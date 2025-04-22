
import pytest
from bogoslav.parser import (
    parse_ai_blocks,
    AIBlock,
    parse,
    ParsedAIBlock,
)

# -------------------------------------------------------------------
# Tests for pass 1: parse_ai_blocks (almost as before)
# -------------------------------------------------------------------

def test_single_simple_block_pass1() -> None:
    txt = """!+begin_ai markdown
Hello, world!
!+end_ai
"""
    blocks = parse_ai_blocks(txt)
    assert len(blocks) == 1
    b = blocks[0]
    assert isinstance(b, AIBlock)
    assert b.language == "markdown"
    assert b.params == {}
    assert b.content == "Hello, world!\n"

def test_block_with_params_and_blank_lines_pass1() -> None:
    txt = """

  !+begin_ai   python   :model  "o3-mini"   :opt "fast"
print("Hi")
!+end_ai

"""
    blocks = parse_ai_blocks(txt)
    assert len(blocks) == 1
    b = blocks[0]
    assert b.language == "python"
    assert b.params == {"model": "o3-mini", "opt": "fast"}
    assert b.content == 'print("Hi")\n'

def test_multiple_blocks_and_interleaved_blanks_pass1() -> None:
    txt = """
!+begin_ai md
First
!+end_ai

!+begin_ai txt
Second line
!+end_ai
"""
    blocks = parse_ai_blocks(txt)
    expected = [
        AIBlock("md", {}, "First\n"),
        AIBlock("txt", {}, "Second line\n"),
    ]
    assert blocks == expected

def test_no_blocks_returns_empty_pass1() -> None:
    txt = "just some text\nand no markers\n"
    blocks = parse_ai_blocks(txt)
    assert blocks == []

@pytest.mark.parametrize("bad", [
    "!+begin_ai\nno language\n!+end_ai\n",    # missing language
    "!+begin_ai md\nunclosed block\n",        # missing end marker
])
def test_malformed_raises_pass1(bad: str) -> None:
    with pytest.raises(Exception):
        parse_ai_blocks(bad)


# -------------------------------------------------------------------
# Tests for pass 2 and top‑level parse()
# -------------------------------------------------------------------

def test_parse_default_user_message() -> None:
    # content has no ``` headers → everything is user
    text = """!+begin_ai txt
Just some text
with multiple lines.
!+end_ai
"""
    result = parse(text)
    assert len(result) == 1
    pb = result[0]
    assert isinstance(pb, ParsedAIBlock)
    assert pb.language == "txt"
    assert pb.params == {}
    # since no ```header, we get one ("user", full_content)
    assert pb.messages == [
        ("user", "Just some text\nwith multiple lines.\n")
    ]

def test_parse_with_assistant_and_user_headers() -> None:
    # a block that starts with user text, then assistant reply, then user follow‑up
    text = """!+begin_ai markdown :model "o3-mini"
Some question here.
Can be multiline...
[AI]:
Some response here.
Can be
multiline
as well.
[ME]:
Maybe another question here.
!+end_ai
"""
    parsed = parse(text)
    assert len(parsed) == 1
    pb = parsed[0]
    assert pb.language == "markdown"
    assert pb.params == {"model": "o3-mini"}

    # Expect three messages: default‐user, assistant, then user
    assert pb.messages == [
        (
            "user",
            "Some question here.\n"
            "Can be multiline...\n"
        ),
        (
            "assistant",
            "\n"
            "Some response here.\n"
            "Can be\n"
            "multiline\n"
            "as well.\n"
        ),
        (
            "user",
            "\n"
            "Maybe another question here.\n"
        ),
    ]

def test_parse_with_assistant_and_user_headers_2() -> None:
    # a block that starts with user text, then assistant reply, then user follow‑up
    text = """!+begin_ai markdown :model "o3-mini"
Some question here.
Can be multiline...
[AI]: Some response here.
Can be
multiline
as well.
[ME]:
Maybe another question here.
!+end_ai
"""
    parsed = parse(text)
    assert len(parsed) == 1
    pb = parsed[0]
    assert pb.language == "markdown"
    assert pb.params == {"model": "o3-mini"}

    # Expect three messages: default‐user, assistant, then user
    assert pb.messages == [
        (
            "user",
            "Some question here.\n"
            "Can be multiline...\n"
        ),
        (
            "assistant",
            "Some response here.\n"
            "Can be\n"
            "multiline\n"
            "as well.\n"
        ),
        (
            "user",
            "\n"
            "Maybe another question here.\n"
        ),
    ]

def test_parse_header_first() -> None:
    # block content begins immediately with a header → no default_user
    text = """!+begin_ai md
[AI]:
Hello!
[ME]:
OK thanks
!+end_ai
"""
    parsed = parse(text)
    assert len(parsed) == 1
    msgs = parsed[0].messages
    # first message comes from header
    assert msgs == [
        ("assistant", "\nHello!\n"),
        ("user", "\nOK thanks\n"),
    ]

def test_parse_multiple_blocks_top_level() -> None:
    text = """
!+begin_ai a
Line A1
Line A2
!+end_ai

!+begin_ai b
[AI]:
Reply B
[ME]:
Followup B
!+end_ai
"""
    parsed = parse(text)
    assert len(parsed) == 2

    pb1, pb2 = parsed
    assert pb1.language == "a"
    assert pb1.messages == [
        ("user", "Line A1\nLine A2\n")
    ]

    assert pb2.language == "b"
    assert pb2.messages == [
        ("assistant", "\nReply B\n"),
        ("user", "\nFollowup B\n"),
    ]

def test_parse_malformed_passes_error_through() -> None:
    # missing end_ai should still raise
    bad = "!+begin_ai md\nUnclosed\n"
    with pytest.raises(Exception):
        parse(bad)
