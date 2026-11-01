"""Shared rule endings, safety caps, and seat-based game results."""

from dataclasses import dataclass
from typing import Any, Literal

from dominion.game.game_state import GAME_TURN_LIMIT

Result = Literal["win", "loss", "tie", "truncated"]


def winning_seats(players) -> tuple[int, ...]:
    """Rank points first, then fewer turns; preserve every fully tied seat."""
    ranks = [(p.get_victory_points(), -p.turns_taken) for p in players]
    best = max(ranks)
    return tuple(i for i, rank in enumerate(ranks) if rank == best)


def episode_status(state, max_turns=GAME_TURN_LIMIT) -> tuple[bool, bool]:
    """Return (naturally terminated, truncated), completing Fleet before either."""
    if max_turns < 1:
        raise ValueError("max_turns must be positive")
    ended = state.is_game_over()
    natural = ended and (state._normal_game_end_reached() or state.fleet_extra_round_active)
    if natural:
        return True, False
    capped = (not state.fleet_extra_round_active and state.phase == "start"
              and state.turn_number > min(max_turns, GAME_TURN_LIMIT))
    return ended and not capped, capped


@dataclass(frozen=True)
class GameOutcome:
    """Immutable results by starting seat; a safety cap has no winners."""

    scores: tuple[int, ...]
    turns_taken: tuple[int, ...]
    winners: tuple[int, ...]
    termination_reason: str

    @property
    def truncated(self) -> bool:
        return self.termination_reason == "turn_limit"

    def result_for(self, seat: int) -> Result:
        if not 0 <= seat < len(self.scores):
            raise IndexError(seat)
        if self.truncated:
            return "truncated"
        if seat not in self.winners:
            return "loss"
        return "tie" if len(self.winners) > 1 else "win"

    def win_share(self, seat: int) -> float:
        result = self.result_for(seat)
        return 1 / len(self.winners) if result in ("win", "tie") else 0.0

    def reward(self, seat: int) -> float:
        return {"win": 1.0, "loss": -1.0, "tie": 0.0, "truncated": 0.0}[self.result_for(seat)]

    @classmethod
    def from_state(cls, state, max_turns=GAME_TURN_LIMIT):
        terminated, truncated = episode_status(state, max_turns)
        if not (terminated or truncated):
            raise ValueError("Cannot score an unfinished game")
        if truncated:
            reason = "turn_limit"
        elif state.fleet_extra_round_active:
            reason = "fleet"
        elif state.supply.get("Province", 0) == 0:
            reason = "province_depleted"
        elif "Colony" in state.supply and state.supply["Colony"] == 0:
            reason = "colony_depleted"
        else:
            reason = "three_piles_depleted"
        return cls(
            tuple(p.get_victory_points() for p in state.players),
            tuple(p.turns_taken for p in state.players),
            () if truncated else winning_seats(state.players),
            reason,
        )


@dataclass(frozen=True)
class PlayedGame:
    """A battle result with AI accessors and legacy four-value unpacking.

    Legacy ``winner`` is None for ties and caps. New scoring code should use
    ``win_share`` and ``result_for`` so neither can become a fabricated loss.
    """

    outcome: GameOutcome
    players: tuple[Any, ...]
    log_path: str | None
    turns: int

    def seat(self, ai) -> int:
        return next(i for i, player in enumerate(self.players) if player is ai)

    def win_share(self, ai) -> float:
        return self.outcome.win_share(self.seat(ai))

    def result_for(self, ai) -> Result:
        return self.outcome.result_for(self.seat(ai))

    @property
    def winner(self):
        return self.players[self.outcome.winners[0]] if len(self.outcome.winners) == 1 else None

    @property
    def scores(self) -> dict[str, int]:
        return {ai.name: score for ai, score in zip(self.players, self.outcome.scores)}

    def __iter__(self):
        yield self.winner
        yield self.scores
        yield self.log_path
        yield self.turns


@dataclass
class OutcomeCounts:
    """Count outcomes without inferring losses from games minus wins."""

    wins: int = 0
    losses: int = 0
    ties: int = 0
    truncated: int = 0

    def record(self, result: Result) -> None:
        field = {"win": "wins", "loss": "losses", "tie": "ties", "truncated": "truncated"}[result]
        setattr(self, field, getattr(self, field) + 1)

    @property
    def games(self) -> int:
        return self.wins + self.losses + self.ties + self.truncated

    @property
    def completed(self) -> int:
        return self.games - self.truncated

    @property
    def win_share(self) -> float:
        return self.wins + self.ties / 2

    @property
    def score_rate(self) -> float:
        return self.win_share / self.games * 100 if self.games else 0.0

    def to_dict(self) -> dict:
        return {"wins": self.wins, "losses": self.losses, "ties": self.ties,
                "truncated": self.truncated, "games": self.games}
