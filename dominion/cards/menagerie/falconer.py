"""Falconer - Action-Reaction from Menagerie."""

from ..base_card import Card, CardCost, CardStats, CardType


class Falconer(Card):
    """Gain a card costing less than this card to your hand.
    When another player gains a card, you may reveal this from your hand to
    gain a card costing less than the gained card.
    """

    def __init__(self):
        super().__init__(
            name="Falconer",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.REACTION],
        )

    def play_effect(self, game_state):
        from ..registry import get_card

        player = game_state.current_player
        max_cost = self.cost.coins - 1
        candidates = []
        for name, count in game_state.supply.items():
            if count <= 0:
                continue
            try:
                card = get_card(name)
            except ValueError:
                continue
            if card.cost.coins <= max_cost and card.cost.potions == 0:
                candidates.append(card)
        if not candidates:
            return

        choice = player.ai.choose_buy(game_state, candidates + [None])
        if choice is None:
            choice = max(candidates, key=lambda c: (c.cost.coins, c.name))
        if game_state.supply.get(choice.name, 0) <= 0:
            return
        game_state.supply[choice.name] -= 1
        gained = game_state.gain_card(player, choice)
        # Move from discard/deck to hand
        if gained in player.discard:
            player.discard.remove(gained)
            player.hand.append(gained)
        elif gained in player.deck:
            player.deck.remove(gained)
            player.hand.append(gained)

    def on_opponent_gain(self, game_state, player, gainer, gained_card) -> None:
        from ..registry import get_card

        if self not in player.hand:
            return
        if not player.ai.should_reveal_falconer(
            game_state, player, gainer, gained_card
        ):
            return

        max_cost = gained_card.cost.coins - 1
        if max_cost < 0:
            return
        candidates = []
        for name, count in game_state.supply.items():
            if count <= 0:
                continue
            try:
                card = get_card(name)
            except ValueError:
                continue
            if card.cost.coins <= max_cost and card.cost.potions == 0:
                candidates.append(card)
        if not candidates:
            return

        choice = player.ai.choose_buy(game_state, candidates + [None])
        if choice is None:
            choice = max(candidates, key=lambda c: (c.cost.coins, c.name))
        if game_state.supply.get(choice.name, 0) <= 0:
            return
        game_state.supply[choice.name] -= 1
        game_state.gain_card(player, choice)
