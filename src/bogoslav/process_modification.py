
from pathlib import Path
from dataclasses import replace
from .parser import parse, Message
from .unparser import serialize_ai_blocks
from .ai_communicator import communicate
from .logger import logger
# from .user_error import UserError


def process_modification(work_file: Path) -> None:
    current_text = work_file.read_text()
    blocks = parse(current_text)

    first_block = blocks[0]
    messages = first_block.messages

    text = ''
    for chunk in communicate(messages):
        text += chunk
        # print(chunk, end='')

    logger.debug("Assistant responded with a message of length %s.", len(text))

    new_message = Message(role="assistant", text=text)
    new_messages = list(messages)
    new_messages.append(new_message)
    first_block = replace(first_block, messages=new_messages)
    blocks = (first_block,) + tuple(blocks[:-1])
    work_file.write_text(serialize_ai_blocks(blocks))
    logger.debug("Updated blocks with a new message.")
