from .base_ally import Ally
from ..cards.allies._rules import decide


class ForestDwellers(Ally):
    def __init__(self):
        super().__init__("Forest Dwellers")

    def on_turn_start(self, game_state, player):
        if player.favors < 1 or not decide(
            game_state,
            player,
            "forest_dwellers",
            [False, True],
            bool(player.deck or player.discard),
        ):
            return
        player.favors -= 1
        revealed = []
        for _ in range(3):
            if not player.deck and player.discard:
                player.shuffle_discard_into_deck()
            if not player.deck:
                break
            revealed.append(player.deck.pop())
        kept = []
        for card in revealed:
            if decide(
                game_state,
                player,
                "forest_dwellers_discard",
                [False, True],
                card.name in {"Curse", "Estate", "Copper"},
            ):
                game_state.discard_card(player, card)
            else:
                kept.append(card)
        ordered = player.ai.order_cards_for_topdeck(game_state, player, kept)
        remaining = list(kept)
        valid = []
        for card in list(ordered or []) + kept:
            if card in remaining:
                remaining.remove(card)
                valid.append(card)
        player.deck.extend(reversed(valid))
