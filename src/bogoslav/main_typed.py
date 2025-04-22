
from pathlib import Path
from .user_error import UserError
from .parser import parse
from .ai_communicator import communicate
from .logger import logger


class CannotWriteToWorkFile(UserError):
    def __init__(self, path: Path) -> None:
        self.path = path
        super().__init__(fmt="Cannot write to work file %r.", fmt_args=[str(path)], code=1)


def main_typed(work_file: Path) -> None:
    try:
        writer = work_file.open("r")
        logger.info("Opened existing file at %r.", str(work_file))
    except:  # noqa
        try:
            writer = work_file.open("w")
            logger.info("Created new file at %r.", str(work_file))
        except BaseException as ex:
            raise CannotWriteToWorkFile(work_file) from ex

    current_text = work_file.read_text()
    blocks = parse(current_text)
    messages = blocks[0].messages
    for chunk in communicate(messages):
        print(chunk, end='')
