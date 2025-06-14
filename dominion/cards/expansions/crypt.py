from ..base_card import Card, CardCost, CardStats, CardType


class Crypt(Card):
    """Simplified implementation of the Crypt card."""

    def __init__(self):
        super().__init__(
            name="Crypt",
            cost=CardCost(coins=5),
            stats=CardStats(actions=1),
            types=[CardType.ACTION, CardType.DURATION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        treasures = [c for c in player.hand if c.is_treasure]
        to_set_aside = treasures[:2]
        for card in to_set_aside:
            player.hand.remove(card)
        player.crypt_set_aside = getattr(player, "crypt_set_aside", []) + to_set_aside
        player.duration.append(self)

    def on_duration(self, game_state):
        player = game_state.current_player
        cards = getattr(player, "crypt_set_aside", [])
        player.hand.extend(cards)
        player.crypt_set_aside = []
        if self in player.duration:
            player.duration.remove(self)
        player.discard.append(self)
