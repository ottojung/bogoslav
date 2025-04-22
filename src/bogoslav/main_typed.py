
from pathlib import Path
from .user_error import UserError


class CannotWriteToWorkFile(UserError):
    def __init__(self, path: Path) -> None:
        self.path = path
        super().__init__(fmt="Cannot write to work file %r.", fmt_args=[str(path)], code=1)


def main_typed(work_file: Path) -> None:
    try:
        writer = work_file.open("w")
    except BaseException as ex:
        raise CannotWriteToWorkFile(work_file) from ex

    raise NotImplementedError()
