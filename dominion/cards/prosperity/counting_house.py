from ..base_card import Card, CardCost, CardStats, CardType


class CountingHouse(Card):
    def __init__(self):
        super().__init__(
            name="Counting House",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        coppers = [c for c in player.discard if c.name == "Copper"]
        if not coppers:
            return
        chosen = player.ai.choose_coppers_for_counting_house(game_state, player, coppers)
        # Normalize a None / non-iterable return to an empty list so an AI
        # following the common "return None to decline" pattern (used by
        # other chooser hooks) doesn't raise TypeError here.
        if chosen is None:
            chosen = []
        # The AI's pick must come from the offered Coppers; ignore anything
        # else (a buggy or adversarial AI cannot smuggle non-Coppers — e.g.
        # Estates — out of the discard pile this way).
        offered = set(map(id, coppers))
        for card in chosen:
            if id(card) not in offered:
                continue
            if card in player.discard:
                player.discard.remove(card)
                player.hand.append(card)
