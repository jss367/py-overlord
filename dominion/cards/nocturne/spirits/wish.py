"""Wish — non-supply Action-Spirit, $0."""

from ...base_card import Card, CardCost, CardStats, CardType


class Wish(Card):
    """+1 Action. Return this to its pile, then gain a card costing up to $6 to hand."""

    def __init__(self):
        super().__init__(
            name="Wish",
            cost=CardCost(coins=0),
            stats=CardStats(actions=1),
            types=[CardType.ACTION, CardType.SPIRIT],
        )

    def starting_supply(self, game_state) -> int:
        return 12

    def may_be_bought(self, game_state) -> bool:
        return False

    def play_effect(self, game_state):
        from ...registry import get_card

        player = game_state.current_player
        # Return Wish to its non-supply pile
        if self in player.in_play:
            player.in_play.remove(self)
        game_state.supply["Wish"] = game_state.supply.get("Wish", 0) + 1

        # Gain a card costing up to $6 to hand
        options = []
        for name, count in game_state.supply.items():
            if count <= 0:
                continue
            try:
                card = get_card(name)
            except ValueError:
                continue
            if card.cost.coins > 6 or card.cost.potions > 0 or card.cost.debt > 0:
                continue
            if not card.may_be_bought(game_state):
                continue
            options.append(card)
        if not options:
            return
        choice = player.ai.choose_card_to_gain_to_hand(
            game_state, player, options, 6
        )
        if choice is None or choice.name not in {c.name for c in options}:
            choice = max(options, key=lambda c: (c.cost.coins, c.stats.cards, c.name))
        if game_state.supply.get(choice.name, 0) <= 0:
            return
        game_state.supply[choice.name] -= 1
        gained = game_state.gain_card(player, choice)
        if gained:
            if gained in player.discard:
                player.discard.remove(gained)
            elif gained in player.deck:
                player.deck.remove(gained)
            if gained not in player.hand:
                player.hand.append(gained)
