
import time
from pathlib import Path
from typing import NoReturn
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent, EVENT_TYPE_MODIFIED
from .user_error import UserError
from .logger import logger
from .process_modification import process_modification


class CannotWriteToWorkFile(UserError):
    def __init__(self, path: Path) -> None:
        self.path = path
        self._init("Cannot write to work file %r.", str(path))


class MyHandler(FileSystemEventHandler):
    def __init__(self, work_file: Path) -> None:
        self.work_file = work_file
        self.target = str(self.work_file)

    def on_any_event(self, event: FileSystemEvent) -> None:
        if event.event_type == EVENT_TYPE_MODIFIED:
            if event.src_path == self.target:
                logger.debug("File %r modified.", self.target)
                process_modification(self.work_file)


def main_loop(work_file: Path) -> None:
    event_handler = MyHandler(work_file)
    observer = Observer()
    observer.schedule(event_handler, str(work_file))
    observer.start()

    logger.info(f"Watching %r... Press Ctrl+C to stop.", str(work_file))

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()

    observer.join()


def main_typed(work_file: Path) -> None:
    try:
        writer = work_file.open("a")
        logger.info("Opened existing file at %r.", str(work_file))
    except:  # noqa
        try:
            writer = work_file.open("w")
            logger.info("Created new file at %r.", str(work_file))
        except BaseException as ex:
            raise CannotWriteToWorkFile(work_file) from ex

    main_loop(work_file)
