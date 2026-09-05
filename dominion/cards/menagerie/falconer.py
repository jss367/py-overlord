"""Falconer - Action-Reaction from Menagerie."""

from ..base_card import Card, CardCost, CardStats, CardType


class Falconer(Card):
    """Gain a card to your hand costing less than this.

    Reaction: when any player gains a card with 2 or more types (Action,
    Attack, etc.), you may play this from your hand. The reaction itself is
    resolved by ``GameState._handle_falconer_reactions`` so it fires on the
    owner's own gains as well as on other players' gains.
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
            if name in game_state.non_supply_pile_names:
                continue
            try:
                card = get_card(name)
            except ValueError:
                continue
            # A card with a Debt or Potion cost never "costs less than $5".
            if card.cost.debt or card.cost.potions:
                continue
            if card.cost.coins <= max_cost and card.may_be_gained(game_state):
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
        if gained is None:
            return
        # Move from discard/deck to hand
        if gained in player.discard:
            player.discard.remove(gained)
            player.hand.append(gained)
        elif gained in player.deck:
            player.deck.remove(gained)
            player.hand.append(gained)
