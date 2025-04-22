
"""
Two‐pass parser for AI‐block annotated text.

Pass 1: extract !+begin_ai … !+end_ai blocks into AIBlock(language, params, content).
Pass 2: split each AIBlock.content into a sequence of (role, message_text)
         where role is "user" or "assistant", as demarcated by lines
         starting with [ME]: or [AI]:.

The top‐level function `parse()` runs both passes and returns a list of
fully‐parsed blocks.
"""

from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional, Union, Sequence, Literal
from lark import Lark, Transformer, Token, Tree

# ------------------------------------------------------------------------------
# PASS 1: find !+begin_ai … !+end_ai blocks
# ------------------------------------------------------------------------------

GRAMMAR = r"""
start: (blank_line | ai_block | other_line)*

blank_line: BLANK_LINE
other_line: OTHER_LINE   -> _ignore

ai_block: begin_line content* end_line

begin_line: BEGIN_MARK WS_INLINE LANGUAGE (WS_INLINE param)* WS_INLINE? NEWLINE
end_line:   END_MARK   WS_INLINE? NEWLINE

param: ":" CNAME WS_INLINE QUOTED_STRING
content: CONTENT_LINE

BEGIN_MARK:    /[ \t]*\!\+begin_ai/
END_MARK:      /[ \t]*\!\+end_ai/
BLANK_LINE:    /[ \t]*\n/
LANGUAGE:      /[A-Za-z][A-Za-z0-9\-]*/

%import common.CNAME
%import common.WS_INLINE
%import common.NEWLINE
%import common.ESCAPED_STRING -> QUOTED_STRING

CONTENT_LINE:  /(?![ \t]*\!\+end_ai)[^\n]*\n/
OTHER_LINE:    /[^\n]*\n/

%ignore /#[^\n]*/
"""

Language = str
AIBlockParams = Dict[str, Union[str, int]]

@dataclass(frozen=True)
class AIBlock:
    """
    One raw !+begin_ai … !+end_ai block.
      .language : str
      .params   : dict of key→value
      .content  : str (raw lines between markers, including newlines)
    """
    language: Language
    params: AIBlockParams
    content: str

class _ASTTransformer(Transformer[Token, Sequence[AIBlock]]):
    def blank_line(self, _: Sequence[Tree[Token]]) -> None:
        return None

    def _ignore(self, _: Sequence[Tree[Token]]) -> None:
        return None

    def begin_line(
        self,
        items: Sequence[Union[Token, Tuple[str,str]]]
    ) -> Tuple[str, Sequence[Tuple[str,str]]]:
        lang: Optional[str] = None
        params: Sequence[Tuple[str,str]] = []
        for it in items:
            if isinstance(it, Token) and it.type == "LANGUAGE":
                lang = it.value
            elif isinstance(it, tuple):
                params.append(it)
        assert lang is not None, "Missing LANGUAGE in begin_line"
        return lang, params

    def param(self, items: Sequence[Token]) -> Tuple[str,str]:
        key_tok, _ws, val_tok = items
        key = key_tok.value
        val = val_tok.value[1:-1]
        return key, val

    def content(self, items: Sequence[Token]) -> str:
        ret = items[0].value
        assert isinstance(ret, str)
        return ret

    def end_line(self, _: Sequence[Tree[Token]]) -> None:
        return None

    def ai_block(
        self,
        items: Sequence[Union[Tuple[str,Sequence[Tuple[str,str]]], str, None]],
    ) -> AIBlock:
        language, param_list = items[0]  # type: ignore
        lines = [x for x in items[1:] if isinstance(x, str)]
        return AIBlock(language, dict(param_list), "".join(lines))

    def start(self, items: Sequence[Optional[AIBlock]]) -> Sequence[AIBlock]:
        return [b for b in items if isinstance(b, AIBlock)]

_parser = Lark(
    GRAMMAR,
    parser="lalr",
    propagate_positions=False,
    maybe_placeholders=False,
)

def parse_ai_blocks(text: str) -> Sequence[AIBlock]:
    """
    Pass 1: parse the text, return raw AIBlock instances.
    Raises on malformed input.
    """
    tree = _parser.parse(text)
    return _ASTTransformer().transform(tree)


# ------------------------------------------------------------------------------
# PASS 2: split raw block.content into messages by role
# ------------------------------------------------------------------------------

MSG_GRAMMAR = r"""
start: default_message? message*

default_message: body_lines+

message: header body_lines*

# ------------------------------------------------------------------
#  ❖ Header lines now look like “[ME]: …” or “[AI]: …”
# ------------------------------------------------------------------
header: ME_HEADER     -> me
      | AI_HEADER     -> ai

ME_HEADER: "[ME]:" WS_INLINE?
AI_HEADER: "[AI]:" WS_INLINE?

# Body = every line up to (but not including) the *next* header
body_lines: /(?:(?!(?:\[ME\]:|\[AI\]:))[^\n]*\n)/

%import common.WS_INLINE
%import common.NEWLINE
"""


MessageRole = Literal["user", "assistant"]
MessageText = str
Message = Tuple[MessageRole, MessageText]


class _MsgTransformer(Transformer[Token, Sequence[Message]]):
    def start(self, items: Sequence[Message]) -> Sequence[Message]:
        return items

    def default_message(self, items: Sequence[str]) -> Message:
        return ("user", "".join(items))

    def message(self, items: Sequence[str]) -> Message:
        role_val: str = items[0]
        if role_val == "user":
            role: MessageRole = "user"
        elif role_val == "assistant":
            role = "assistant"
        else:
            raise TypeError("Invalid role.", role_val)
        body = "".join(map(str, items[1:]))
        return (role, body)

    def me(self, _: Sequence[Token]) -> MessageRole:
        return "user"

    def ai(self, _: Sequence[Token]) -> MessageRole:
        return "assistant"

    def body_lines(self, items: Sequence[Token]) -> str:
        ret = items[0].value
        assert isinstance(ret, str)
        return ret


_msg_parser = Lark(
    MSG_GRAMMAR,
    parser="lalr",
    propagate_positions=False,
    maybe_placeholders=False,
)

def split_messages(block_content: str) -> Sequence[Message]:
    """
    Pass 2: split a raw block.content into (role, message_text) tuples.
    """

    tree = _msg_parser.parse(block_content)
    return _MsgTransformer().transform(tree)


# ------------------------------------------------------------------------------
# TOP‐LEVEL: run both passes and return "fully parsed" blocks
# ------------------------------------------------------------------------------

@dataclass(frozen=True)
class ParsedAIBlock:
    """
    Fully parsed AI block:
      .language : str
      .params   : dict of key→value
      .messages : list of (role, text) tuples
    """
    language: Language
    params: AIBlockParams
    messages: Sequence[Message]


def parse(text: str) -> Sequence[ParsedAIBlock]:
    """
    Top‐level entry point.

    Given the full document text, run pass 1 to find all AI blocks,
    then pass 2 on each block.content to split into user/assistant messages.
    Returns a list of ParsedAIBlock.
    """

    raw_blocks: Sequence[AIBlock] = parse_ai_blocks(text)
    parsed: List[ParsedAIBlock] = []
    for blk in raw_blocks:
        msgs = split_messages(blk.content)
        parsed.append(ParsedAIBlock(blk.language, blk.params, msgs))
    return parsed
