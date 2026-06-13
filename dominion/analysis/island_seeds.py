"""Board-derived island seeds for the island-model evolution pipeline.

The island model runs one GeneticTrainer per *seed* — each seed a distinct
theory of the kingdom — so the run escapes shared local optima. The original
pipeline hardcoded six hand-written Lisbon strategies, which meant a new
board required writing six seed strategies before islands could run at all.

This module derives the island roster from the board itself:

1. **Library reuse** — existing strategies whose referenced cards overlap
   this kingdom (:func:`find_compatible_strategies`), each as its own island.
2. **Trick seeds** — one island per mechanical interaction surfaced by the
   trick scanner (:func:`build_seed_genomes`).
3. **Big Money** — the archetype baseline island, always available.
4. **Random islands** — unseeded lineages (the structured-genome random init
   produces coherent menus, so these are real hypotheses, not noise) filling
   the roster up to ``max_islands``.

Island specs are plain dataclasses of strings: the pipeline runs each island
in a spawned subprocess, and strategy objects (lambda conditions) cannot be
serialized across that boundary. Workers rebuild the actual seed strategy
from the spec via :func:`resolve_island_seed`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from dominion.analysis.seed_genomes import build_seed_genomes
from dominion.analysis.strategy_library import find_compatible_strategies
from dominion.boards.loader import BoardConfig
from dominion.strategy.enhanced_strategy import EnhancedStrategy


@dataclass(frozen=True)
class IslandSpec:
    """A subprocess-safe description of one island's starting point.

    ``kind`` is one of ``"loader"`` (a registered strategy name), ``"library"``
    (a compatible strategy from the reuse library, keyed by entry name),
    ``"trick"`` (an index into ``build_seed_genomes(board)``), or ``"random"``
    (no seed — the island starts from random structured menus).
    """

    kind: str
    key: str
    name: str


def derive_island_specs(
    board: BoardConfig,
    max_islands: int = 6,
    reuse_top_k: int = 3,
    reuse_min_overlap: int = 2,
) -> list[IslandSpec]:
    """Derive an island roster for ``board``.

    Library and trick islands come first (they carry the most board-specific
    information), then the Big Money archetype, then random islands pad the
    roster to ``max_islands``. If the informed islands alone exceed
    ``max_islands``, the roster is truncated — library entries are ranked by
    overlap score and trick seeds follow scanner order, so the cut keeps the
    strongest candidates.
    """

    specs: list[IslandSpec] = []

    for entry in find_compatible_strategies(
        board.kingdom_cards, top_k=reuse_top_k, min_overlap=reuse_min_overlap
    ):
        specs.append(IslandSpec("library", entry.name, f"Reuse {entry.name}"))

    for index, (name, _strategy) in enumerate(build_seed_genomes(board)):
        specs.append(IslandSpec("trick", str(index), name))

    specs.append(IslandSpec("loader", "Big Money", "Big Money Island"))

    random_index = 0
    while len(specs) < max_islands:
        random_index += 1
        specs.append(IslandSpec("random", str(random_index), f"Random Island {random_index}"))

    return specs[:max_islands]


def resolve_island_seed(
    spec: IslandSpec,
    board: BoardConfig,
    strategy_loader,
) -> Optional[EnhancedStrategy]:
    """Rebuild the seed strategy for ``spec`` (inside the island subprocess).

    Returns ``None`` for ``"random"`` islands — the caller simply skips seed
    injection and lets the trainer start from random structured menus.
    Raises ``ValueError`` if a named seed can no longer be found, so a
    misconfigured island fails loudly instead of silently devolving into a
    random island with a misleading name.
    """

    if spec.kind == "random":
        return None

    if spec.kind == "loader":
        strategy = strategy_loader.get_strategy(spec.key)
        if strategy is None:
            raise ValueError(f"Island seed not found in strategy loader: {spec.key!r}")
        return strategy

    if spec.kind == "library":
        entries = find_compatible_strategies(
            board.kingdom_cards, top_k=10, min_overlap=1
        )
        for entry in entries:
            if entry.name == spec.key:
                return entry.factory()
        raise ValueError(f"Island seed not found in strategy library: {spec.key!r}")

    if spec.kind == "trick":
        seeds = build_seed_genomes(board)
        index = int(spec.key)
        if index >= len(seeds):
            raise ValueError(
                f"Trick seed index {index} out of range ({len(seeds)} seeds on this board)"
            )
        return seeds[index][1]

    raise ValueError(f"Unknown island spec kind: {spec.kind!r}")
