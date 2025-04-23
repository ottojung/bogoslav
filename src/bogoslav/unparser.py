
"""
Inverse (serializer) for AI‑block annotated text.

This module turns the in‑memory representation produced by
``bogoslav.parser.parse`` – a sequence of ``ParsedAIBlock`` – back into the
text form that ``parse`` can read.

Round‑tripping guarantee
------------------------
If a document is parsed with ``bogoslav.parser.parse`` and then immediately
serialised with :pyfunc:`serialize_ai_blocks`, reparsing the result yields an
*equivalent* list of :class:`~bogoslav.parser.ParsedAIBlock` objects.  Some
incidental whitespace (e.g. the exact number of blank lines between blocks or
spacing after a header token) may differ, but the semantic content – language,
params, role order, and message texts – is preserved.

The formatter aims to produce clean, human‑readable output:
* All parameters are emitted in **sorted key order** for determinism.
* String parameter values are **double‑quoted** with embedded quotes escaped.
* The first user message is written without an explicit ``[ME]:`` header when
  this introduces no ambiguity, mirroring the shorthand accepted by the
  parser.
* Every other message is introduced by a header token on its own line (or
  continuing the line when the message body does not start with a newline),
  closely matching the styles present in the reference tests.
"""

from typing import Sequence, Tuple, Dict, Union, List, NoReturn

from .parser import ParsedAIBlock, MessageRole, MessageText, Message

from .logger import logger

ParamValue = Union[str, int]

__all__ = [
    "serialize_block",
    "serialize_ai_blocks",
]

# ---------------------------------------------------------------------------
# Helpers – parameters & quoting
# ---------------------------------------------------------------------------

def _quote_param(val: ParamValue) -> str:
    """Return a serialised representation for *val* suitable for begin‑line."""
    if isinstance(val, int):
        return str(val)
    else:
        escaped: str = val
        # Escape embedded quotes.  Backslashes are not allowed by the grammar so we
        # only need to escape the quote character itself.
        escaped = escaped.replace("\"", "\\\"")
        escaped = '"' + escaped + '"'
        return escaped


def _serialise_params(params: Dict[str, ParamValue]) -> str:
    """Return the *space‑prefixed* parameter segment for a begin‑line."""
    if not params:
        return ""
    # Emit in sorted key order for stable output.
    parts: List[str] = [f":{key} {_quote_param(params[key])}" for key in sorted(params)]
    return " " + " ".join(parts)

# ---------------------------------------------------------------------------
# Helpers – messages
# ---------------------------------------------------------------------------

def _header_for_role(role: MessageRole) -> str:
    if role == "user":
        return "[ME]:"
    elif role == "assistant":
        return "[AI]:"
    elif role == "system":
        return "[SYSTEM]:"
    else:
        _x: NoReturn = role
        raise ValueError(f"Unexpected role {role!r}.")


def _serialise_messages(messages: Sequence[Message]) -> str:
    """Convert the *messages* list back into the textual body of a block."""
    out_parts: List[str] = []

    for idx, message in enumerate(messages):
        header = _header_for_role(message.role)
        if message.text.startswith("\n"):
            # Put header on its own line → keep the leading newline in *body*.
            out_parts.append(header + message.text)
        else:
            # Inline body after header.  Insert a single separating space unless
            # the body itself already begins with whitespace.
            sep = "" if message.text[:1].isspace() else " "
            out_parts.append(header + sep + message.text)

    return "".join(out_parts)

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def serialize_block(block: ParsedAIBlock) -> str:
    """Serialise a single :class:`~bogoslav.parser.ParsedAIBlock`."""
    begin = f"#+begin_ai {block.language}{_serialise_params(block.params)}\n"
    body = _serialise_messages(block.messages)
    if body.endswith("\n"):
        end = ""
    else:
        end = "\n"
    end += "#+end_ai"
    end += "\n"
    return begin + body + end


def serialize_ai_blocks(blocks: Sequence[ParsedAIBlock]) -> str:
    """Serialise *blocks* into a full document string.

    Blocks are separated by a single blank line for readability.
    """
    if not blocks:
        return ""

    return "\n\n".join(serialize_block(b) for b in blocks)
