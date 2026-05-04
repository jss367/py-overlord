"""Zombie Mason — non-supply Action-Night, $3."""

from ...base_card import Card, CardCost, CardStats, CardType


class ZombieMason(Card):
    """Reveal hand. Trash a card. Gain a card costing up to $1 more."""

    def __init__(self):
        super().__init__(
            name="Zombie Mason",
            cost=CardCost(coins=3),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.NIGHT, CardType.ZOMBIE],
        )

    def starting_supply(self, game_state) -> int:
        return 1

    def may_be_bought(self, game_state) -> bool:
        return False

    def play_effect(self, game_state):
        from ...registry import get_card

        player = game_state.current_player
        if not player.deck:
            player.shuffle_discard_into_deck()
        if not player.deck:
            return
        trashed = player.deck.pop()
        game_state.trash_card(player, trashed)

        max_cost = trashed.cost.coins + 1
        options = []
        for name, count in game_state.supply.items():
            if count <= 0:
                continue
            try:
                card = get_card(name)
            except ValueError:
                continue
            if card.cost.coins > max_cost or card.cost.potions > 0 or card.cost.debt > 0:
                continue
            if not card.may_be_bought(game_state):
                continue
            options.append(card)
        if not options:
            return
        choice = player.ai.choose_card_to_gain_for_zombie_mason(
            game_state, player, max_cost, options
        )
        if choice is None or choice.name not in {c.name for c in options}:
            choice = max(options, key=lambda c: (c.cost.coins, c.stats.cards, c.name))
        if game_state.supply.get(choice.name, 0) <= 0:
            return
        game_state.supply[choice.name] -= 1
        game_state.gain_card(player, choice)
