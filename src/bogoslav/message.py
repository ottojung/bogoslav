
from dataclasses import dataclass
from typing import Union


MessageText = str


@dataclass(frozen=True)
class UserMessage:
    text: MessageText


@dataclass(frozen=True)
class AssistantMessage:
    text: MessageText


@dataclass(frozen=True)
class SystemMessage:
    text: MessageText


Message = Union[UserMessage, AssistantMessage, SystemMessage]
