"""Pillage — $5 Action-Attack one-shot that trashes itself for 2 Spoils."""

from ..base_card import Card, CardCost, CardStats, CardType


class Pillage(Card):
    """Trash this. Gain 2 Spoils. Each other player with 5 or more cards in
    hand reveals their hand and discards a card you choose.
    """

    def __init__(self):
        super().__init__(
            name="Pillage",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.ATTACK],
        )

    def get_additional_piles(self) -> dict[str, int]:
        return {"Spoils": 15}

    def play_effect(self, game_state):
        from ..registry import get_card

        attacker = game_state.current_player

        # Trash this Pillage
        if self in attacker.in_play:
            attacker.in_play.remove(self)
            game_state.trash_card(attacker, self)

        # Gain 2 Spoils
        for _ in range(2):
            if game_state.supply.get("Spoils", 0) <= 0:
                break
            game_state.supply["Spoils"] -= 1
            game_state.gain_card(attacker, get_card("Spoils"))

        # Attack each other player with hand size >= 5
        def attack_target(target):
            if len(target.hand) < 5:
                return
            game_state.log_callback(
                (
                    "action",
                    target.ai.name,
                    f"reveals hand for Pillage: {[c.name for c in target.hand]}",
                    {"hand": [c.name for c in target.hand]},
                )
            )
            choice = attacker.ai.choose_card_to_discard_for_pillage(
                game_state, attacker, target, list(target.hand)
            )
            if choice and choice in target.hand:
                target.hand.remove(choice)
                game_state.discard_card(target, choice)

        for other in game_state.players:
            if other is attacker:
                continue
            game_state.attack_player(other, attack_target)
