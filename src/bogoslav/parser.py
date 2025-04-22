
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional, Union, Sequence
from lark import Lark, Transformer, Token, Tree

GRAMMAR = r"""
//───────────────────────────────────────────────────────────────────────────────
// Top‐level: zero or more blank lines, blocks, or other lines
//───────────────────────────────────────────────────────────────────────────────
start: (blank_line | ai_block | other_line)*

blank_line: BLANK_LINE
other_line: OTHER_LINE   -> _ignore

//───────────────────────────────────────────────────────────────────────────────
// One AI block
//───────────────────────────────────────────────────────────────────────────────
ai_block: begin_line content* end_line

// The begin marker, with optional params, then newline
begin_line: BEGIN_MARK WS_INLINE LANGUAGE (WS_INLINE param)* WS_INLINE? NEWLINE

// The end marker
end_line:   END_MARK   WS_INLINE? NEWLINE

// A key/value parameter in the begin line
param: ":" CNAME WS_INLINE QUOTED_STRING

// Any line up to but not including an !+end_ai
content: CONTENT_LINE

//───────────────────────────────────────────────────────────────────────────────
// Terminals
//───────────────────────────────────────────────────────────────────────────────

// These three must come first so they preempt OTHER_LINE
BEGIN_MARK:    /[ \t]*\!\+begin_ai/
END_MARK:      /[ \t]*\!\+end_ai/
BLANK_LINE:    /[ \t]*\n/

// An identifier for the language (e.g. markdown, python)
LANGUAGE:      /[A-Za-z][A-Za-z0-9\-]*/

// Import names, whitespace, and quoted strings
%import common.CNAME
%import common.WS_INLINE
%import common.NEWLINE
%import common.ESCAPED_STRING -> QUOTED_STRING

// A content line inside a block—anything except the end marker
CONTENT_LINE:  /(?![ \t]*\!\+end_ai)[^\n]*\n/

// A catch‐all for any line not matched above (outside blocks)
OTHER_LINE:    /[^\n]*\n/

// allow shell‐style comments anywhere
%ignore /#[^\n]*/
"""


Language = str
AIBlockParams = Dict[str, Union[str, int]]


# --------------------------------------------------------------------
# Data class for one parsed !+begin_ai … !+end_ai block
# --------------------------------------------------------------------
@dataclass(frozen=True)
class AIBlock:
    """
    .language : Language       e.g. "markdown" or "python"
    .params   : AIBlockParams  mapping of keys->values from :key "value"
    .content  : str            the raw lines between begin/end (with newlines)
    """
    language: Language
    params: AIBlockParams
    content: str


# --------------------------------------------------------------------
# Transform the Lark parse‐tree into AIBlock instances
# --------------------------------------------------------------------
class _ASTTransformer(Transformer[Token, List[AIBlock]]):
    # blank_line -> None
    def blank_line(self, _: List[Tree[Token]]) -> None:
        return None

    # other_line -> None
    def _ignore(self, _: List[Tree[Token]]) -> None:
        return None

    # begin_line → (language, [(key,val),…])
    def begin_line(self, items: List[Token]) -> Tuple[str, List[Tuple[str,str]]]:
        lang: Optional[str] = None
        params: List[Tuple[str,str]] = []
        for it in items:
            if isinstance(it, Token) and it.type == "LANGUAGE":
                lang = it.value
            elif isinstance(it, tuple):
                params.append(it)
        assert lang is not None, "Missing LANGUAGE in begin_line"
        return lang, params

    # param → (key, unquoted_value)
    def param(self, items: List[Token]) -> Tuple[str,str]:
        key_tok, whitespace, val_tok = items
        key = key_tok.value
        # val_tok is ESCAPED_STRING, so strip quotes
        val = val_tok.value[1:-1]
        return key, val

    # content → raw line text
    def content(self, items: List[Token]) -> str:
        txt = items[0].value
        assert isinstance(txt, str)
        return txt

    # end_line → None
    def end_line(self, _: List[Tree[Token]]) -> None:
        return None

    # ai_block → build an AIBlock
    def ai_block(self, items: List[Tuple[Language, Sequence[Tuple[str, str]]]]) -> AIBlock:
        # items[0]   = (language, param_list)
        # items[1:-1] = zero or more content‐lines (str)
        # items[-1]  = None (from end_line)
        language, param_list = items[0]
        lines = [x for x in items[1:] if isinstance(x, str)]
        return AIBlock(language, dict(param_list), "".join(map(str, lines)))

    # start → filter out None's and return List[AIBlock]
    def start(self, items: List[Optional[AIBlock]]) -> List[AIBlock]:
        return [b for b in items if isinstance(b, AIBlock)]


# --------------------------------------------------------------------
# Build the LALR(1) parser once
# --------------------------------------------------------------------
_parser = Lark(
    GRAMMAR,
    parser="lalr",
    propagate_positions=False,
    maybe_placeholders=False,
)

def parse_ai_blocks(text: str) -> List[AIBlock]:
    """
    Parse the given text and return a list of AIBlock objects.
    Lines outside of any block are ignored.
    """
    tree = _parser.parse(text)             # may raise on malformed input
    return _ASTTransformer().transform(tree)
