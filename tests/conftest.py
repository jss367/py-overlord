import os
import random

import pytest


@pytest.fixture
def seed_rng(request):
    seed = getattr(request, "param", None)
    if seed is None:
        seed = int(os.environ.get("PY_OVERLORD_TEST_SEED", "1729"))
    random.seed(seed)
    yield seed
