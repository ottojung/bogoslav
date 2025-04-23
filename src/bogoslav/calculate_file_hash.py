
import zlib
import mmap
from pathlib import Path
from typing import NewType


Checksum = NewType("Checksum", int)


def calculate_file_hash(path: Path) -> Checksum:
    with path.open('rb') as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        ret = zlib.crc32(mm) & 0xFFFFFFFF
        return Checksum(ret)
