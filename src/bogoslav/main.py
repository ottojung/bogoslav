
import argparse
import sys
from typing import Sequence
from pathlib import Path
from .mainwrap import mainwrap
from .parsecli import parse_cli
from .main_typed import main_typed


def cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--work-file", type=Path, required=True, help="The working file.")
    return parser


def main(argv: Sequence[str]) -> int:
    parser = cli_parser()
    args = parse_cli(parser, argv)
    main_typed(args.work_file)
    return 0


def cli() -> None:
    mainwrap(main)


if __name__ == "__main__": cli()  # noqa
