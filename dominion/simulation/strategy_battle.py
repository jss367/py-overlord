import argparse
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from logging import getLogger
from pathlib import Path
from typing import Any, Optional

from dominion.ai.genetic_ai import GeneticAI
from dominion.allies.registry import ALLY_TYPES, get_ally
from dominion.boards.loader import BoardConfig, load_board
from dominion.cards.registry import CARD_ALIASES, CARD_TYPES, get_card
from dominion.events.registry import EVENT_TYPES, get_event
from dominion.game.game_state import GameState
from dominion.projects.registry import PROJECT_TYPES, get_project
from dominion.reporting.html_report import generate_html_report
from dominion.simulation.game_logger import GameLogger
from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule
from dominion.strategy.strategy_loader import StrategyLoader
from dominion.traits import apply_trait
from dominion.ways.registry import WAY_TYPES, get_way

logger = getLogger(__name__)

_WAY_PARAM_RE = re.compile(r"\s*\(.+\)$")

DEFAULT_KINGDOM_CARDS = [
    "Village",
    "Smithy",
    "Market",
    "Festival",
    "Laboratory",
    "Mine",
    "Witch",
    "Moat",
    "Workshop",
    "Chapel",
]

# Cards that should not be included in the kingdom supply when extracting
# names from strategies. These are part of the base supply or starting cards
# and are automatically handled by ``GameState.setup_supply``.
BASIC_CARDS = {
    "Copper",
    "Silver",
    "Gold",
    "Estate",
    "Duchy",
    "Province",
    "Curse",
    # Shelters are never part of the normal supply
    "Hovel",
    "Necropolis",
    "Overgrown Estate",
}


@dataclass(frozen=True)
class StrategyBoardReferences:
    kingdom_cards: list[str]
    events: list[str]
    projects: list[str]
    ways: list[str]
    allies: list[str]


def canonical_way_name(way: str) -> str:
    """Return the runtime Way.name for a board or strategy Way reference."""
    return _WAY_PARAM_RE.sub("", way)


# Set up module-level logger
logger = logging.getLogger(__name__)


