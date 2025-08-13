try:
    from __main__ import __version__
except ImportError:
    __version__ = "0.1.0"


def test_version():
    assert __version__ == "0.1.0"
