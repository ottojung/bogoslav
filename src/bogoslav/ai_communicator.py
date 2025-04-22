
import os
import sys
from google import genai
from typing import Iterator
from pathlib import Path
from functools import cache

from .user_error import UserError


KEY_NAME = "MY_GEMINI_API_KEY"


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


def _communicate(contents: str) -> Iterator[genai.types.GenerateContentResponse]:

    yield from _get_client().models.generate_content_stream(
        model="gemini-2.0-flash",
        contents=f"""\
{contents}
""",
    )

    # for chunk in response:
    #     print(chunk.text, end="")
