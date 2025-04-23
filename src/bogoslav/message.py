
from dataclasses import dataclass
from typing import Literal


MessageRole = Literal["user", "assistant", "system"]
MessageText = str


@dataclass(frozen=True)
class Message:
    role: MessageRole
    text: MessageText