class StrategyBattle:
    """System for running battles between strategies."""

    def __init__(
        self,
        kingdom_cards: Optional[list[str]] = None,
        log_folder: str = "battle_logs",
        use_shelters: bool = False,
        board_config: Optional[BoardConfig] = None,
        *,
        verbose: bool = False,
        log_frequency: int = 10,
    ):
        # ``kingdom_cards`` allows explicitly providing the supply. If omitted
        # the supply will be dynamically determined from the strategies used in
        # each battle.
        self.board_config = board_config
        if board_config and kingdom_cards and board_config.kingdom_cards != kingdom_cards:
            raise ValueError("kingdom_cards and board_config.kingdom_cards must match when both provided")

        self.kingdom_cards = board_config.kingdom_cards if board_config else kingdom_cards
        self.logger = GameLogger(log_folder=log_folder, log_frequency=log_frequency)
        self.strategy_loader = StrategyLoader()  # Now automatically loads all strategies
        self.use_shelters = use_shelters
        self.verbose = verbose

    def _extract_cards_from_strategy(self, strat: EnhancedStrategy) -> set[str]:
        """Return all names referenced by a strategy's priority lists."""
        references: set[str] = set()
        for priority_list in [
            strat.gain_priority,
            strat.action_priority,
            strat.trash_priority,
            strat.treasure_priority,
        ]:
            for rule in priority_list:
                if isinstance(rule, PriorityRule):
                    references.add(rule.card_name)

        for rule in getattr(strat, "way_policy", []) or []:
            card_name = getattr(rule, "card_name", None)
            way_name = getattr(rule, "way_name", None)
            if card_name:
                references.add(card_name)
            if way_name:
                references.add(way_name)

        return references

    @staticmethod
    def _is_card_reference(name: str) -> bool:
        return CARD_ALIASES.get(name, name) in CARD_TYPES

    @staticmethod
    def _is_way_reference(name: str) -> bool:
        if name in WAY_TYPES:
            return True

        match = re.match(r"^(Way of the Mouse)\s*\((.+)\)$", name)
        return bool(match and match.group(1) in WAY_TYPES)

    def _split_board_references(self, names: set[str]) -> StrategyBoardReferences:
        """Split strategy references into cards and supported landscapes."""

        kingdom_cards: list[str] = []
        events: list[str] = []
        projects: list[str] = []
        ways: list[str] = []
        allies: list[str] = []

        for name in sorted(names):
            if name in BASIC_CARDS:
                continue

            if self._is_card_reference(name):
                kingdom_cards.append(name)
            elif name in EVENT_TYPES:
                events.append(name)
            elif name in PROJECT_TYPES:
                projects.append(name)
            elif self._is_way_reference(name):
                ways.append(name)
            elif name in ALLY_TYPES:
                allies.append(name)
            else:
                # Preserve the old failure mode for typos and unsupported
                # references: board preparation will raise Unknown card.
                kingdom_cards.append(name)

        return StrategyBoardReferences(kingdom_cards, events, projects, ways, allies)

    def _determine_board_references(
        self, strat1: EnhancedStrategy, strat2: EnhancedStrategy
    ) -> StrategyBoardReferences:
        """Compute cards and landscapes from both strategies if not explicitly set."""
        if self.kingdom_cards is not None:
            return StrategyBoardReferences(self.kingdom_cards, [], [], [], [])

        all_names = self._extract_cards_from_strategy(strat1) | self._extract_cards_from_strategy(strat2)
        return self._split_board_references(all_names)

    def _determine_kingdom_cards(self, strat1: EnhancedStrategy, strat2: EnhancedStrategy) -> list[str]:
        """Compute kingdom cards from both strategies if not explicitly set."""
        return self._determine_board_references(strat1, strat2).kingdom_cards

    def _prepare_board_components(
        self,
        kingdom_card_names: list[str],
        event_names: Optional[list[str]] = None,
        project_names: Optional[list[str]] = None,
        way_names: Optional[list[str]] = None,
        ally_names: Optional[list[str]] = None,
    ):
        """Instantiate cards and landscape components for a game."""

        kingdom_cards = [get_card(name) for name in kingdom_card_names]

        if self.board_config:
            event_names = self.board_config.events
            project_names = self.board_config.projects
            way_names = self.board_config.ways
            ally_names = self.board_config.allies

        events = [get_event(name) for name in event_names or []]
        projects = [get_project(name) for name in project_names or []]
        ways = [get_way(name) for name in way_names or []]
        allies = [get_ally(name) for name in ally_names or []]

        return kingdom_cards, events, projects, ways, allies

    def _apply_board_traits(self, game_state: GameState) -> None:
        """Apply Plunder traits declared by the loaded board config."""

        if not self.board_config:
            return

        for card_name, trait in self.board_config.traits.items():
            apply_trait(game_state, trait, card_name)

    @staticmethod
    def _empty_decision_firings(strategy_name: str) -> dict[str, Any]:
        return {
            "strategy_name": strategy_name,
            "choose_way": {},
            "choose_gain_overrides": {
                "total": 0,
                "by_selection": {},
            },
        }

    @staticmethod
    def _increment_nested_count(counts: dict[str, Any], first: str, second: str) -> None:
        counts.setdefault(first, {})
        counts[first][second] = counts[first].get(second, 0) + 1

    @staticmethod
    def _increment_count(counts: dict[str, int], key: str) -> None:
        counts[key] = counts.get(key, 0) + 1

    @staticmethod
    def _merge_decision_firings(total: dict[str, Any], game: dict[str, Any]) -> None:
        for card_name, ways in game["choose_way"].items():
            for way_name, count in ways.items():
                total["choose_way"].setdefault(card_name, {})
                total["choose_way"][card_name][way_name] = (
                    total["choose_way"][card_name].get(way_name, 0) + count
                )

        total_gain = total["choose_gain_overrides"]
        game_gain = game["choose_gain_overrides"]
        total_gain["total"] += game_gain["total"]
        for selection, count in game_gain["by_selection"].items():
            total_gain["by_selection"][selection] = total_gain["by_selection"].get(selection, 0) + count

    @staticmethod
    def _top_gain_priority_choice(strategy: EnhancedStrategy, state, player, choices) -> Optional[Any]:
        if not choices:
            return None
        choose_from_priority = getattr(strategy, "_choose_from_priority", None)
        if choose_from_priority is None:
            return None
        try:
            return choose_from_priority(strategy.gain_priority, choices, state, player)
        except Exception:
            return None

    def _instrument_ai_decisions(self, ai: GeneticAI, stats: dict[str, Any]) -> None:
        original_choose_way = ai.choose_way
        original_choose_buy = ai.choose_buy

        def tracked_choose_way(state, card, ways):
            way = original_choose_way(state, card, ways)
            if way is not None:
                self._increment_nested_count(
                    stats["choose_way"],
                    getattr(card, "name", str(card)),
                    getattr(way, "name", str(way)),
                )
            return way

        def tracked_choose_buy(state, choices):
            valid_choices = [c for c in choices if c is not None]
            player = getattr(state, "current_player", None)
            top_priority = self._top_gain_priority_choice(ai.strategy, state, player, valid_choices)
            selected = original_choose_buy(state, choices)
            if (
                selected is not None
                and top_priority is not None
                and getattr(selected, "name", None) != getattr(top_priority, "name", None)
            ):
                selected_name = getattr(selected, "name", str(selected))
                top_name = getattr(top_priority, "name", str(top_priority))
                stats["choose_gain_overrides"]["total"] += 1
                self._increment_count(
                    stats["choose_gain_overrides"]["by_selection"],
                    f"{selected_name} over {top_name}",
                )
            return selected

        ai.choose_way = tracked_choose_way
        ai.choose_buy = tracked_choose_buy

    def run_battle(self, strategy1_name: str, strategy2_name: str, num_games: int = 100) -> dict[str, Any]:
        """Run multiple games between two strategies"""
        # Get strategies from loader
        strategy1 = self.strategy_loader.get_strategy(strategy1_name)
        strategy2 = self.strategy_loader.get_strategy(strategy2_name)

        missing = []
        if not strategy1:
            missing.append(strategy1_name)
        if not strategy2:
            missing.append(strategy2_name)
        if missing:
            logger.warning("Could not find strategies: %s", ', '.join(missing))
            raise ValueError(f"Could not find strategies: {', '.join(missing)}")

        # Initialize results tracking
        results = {
            "strategy1_name": strategy1_name,
            "strategy2_name": strategy2_name,
            "strategy1_wins": 0,
            "strategy2_wins": 0,
            "strategy1_total_score": 0,
            "strategy2_total_score": 0,
            "games_played": num_games,
            "detailed_results": [],
            "decision_firings": {
                "strategy1": self._empty_decision_firings(strategy1_name),
                "strategy2": self._empty_decision_firings(strategy2_name),
            },
        }

        # Run the games
        if self.verbose:
            logger.info("\nRunning %d games between:", num_games)
            logger.info("Strategy 1: %s", strategy1_name)
            logger.info("Strategy 2: %s\n", strategy2_name)

        board_references = self._determine_board_references(strategy1, strategy2)
        kingdom_card_names = board_references.kingdom_cards
        if self.verbose:
            logger.info("Using kingdom cards: %s", ", ".join(kingdom_card_names))
            if not self.board_config:
                logger.info(
                    "Using landscapes: %s",
                    ", ".join(
                        filter(
                            None,
                            [
                                f"Ways={len(board_references.ways)}" if board_references.ways else "",
                                f"Projects={len(board_references.projects)}" if board_references.projects else "",
                                f"Events={len(board_references.events)}" if board_references.events else "",
                                f"Allies={len(board_references.allies)}" if board_references.allies else "",
                            ],
                        ),
                    )
                    or "(no landscapes)",
                )

        if self.board_config and self.verbose:
            logger.info(
                "Board configuration: %s",
                ", ".join(
                    filter(
                        None,
                        [
                            f"Ways={len(self.board_config.ways)}" if self.board_config.ways else "",
                            f"Projects={len(self.board_config.projects)}" if self.board_config.projects else "",
                            f"Events={len(self.board_config.events)}" if self.board_config.events else "",
                        ],
                    ),
                )
                or "(no landscapes)",
            )

        for game_num in range(num_games):
            if self.verbose:
                logger.info("Playing game %d/%d...", game_num + 1, num_games)

            # Create fresh AIs for each game using new strategy instances
            ai1 = GeneticAI(strategy1)
            ai2 = GeneticAI(strategy2)
            game_decision_firings = {
                "strategy1": self._empty_decision_firings(strategy1_name),
                "strategy2": self._empty_decision_firings(strategy2_name),
            }
            decision_stats_by_ai = {
                ai1: game_decision_firings["strategy1"],
                ai2: game_decision_firings["strategy2"],
            }

            # Alternate who goes first
            if game_num % 2 == 0:
                winner, scores, log_path, turns = self.run_game(
                    ai1,
                    ai2,
                    kingdom_card_names,
                    decision_stats_by_ai=decision_stats_by_ai,
                    events=board_references.events,
                    projects=board_references.projects,
                    ways=board_references.ways,
                    allies=board_references.allies,
                )
            else:
                winner, scores, log_path, turns = self.run_game(
                    ai2,
                    ai1,
                    kingdom_card_names,
                    decision_stats_by_ai=decision_stats_by_ai,
                    events=board_references.events,
                    projects=board_references.projects,
                    ways=board_references.ways,
                    allies=board_references.allies,
                )

            # Record results
            game_result = {
                "game_number": game_num + 1,
                "winner": strategy1_name if winner == ai1 else strategy2_name,
                "strategy1_score": scores[ai1.name],
                "strategy2_score": scores[ai2.name],
                "margin": abs(scores[ai1.name] - scores[ai2.name]),
                "turns": turns,
                "log_path": log_path,
                "decision_firings": game_decision_firings,
            }
            results["detailed_results"].append(game_result)
            self._merge_decision_firings(
                results["decision_firings"]["strategy1"],
                game_decision_firings["strategy1"],
            )
            self._merge_decision_firings(
                results["decision_firings"]["strategy2"],
                game_decision_firings["strategy2"],
            )

            if winner == ai1:
                results["strategy1_wins"] += 1
            else:
                results["strategy2_wins"] += 1

            results["strategy1_total_score"] += scores[ai1.name]
            results["strategy2_total_score"] += scores[ai2.name]

        # Calculate final statistics
        results["strategy1_win_rate"] = results["strategy1_wins"] / num_games * 100
        results["strategy2_win_rate"] = results["strategy2_wins"] / num_games * 100
        results["strategy1_avg_score"] = results["strategy1_total_score"] / num_games
        results["strategy2_avg_score"] = results["strategy2_total_score"] / num_games

        results["log_paths"] = list(self.logger.game_logs)

        return results

    def run_game(
        self,
        ai1: GeneticAI,
        ai2: GeneticAI,
        kingdom_card_names: list[str],
        *,
        decision_stats_by_ai: Optional[dict[GeneticAI, dict[str, Any]]] = None,
        events: Optional[list[str]] = None,
        projects: Optional[list[str]] = None,
        ways: Optional[list[str]] = None,
        allies: Optional[list[str]] = None,
    ) -> tuple[GeneticAI, dict[str, int], Optional[str], int]:
        """Run a single game between two AIs. TODO: This shouldn't be within this class."""
        if decision_stats_by_ai:
            for ai, stats in decision_stats_by_ai.items():
                self._instrument_ai_decisions(ai, stats)

        # Start game logging with actual AI objects for better descriptions
        self.logger.start_game([ai1, ai2])

        # Set up game state and attach logger for structured logging
        game_state = GameState(players=[], supply={})
        game_state.set_logger(self.logger)

        # Initialize game
        kingdom_cards, event_objs, project_objs, way_objs, ally_objs = self._prepare_board_components(
            kingdom_card_names,
            events,
            projects,
            ways,
            allies,
        )
        game_state.initialize_game(
            [ai1, ai2],
            kingdom_cards,
            use_shelters=self.use_shelters,
            events=event_objs,
            projects=project_objs,
            ways=way_objs,
            allies=ally_objs,
        )

        self._apply_board_traits(game_state)

        # Run game
        while not game_state.is_game_over():
            game_state.play_turn()

        # Get results
        final_turns = game_state.turn_number
        scores = {p.ai.name: p.get_victory_points() for p in game_state.players}
        winner = max(game_state.players, key=lambda p: p.get_victory_points()).ai

        # End game logging and capture log path if any
        log_path = self.logger.end_game(winner.name, scores, game_state.supply, game_state.players)

        return winner, scores, log_path, final_turns


