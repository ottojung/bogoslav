
from pathlib import Path
from dataclasses import replace
from .parser import parse, Message
from .unparser import serialize_ai_blocks
from .ai_communicator import communicate
from .logger import logger
# from .user_error import UserError


EMPTY_USER_MESSAGE = Message(role="user", text="")


def process_modification(work_file: Path) -> None:
    current_text = work_file.read_text()
    blocks = parse(current_text)

    if not blocks:
        return

    first_block = blocks[0]
    messages = first_block.messages

    if not messages:
        return

    if messages[-1].role == "user" and not messages[-1].text.strip():
        return

    text = ''
    for chunk in communicate(messages):
        text += chunk
        # print(chunk, end='')

    logger.debug("Assistant responded with a message of length %s.", len(text))

    new_messages = list(messages)
    new_messages.append(Message(role="assistant", text=text))
    new_messages.append(EMPTY_USER_MESSAGE)

    first_block = replace(first_block, messages=new_messages)
    blocks = (first_block,) + tuple(blocks[:-1])
    work_file.write_text(serialize_ai_blocks(blocks))
    logger.debug("Updated blocks with a new message.")
