"""Pillage — $5 Action-Attack one-shot that trashes itself for 2 Spoils."""

from ..base_card import Card, CardCost, CardStats, CardType


class Pillage(Card):
    """Trash this. If you did, attack hands of at least five cards, then
    gain two Spoils.
    """

    def __init__(self):
        super().__init__(
            name="Pillage",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.ATTACK],
        )

    def get_additional_non_supply_piles(self) -> dict[str, int]:
        return {"Spoils": 15}

    def play_effect(self, game_state):
        from ..registry import get_card

        attacker = game_state.current_player

        # A virtual Supply play or replay after self-trash cannot move this
        # particular card, so neither the attack nor rewards can resolve.
        if self not in attacker.in_play:
            return
        attacker.in_play.remove(self)
        game_state.trash_card(attacker, self)

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

        attacker_index = game_state.players.index(attacker)
        opponents = game_state.players[attacker_index + 1:] + game_state.players[:attacker_index]
        for other in opponents:
            game_state.attack_player(other, attack_target)

        # Resolve the attack before gaining Spoils, including reactions.
        for _ in range(2):
            if game_state.supply.get("Spoils", 0) <= 0:
                break
            game_state.supply["Spoils"] -= 1
            game_state.gain_card(attacker, get_card("Spoils"))
