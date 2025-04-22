
from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class UserError(BaseException):
    fmt: str
    fmt_args: Sequence[object]
    code: int
