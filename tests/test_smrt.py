"""Common SMRT tests."""

from smrt import __version__


def test_version():
    """Make sure that version is correct."""
    assert __version__ == '0.0.1'
