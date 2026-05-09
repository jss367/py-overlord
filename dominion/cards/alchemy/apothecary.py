"""Apothecary - Action from Alchemy."""

from ..base_card import Card, CardCost, CardStats, CardType


class Apothecary(Card):
    """Action ($2P): +1 Card, +1 Action.

    Reveal the top 4 cards of your deck. Put any revealed Coppers and
    Potions into your hand. Put the rest back on top in any order.
    """

    def __init__(self):
        super().__init__(
            name="Apothecary",
            cost=CardCost(coins=2, potions=1),
            stats=CardStats(actions=1, cards=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        revealed = []
        for _ in range(4):
            if not player.deck and player.discard:
                player.shuffle_discard_into_deck()
            if not player.deck:
                break
            revealed.append(player.deck.pop())

        if not revealed:
            return

        to_hand = [c for c in revealed if c.name in ("Copper", "Potion")]
        to_topdeck = [c for c in revealed if c.name not in ("Copper", "Potion")]

        player.hand.extend(to_hand)

        if to_topdeck:
            ordered = player.ai.order_cards_for_apothecary_topdeck(
                game_state, player, list(to_topdeck)
            )
            if ordered is None or sorted(c.name for c in ordered) != sorted(
                c.name for c in to_topdeck
            ):
                ordered = to_topdeck
            # Last item ends up on top (drawn first), per deck.pop convention.
            for card in ordered:
                player.deck.append(card)
