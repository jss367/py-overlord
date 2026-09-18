"""Retirement metadata lives on factories, alongside the strategy implementation."""

from dataclasses import dataclass
from typing import Callable

from dominion.strategy.enhanced_strategy import EnhancedStrategy


@dataclass(frozen=True)
class Retirement:
    replacement: str
    reason: str
    display_name: str | None = None


def retired_strategy(*, replacement: str, reason: str, display_name: str | None = None):
    """Hide a factory from default lists without changing explicit lookup or imports."""
    def decorate(factory: Callable[[], EnhancedStrategy]):
        factory.retirement = Retirement(replacement=replacement, reason=reason, display_name=display_name)
        return factory
    return decorate
