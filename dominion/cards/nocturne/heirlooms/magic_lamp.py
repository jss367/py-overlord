"""Magic Lamp — Secret Cave's Heirloom."""

from collections import Counter

from ...base_card import Card, CardCost, CardStats, CardType


class MagicLamp(Card):
    """$1 Treasure-Heirloom.

    When you play this, if 6+ cards have exactly one copy in play, trash this
    and gain 3 Wishes from the Wish pile.
    """

    def __init__(self):
        super().__init__(
            name="Magic Lamp",
            cost=CardCost(coins=0),
            stats=CardStats(coins=1),
            types=[CardType.TREASURE, CardType.HEIRLOOM],
        )

    def starting_supply(self, game_state) -> int:  # pragma: no cover
        return 0

    def play_effect(self, game_state):
        player = game_state.current_player
        # Duration queues retain instructions after their cards move. Older
        # implementations also use the queue as the only in-play location.
        owned = {id(card) for card in player.all_cards()}
        moved = {
            id(card)
            for zone in player._physical_card_zones()
            if zone is not player.in_play
            for card in zone
        }
        durations_in_play = [
            card for card in player.duration + player.multiplied_durations
            if id(card) in owned and id(card) not in moved
        ]
        counts = Counter(c.name for c in dict.fromkeys(player.in_play + durations_in_play))
        if sum(count == 1 for count in counts.values()) < 6 or self not in player.in_play:
            return
        if self in player.in_play:
            player.in_play.remove(self)
            game_state.trash_card(player, self)
        from ...registry import get_card

        for _ in range(3):
            if game_state.supply.get("Wish", 0) <= 0:
                break
            game_state.supply["Wish"] -= 1
            game_state.gain_card(player, get_card("Wish"))
