from contextlib import contextmanager

from ..base_card import Card, CardCost, CardStats, CardType


@contextmanager
def _asking(game_state, chooser):
    """Pose a question to ``chooser`` as the acting player.

    Governor prompts every player in turn, but the AI hooks for trashing and
    gaining read ``state.current_player`` to decide whose deck they are
    reasoning about. Without this swap an opponent answers Governor using the
    Governor owner's deck counts, buy rules and priorities. ``turn_player``
    still reports the real turn holder, so "on your turn" effects are
    unaffected.
    """
    old_index = game_state.current_player_index
    old_turn = game_state.reaction_turn_player_index
    game_state.reaction_turn_player_index = game_state.players.index(
        game_state.turn_player
    )
    game_state.current_player_index = game_state.players.index(chooser)
    try:
        yield
    finally:
        game_state.current_player_index = old_index
        game_state.reaction_turn_player_index = old_turn


class Governor(Card):
    """Flexible payload that benefits everyone."""

    def __init__(self):
        super().__init__(
            name="Governor",
            cost=CardCost(coins=5),
            stats=CardStats(actions=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        options = ["cards", "gold", "upgrade"]
        choice = player.ai.choose_governor_option(game_state, player, options)

        from ..allies._rules import select_modes

        def resolve(choice):
            if choice == "cards":
                self._do_cards_option(game_state, player)
            elif choice == "gold":
                self._do_gold_option(game_state, player)
            else:
                # "Trash a card from your hand" is mandatory for the Governor
                # when able, and choosing it with an empty hand simply does
                # nothing -- it does not become the +3 Cards mode. Each other
                # player still gets their optional upgrade either way.
                self._do_upgrade_option(game_state, player)

        for choice in select_modes(game_state, player, self, options, [choice]):
            resolve(choice)

    def _do_cards_option(self, game_state, player):
        game_state.draw_cards(player, 3)
        for other in game_state.players:
            if other is player:
                continue
            game_state.draw_cards(other, 1)

    def _do_gold_option(self, game_state, player):
        from ..registry import get_card

        gold = get_card("Gold")
        if game_state.supply.get("Gold", 0) > 0:
            game_state.supply["Gold"] -= 1
            game_state.gain_card(player, gold)
        for other in game_state.players:
            if other is player:
                continue
            if game_state.supply.get("Silver", 0) > 0:
                game_state.supply["Silver"] -= 1
                game_state.gain_card(other, get_card("Silver"))

    @staticmethod
    def _exact_upgrade_targets(game_state, chooser, trashed, increment):
        """Supply cards costing exactly ``increment`` more than ``trashed``.

        Governor's upgrade is an exact-cost gain, not a "costing up to" gain:
        $2 more for the player, $1 more for everyone else. The comparison is
        against *current* costs for this player, so cost reducers such as
        Bridge Troll, Highway and a Ferry token move both sides of it. Potion
        and Debt components must match exactly as well, since $5, $2P and
        $5D are three different costs.
        """

        from ..registry import get_card

        target_coins = game_state.get_card_cost(chooser, trashed) + increment
        return [
            get_card(name)
            for name, count in game_state.supply.items()
            if count > 0
            and game_state.get_card_cost(chooser, get_card(name)) == target_coins
            and get_card(name).cost.potions == trashed.cost.potions
            and get_card(name).cost.debt == trashed.cost.debt
        ]

    @staticmethod
    def _upgrade_one(game_state, chooser, increment, *, optional):
        """Trash a card from ``chooser``'s hand and gain the exact upgrade.

        The Governor's own trash is mandatory; every other player "may" trash,
        so an AI naming nothing skips their upgrade. Returns True when a card
        was trashed.
        """

        from ..registry import get_card

        if not chooser.hand:
            return False
        offered = list(chooser.hand) + ([None] if optional else [])
        with _asking(game_state, chooser):
            to_trash = chooser.ai.choose_card_to_trash(game_state, offered)
        if to_trash not in chooser.hand:
            if optional:
                return False
            # Mandatory: an AI that named nothing still has to give something up.
            to_trash = min(
                chooser.hand,
                key=lambda c: (c.is_action, c.is_treasure, c.cost.coins, c.name),
            )
        chooser.hand.remove(to_trash)
        game_state.trash_card(chooser, to_trash)

        targets = Governor._exact_upgrade_targets(
            game_state, chooser, to_trash, increment
        )
        if targets:
            # The shared Allies helper asks as the responder and falls back to
            # the most expensive target when the answer is not on offer.
            from ..allies import _rules

            gain = _rules.choose_gain(game_state, chooser, targets)
            if (
                gain is None
                or gain.name not in game_state.supply
                or game_state.supply[gain.name] <= 0
            ):
                gain = max(targets, key=lambda c: (c.is_action, c.name))
            game_state.supply[gain.name] -= 1
            game_state.gain_card(chooser, get_card(gain.name))
        return True

    def _do_upgrade_option(self, game_state, player):
        """Resolve the upgrade mode for the Governor, then for everyone else.

        The Governor's own trash is mandatory when their hand is non-empty;
        only the other players "may" decline. An empty hand trashes nothing
        and gains nothing, and the other players' upgrades still happen.
        """
        self._upgrade_one(game_state, player, 2, optional=False)
        for other in game_state.players:
            if other is player:
                continue
            self._upgrade_one(game_state, other, 1, optional=True)
        return True
