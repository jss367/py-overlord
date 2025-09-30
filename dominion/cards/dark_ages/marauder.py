from ..base_card import Card, CardCost, CardStats, CardType


class Marauder(Card):
    """Simplified Marauder implementation."""

    def __init__(self):
        super().__init__(
            name="Marauder",
            cost=CardCost(coins=4),
            stats=CardStats(coins=2),
            types=[CardType.ACTION, CardType.ATTACK],
        )

    def get_additional_piles(self) -> dict[str, int]:
        return {"Ruins": 10, "Spoils": 15}

    def play_effect(self, game_state):
        from ..registry import get_card

        player = game_state.current_player

        if game_state.supply.get("Spoils", 0) > 0:
            game_state.supply["Spoils"] -= 1
            spoils = get_card("Spoils")
            gained = game_state.gain_card(player, spoils)
            if gained in player.discard:
                player.discard.remove(gained)
            elif gained in player.deck:
                player.deck.remove(gained)
            if gained not in player.hand:
                player.hand.append(gained)

        def attack_target(target):
            if game_state.supply.get("Ruins", 0) <= 0:
                return
            game_state.supply["Ruins"] -= 1
            ruin = get_card("Ruins")
            game_state.gain_card(target, ruin)

        for other in game_state.players:
            if other is player:
                continue
            game_state.attack_player(other, attack_target)
