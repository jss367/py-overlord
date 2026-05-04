from ..base_card import Card, CardCost, CardStats, CardType


class Kitsune(Card):
    """Action-Attack-Omen ($5): +1 Sun.
    Then choose two different options (in the listed order):
    - Each other player gains a Curse
    - +1 Action
    - +$2
    - Gain a Silver
    """

    OPTIONS = ["curse", "action", "coins", "silver"]

    def __init__(self):
        super().__init__(
            name="Kitsune",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.ATTACK, CardType.OMEN],
        )

    def play_effect(self, game_state):
        from ..registry import get_card

        player = game_state.current_player

        chosen = player.ai.choose_kitsune_options(game_state, player, list(self.OPTIONS))
        # Always pick at most two distinct options
        seen = []
        for option in chosen:
            if option in self.OPTIONS and option not in seen:
                seen.append(option)
            if len(seen) == 2:
                break

        # Resolve in the listed order, regardless of pick order
        for option in self.OPTIONS:
            if option not in seen:
                continue
            if option == "curse":
                self._curse_others(game_state, player)
            elif option == "action":
                player.actions += 1
            elif option == "coins":
                player.coins += 2
            elif option == "silver":
                if game_state.supply.get("Silver", 0) > 0:
                    game_state.supply["Silver"] -= 1
                    game_state.gain_card(player, get_card("Silver"))

    def _curse_others(self, game_state, player):
        from ..registry import get_card

        for other in game_state.players:
            if other is player:
                continue

            def attack_target(target):
                if game_state.supply.get("Curse", 0) <= 0:
                    return
                game_state.supply["Curse"] -= 1
                game_state.gain_card(target, get_card("Curse"))

            game_state.attack_player(other, attack_target)
