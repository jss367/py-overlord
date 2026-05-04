from .base_prophecy import Prophecy

# Side-effect imports register each subclass with PROPHECY_TYPES via the
# @register decorator.
from . import (  # noqa: F401
    approaching_army,
    biding_time,
    bureaucracy,
    divine_wind,
    enlightenment,
    flourishing_trade,
    good_harvest,
    great_leader,
    growth,
    harsh_winter,
    kind_emperor,
    panic,
    progress,
    rapid_expansion,
    sickness,
)
from .registry import PROPHECY_TYPES, get_prophecy

__all__ = ['Prophecy', 'PROPHECY_TYPES', 'get_prophecy']

