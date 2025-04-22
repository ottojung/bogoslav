"""
A hermetic façade over Google Gemini that converts the domain‑specific
conversation representation employed by *Bogoslav* into the wire schema
required by the public Gemini SDK and vice versa.

The wrapper is intentionally minimal: it is agnostic of the higher‑level
*org‑mode* parsing layer and exposes a single, side‑effect‑free function
:`_communicate`, which performs the following steps:

1. **Lazy client initialisation** – a cached constructor retrieves the API key
   from :pydata:`~os.environ` and instantiates :pyclass:`google.genai.Client`.
2. **Message marshalling** – the program‑internal `(role, text)` tuples are
   transformed into Gemini‑compatible dictionaries containing *role* and *parts*.
3. **Streaming inference** – the client is queried with the terse, low‑latency
   *"gemini‑2.0‑flash"* model; responses are consumed incrementally and
   concatenated locally.
4. **Canonical return value** – the assembled reply is yielded as a single
   :pydata:`("assistant", text)` tuple that the surrounding code can
   immediately append to a :pyclass:`bogoslav.parser.ParsedAIBlock`.

This self‑contained adapter ensures that the rest of the code base remains both
model‑ and vendor‑agnostic: swapping Gemini for another LLM backend would only
require rewriting this module (or providing an interface‑compatible drop‑in
replacement) without disturbing the parsing, serialisation, or CLI layers.
"""

import os
import sys
from dataclasses import dataclass
from google import genai
from typing import Iterator, List, Sequence
from pathlib import Path
from functools import cache

from .user_error import UserError
from .parser import Message, MessageRole


KEY_NAME = "MY_GEMINI_API_KEY"
MODEL="gemini-2.0-flash",


class NoAPIKey(UserError):
    def __init__(self) -> None:
        super().__init__("Expected $%s to be set.", [KEY_NAME], code=1)


@cache
def _get_client() -> genai.Client:
    try:
        MY_GEMINI_API_KEY: str = os.environ["MY_GEMINI_API_KEY"]
    except LookupError:
        raise NoAPIKey()

    return genai.Client(api_key=MY_GEMINI_API_KEY)

# ---------------------------------------------------------------------------
# Local structural types
# ---------------------------------------------------------------------------

Conversation = Sequence[Message]


def _to_gemini_payload(conv: Conversation) -> Iterator[genai.types.Content]:
    """Translate the internal conversation object into Gemini's payload.

    The mapping is intentionally explicit so that the compiler flags any future
    divergence between *Bogoslav*'s chat schema and Gemini's expectations.
    """

    role_map = {"user": "user", "assistant": "model", "system": "model"}  # last one handled elsewhere

    for role, text in conv:
        if role == "system":
            system_instruction = text  # keep **last** one we encounter
            continue  # not part of chat history under new API rules

        try:
            sdk_role = role_map[role]
        except KeyError as exc:
            raise ValueError(f"Unsupported role {role!r}.") from exc

        yield genai.types.Content(role=sdk_role, parts=[genai.types.Part(text=text)])


# ---------------------------------------------------------------------------
# Public façade
# ---------------------------------------------------------------------------

def communicate(conv: Conversation) -> Iterator[str]:  # noqa: D401 – imperative
    """Stream the assistant’s answer.

    Parameters
    ----------
    conv
        Chronologically ordered list of ``(role, text)`` pairs.  Roles may be
        ``"system"``, ``"user"`` or ``"assistant"``.

    Yields
    ------
    str
        Incremental snippets of the model’s response, in the order they are
        received from the network.

    Notes
    -----
    * Any *system* messages are collapsed: the **last** such entry becomes the
      request‑level `system_instruction`.  It is **not** forwarded as part of
      the normal chat history, because the Gemini SDK disallows the
      per‑message role value ``"system"``.
    * All remaining user/assistant messages are marshalled into
      :pyclass:`google.genai.types.Content` objects.
    """

    # 1. Extract the final system prompt (if present) and build the chat history
    system_instruction: str | None = None
    for role, text in conv:
        if role == "system":
            system_instruction = text  # keep **last** one we encounter
            continue  # not part of chat history under new API rules

    # 2. Kick off streaming generation
    contents = tuple(_to_gemini_payload(conv))
    client = _get_client()
    stream = client.models.generate_content_stream(
        model=MODEL,
        contents=contents,
        system_instruction=system_instruction,
    )

    # 3. Yield text parts as soon as they arrive
    for chunk in stream:  # each chunk = types.GenerateContentResponse
        for candidate in chunk.candidates:
            for part in candidate.content.parts:
                text = part.get("text", "")
                if text:
                    yield text
            break
