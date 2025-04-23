
from pathlib import Path
from .parser import parse
from .ai_communicator import communicate
from .logger import logger
from .user_error import UserError


def process_modification(work_file: Path) -> None:
    current_text = work_file.read_text()
    blocks = parse(current_text)
    messages = blocks[0].messages
    for chunk in communicate(messages):
        print(chunk, end='')
