
import pytest
from bogoslav.main import cli


def test_invocation() -> None:
    with pytest.raises(SystemExit):
        cli()
