from ..base_card import Card, CardCost, CardStats, CardType


class TreasureMap(Card):
    """Action ($4): Trash this and another Treasure Map from your hand.
    If you trashed two Treasure Maps, gain 4 Golds, putting them on top of your deck.
    """

    def __init__(self):
        super().__init__(
            name="Treasure Map",
            cost=CardCost(coins=4),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        from ..registry import get_card

        player = game_state.current_player

        # Trash this Treasure Map (it was moved to in_play during on_play).
        if self in player.in_play:
            player.in_play.remove(self)
            game_state.trash_card(player, self)

        # Find another Treasure Map in hand.
        other = next((c for c in player.hand if c.name == "Treasure Map"), None)
        if other is None:
            return

        player.hand.remove(other)
        game_state.trash_card(player, other)

        # Gain 4 Golds onto the top of the deck.
        for _ in range(4):
            if game_state.supply.get("Gold", 0) <= 0:
                break
            game_state.supply["Gold"] -= 1
            gained = game_state.gain_card(player, get_card("Gold"))
            # Move from discard onto the top of the deck.
            if gained in player.discard:
                player.discard.remove(gained)
                player.deck.append(gained)
