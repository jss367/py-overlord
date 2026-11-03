"""Hard accounting for sequential simulation stages sharing one allowance."""

from dataclasses import dataclass, field


class SimulationBudgetExceeded(RuntimeError):
    """A complete evaluation would exceed the remaining game allowance."""


@dataclass
class SimulationBudget:
    limit: int
    spent: dict[str, int] = field(default_factory=dict, init=False)

    def __post_init__(self):
        if type(self.limit) is not int or self.limit < 0:
            raise ValueError("Simulation budget must be a nonnegative integer")

    @property
    def completed(self):
        return sum(self.spent.values())

    @property
    def remaining(self):
        return self.limit - self.completed

    def require(self, games: int):
        if type(games) is not int or games < 0:
            raise ValueError("Requested games must be a nonnegative integer")
        if games > self.remaining:
            raise SimulationBudgetExceeded(
                f"Evaluation needs {games} games; only {self.remaining} remain"
            )

    def consume(self, games: int, phase: str):
        self.require(games)
        self.spent[phase] = self.spent.get(phase, 0) + games

    def snapshot(self):
        return {"limit": self.limit, "completed": self.completed,
                "remaining": self.remaining, "phases": dict(self.spent)}