def main():
    parser = argparse.ArgumentParser(description="Run and report a battle between two Dominion strategies")
    parser.add_argument(
        "strategy1_name",
        help=(
            "Strategy identifier (display name or alias). Examples: 'Big Money', 'big_money', "
            "'big-money', 'bigmoney', 'BigMoney'. This is not a Python class name. It matches "
            "strategies registered from create_* functions (and also accepts the EnhancedStrategy "
            "strategy.name value)."
        ),
    )
    parser.add_argument(
        "strategy2_name",
        help=(
            "Strategy identifier (display name or alias). Examples: 'Chapel Witch', 'chapel_witch', "
            "'chapel-witch', 'chapelwitch', 'ChapelWitch'. This is not a Python class name. It matches "
            "strategies registered from create_* functions (and also accepts the EnhancedStrategy "
            "strategy.name value)."
        ),
    )
    parser.add_argument("--games", type=int, default=100, help="Number of games to play")
    parser.add_argument(
        "--use-shelters",
        action="store_true",
        help="Start games with Shelters instead of Estates",
    )
    parser.add_argument("--board", help="Board definition file to enforce kingdom and landscapes")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output HTML file for report",
    )
    parser.add_argument("--print", dest="do_print", action="store_true", help="Print results to console")
    parser.add_argument("--no-report", action="store_true", help="Do not generate an HTML report")
    parser.add_argument("--log", action="store_true", help="Write detailed game logs to battle_logs/")
    parser.add_argument("--log-frequency", type=int, default=10, help="Log every Nth game (1 = every game). Only applies when --log is used.")

    args = parser.parse_args()

    board_config = load_board(args.board) if args.board else None

    if args.do_print:
        logging.basicConfig(level=logging.INFO)

    # Only write game logs when --log is passed; otherwise disable file logging
    log_freq = args.log_frequency if args.log else 0

    battle = StrategyBattle(
        use_shelters=args.use_shelters,
        board_config=board_config,
        verbose=args.do_print,
        log_frequency=log_freq,
    )

    results = battle.run_battle(args.strategy1_name, args.strategy2_name, args.games)

    if args.do_print:
        log_results(results)

    if not args.no_report:
        # Determine output path: auto-generate if not provided
        if args.output is None:

            def _slugify_filename(name: str) -> str:
                slug = name.replace("-", " ").replace("_", " ").lower().replace(" ", "_")
                return re.sub(r"[^a-z0-9_]+", "", slug)

            strat1 = results["strategy1_name"]
            strat2 = results["strategy2_name"]
            games = results["games_played"]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            filename = (
                f"{_slugify_filename(strat1)}_vs_{_slugify_filename(strat2)}_" f"{games}games_{timestamp}_report.html"
            )
            output_path = Path("reports") / filename
        else:
            output_path = args.output

        output_path.parent.mkdir(parents=True, exist_ok=True)
        generate_html_report(results, output_path)


