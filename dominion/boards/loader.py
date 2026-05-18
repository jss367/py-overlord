"""Utilities for parsing Dominion board definition files."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re


@dataclass(slots=True)
class BoardConfig:
    """Structured representation of a board definition."""

    kingdom_cards: list[str]
    events: list[str] = field(default_factory=list)
    projects: list[str] = field(default_factory=list)
    ways: list[str] = field(default_factory=list)
    landmarks: list[str] = field(default_factory=list)
    allies: list[str] = field(default_factory=list)
    traits: dict[str, str] = field(default_factory=dict)  # {card_name: trait_name}


def _normalise_entry(entry: str) -> str:
    """Return a stripped entry or raise if empty."""

    value = entry.strip()
    if not value:
        raise ValueError("Board entry cannot be empty")
    return value


def _parse_trait_value(value: str) -> tuple[str, str]:
    """Return ``(trait_name, card_name)`` for supported Trait line formats."""

    match = re.fullmatch(r"(.+?)\s*\((.+)\)", value)
    if match:
        return match.group(1).strip(), match.group(2).strip()

    match = re.fullmatch(r"(.+?)\s+-\s+(.+)", value)
    if match:
        return match.group(1).strip(), match.group(2).strip()

    return "", ""


def _parse_landmark_value(value: str) -> str:
    """Return a normalized Landmark entry.

    Obelisk has a setup-time chosen pile. Board files can express that as
    ``Landmark: Obelisk (Temple)`` or ``Landmark: Obelisk - Temple``; the
    registry understands the parenthetical form.
    """

    landmark_name, chosen_pile = _parse_trait_value(value)
    if landmark_name and chosen_pile and landmark_name == "Obelisk":
        return f"{landmark_name} ({chosen_pile})"
    return value


def _parse_special_line(line: str, config: BoardConfig) -> bool:
    """Attempt to parse a special prefix line like ``Way: Foo``.

    Returns ``True`` when the line was handled.
    """

    prefix, _, remainder = line.partition(":")
    if not remainder:
        return False

    value = _normalise_entry(remainder)
    key = prefix.strip().lower()

    if key == "event":
        config.events.append(value)
    elif key == "project":
        config.projects.append(value)
    elif key == "way":
        config.ways.append(value)
    elif key.startswith("way of the"):
        # ``Way of the Mouse: Native Village`` becomes
        # ``Way of the Mouse (Native Village)`` so the registry's
        # parametric-Way regex resolves the target.
        config.ways.append(f"{prefix.strip()} ({value})")
    elif key == "landmark":
        config.landmarks.append(_parse_landmark_value(value))
    elif key == "ally":
        config.allies.append(value)
    elif key == "trait":
        # Formats: "Trait: TraitName - CardName" or "Trait: TraitName (CardName)".
        trait_name, card_name = _parse_trait_value(value)
        if trait_name and card_name:
            config.traits[card_name] = trait_name
    else:
        return False

    return True


def load_board(path: Path | str) -> BoardConfig:
    """Parse a Dominion board text file into a :class:`BoardConfig`.

    Lines without a ``":"`` separator are treated as kingdom piles. Lines
    beginning with recognised prefixes (``Event:``, ``Project:``, ``Way:``,
    ``Landmark:``, ``Ally:``) populate the corresponding collections.
    Comments (``#``) and blank lines are ignored.
    """

    board_path = Path(path)
    if not board_path.exists():
        raise FileNotFoundError(f"Board file not found: {board_path}")

    kingdom_cards: list[str] = []
    config = BoardConfig(kingdom_cards)

    for raw_line in board_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        if _parse_special_line(line, config):
            continue

        kingdom_cards.append(_normalise_entry(line))

    if not kingdom_cards:
        raise ValueError(f"Board file {board_path} does not list any kingdom cards")

    return config
