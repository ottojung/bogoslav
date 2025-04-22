
import pytest
from bogoslav.parser import parse_ai_blocks, AIBlock

def test_single_simple_block() -> None:
    txt = """!+begin_ai markdown
Hello, world!
!+end_ai
"""
    blocks = parse_ai_blocks(txt)
    assert len(blocks) == 1
    b = blocks[0]
    assert b.language == "markdown"
    assert b.params   == {}
    assert b.content  == "Hello, world!\n"

def test_block_with_params_and_blank_lines() -> None:
    txt = """

  !+begin_ai   python   :model  "o3-mini"   :opt "fast"
print("Hi")
!+end_ai

"""
    blocks = parse_ai_blocks(txt)
    assert len(blocks) == 1
    b = blocks[0]
    assert b.language == "python"
    assert b.params   == {"model":"o3-mini", "opt":"fast"}
    assert b.content  == 'print("Hi")\n'

def test_multiple_blocks_and_interleaved_blanks() -> None:
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

def test_no_blocks_returns_empty() -> None:
    txt = "just some text\nand no markers\n"
    blocks = parse_ai_blocks(txt)
    assert blocks == []

@pytest.mark.parametrize("bad", [
    "!+begin_ai\nno language\n!+end_ai\n",    # missing language
    "!+begin_ai md\nunclosed block\n",        # missing end marker
])
def test_malformed_raises(bad: str) -> None:
    with pytest.raises(Exception):
        parse_ai_blocks(bad)