def log_results(results: dict[str, Any]):
    """Print battle results in a readable format."""
    logger.info("\n=== Strategy Battle Results ===")
    logger.info("\nGames played: %d", results['games_played'])

    logger.info("\n%s:", results['strategy1_name'])
    logger.info("  Wins: %d (%.1f%%)", results['strategy1_wins'], results['strategy1_win_rate'])
    logger.info("  Average Score: %.1f", results['strategy1_avg_score'])

    logger.info("\n%s:", results['strategy2_name'])
    logger.info("  Wins: %d (%.1f%%)", results['strategy2_wins'], results['strategy2_win_rate'])
    logger.info("  Average Score: %.1f", results['strategy2_avg_score'])

    log_decision_firings(results)

    logger.info("\nDetailed game results:")
    for game in results["detailed_results"]:
        logger.info("\nGame %d:", game['game_number'])
        logger.info("  Winner: %s", game['winner'])
        logger.info(
            "  Scores: %s=%d, %s=%d",
            results['strategy1_name'],
            game['strategy1_score'],
            results['strategy2_name'],
            game['strategy2_score'],
        )
        logger.info("  Margin: %d", game['margin'])
        logger.info("  Turns: %d", game['turns'])
        if game.get("log_path"):
            logger.info("  Log: %s", game['log_path'])


def log_decision_firings(results: dict[str, Any]) -> None:
    """Print choose_way and choose_gain instrumentation summaries."""
    decision_firings = results.get("decision_firings") or {}
    if not decision_firings:
        return

    logger.info("\nDecision firings:")
    for role in ("strategy1", "strategy2"):
        stats = decision_firings.get(role) or {}
        logger.info("  %s:", stats.get("strategy_name", role))

        way_rows = [
            (card_name, way_name, count)
            for card_name, ways in sorted((stats.get("choose_way") or {}).items())
            for way_name, count in sorted(ways.items())
        ]
        if way_rows:
            logger.info("    choose_way:")
            for card_name, way_name, count in way_rows:
                logger.info("      %s -> %s: %d", card_name, way_name, count)
        else:
            logger.info("    choose_way: 0")

        gain_stats = stats.get("choose_gain_overrides") or {}
        logger.info("    choose_gain special cases: %d", gain_stats.get("total", 0))
        for selection, count in sorted((gain_stats.get("by_selection") or {}).items()):
            logger.info("      %s: %d", selection, count)


if __name__ == "__main__":
    main()
