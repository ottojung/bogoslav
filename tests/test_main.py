
import pytest
from bogoslav.main import cli


def test_invocation():
    with pytest.raises(SystemExit):
        cli()
