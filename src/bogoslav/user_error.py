
from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class UserError(BaseException):
    fmt: str
    fmt_args: Sequence[object]
    code: int

    def _init(self, fmt: str, *fmt_args: object, code: int = 1) -> None:
        UserError.__init__(self, fmt=fmt, fmt_args=fmt_args, code=code)
