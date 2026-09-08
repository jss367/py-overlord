"""Catacombs — $5 Action that previews 3 cards and gains a cheaper card on trash."""

from ..base_card import Card, CardCost, CardStats, CardType


class Catacombs(Card):
    """Look at the top 3 cards of your deck. Choose one: put them into your hand;
    or discard them and +3 Cards.

    When you trash this, gain a cheaper card.
    """

    def __init__(self):
        super().__init__(
            name="Catacombs",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        from ..allies._rules import select_modes, plus_cards

        player = game_state.current_player
        looked_at = []
        for _ in range(3):
            if not player.deck and player.discard:
                player.shuffle_discard_into_deck()
            if not player.deck:
                break
            looked_at.append(player.deck.pop())
        default = (
            "discard"
            if player.ai.should_catacombs_discard_three(
                game_state, player, list(looked_at)
            )
            else "hand"
        )
        for mode in select_modes(
            game_state, player, self, ["hand", "discard"], [default]
        ):
            if mode == "hand":
                player.hand.extend(looked_at)
            else:
                for card in looked_at:
                    game_state.discard_card(player, card)
                plus_cards(game_state, player, 3)
            # Once moved, these cards cannot be moved again by the other choice.
            looked_at = []

    def on_trash(self, game_state, player):
        from ..registry import get_card

        candidates: list[Card] = []
        my_cost = self.cost.coins
        for name, count in game_state.supply.items():
            if count <= 0:
                continue
            try:
                c = get_card(name)
            except ValueError:
                continue
            if c.cost.coins >= my_cost:
                continue
            if c.cost.potions > 0 or c.cost.debt > 0:
                continue
            if not c.may_be_bought(game_state):
                continue
            candidates.append(c)

        choice = player.ai.choose_card_to_gain_with_catacombs(
            game_state, player, candidates
        )
        if choice and game_state.supply.get(choice.name, 0) > 0:
            game_state.supply[choice.name] -= 1
            game_state.gain_card(player, get_card(choice.name))
