"""Implementation of the Artificer discard-for-gain card."""

from ..base_card import Card, CardCost, CardStats, CardType


class Artificer(Card):
    def __init__(self):
        super().__init__(
            name="Artificer",
            cost=CardCost(coins=5),
            stats=CardStats(cards=1, actions=1, coins=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        if not player.hand:
            return

        discard_choices = player.ai.choose_cards_to_discard(
            game_state, player, list(player.hand), len(player.hand)
        )
        discarded = 0
        for card in discard_choices:
            if card in player.hand:
                player.hand.remove(card)
                game_state.discard_card(player, card)
                discarded += 1

        if discarded == 0:
            return

        from ..registry import get_card

        gain_options = []
        for name, count in game_state.supply.items():
            if count <= 0:
                continue
            card = get_card(name)
            if card.cost.coins <= discarded:
                gain_options.append(card)

        if not gain_options:
            return

        gain_options.sort(key=lambda c: (c.cost.coins, c.name), reverse=True)
        target = gain_options[0]
        game_state.supply[target.name] -= 1
        game_state.gain_card(player, target, to_deck=True)
