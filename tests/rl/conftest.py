import pytest

collect_ignore_glob = []

try:
    import gymnasium  # noqa: F401
    import torch  # noqa: F401
except ImportError:
    collect_ignore_glob = ["test_*.py"]
