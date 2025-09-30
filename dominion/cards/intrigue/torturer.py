from ..base_card import Card, CardCost, CardStats, CardType


class Torturer(Card):
    def __init__(self):
        super().__init__(
            name="Torturer",
            cost=CardCost(coins=5),
            stats=CardStats(cards=3),
            types=[CardType.ACTION, CardType.ATTACK],
        )

    def play_effect(self, game_state):
        """Each other player discards two cards or gains a Curse to hand."""

        player = game_state.current_player

        def attack_target(target):
            hand_size = len(target.hand)
            curses_remaining = game_state.supply.get("Curse", 0)

            if hand_size < 2:
                if curses_remaining > 0:
                    gained = game_state.give_curse_to_player(target, to_hand=True)
                    if gained:
                        game_state.log_callback(
                            (
                                "action",
                                target.ai.name,
                                "takes Curse to hand due to Torturer",
                                {
                                    "curses_remaining": game_state.supply.get("Curse", 0),
                                    "hand": [c.name for c in target.hand],
                                },
                            )
                        )
                return

            choose_discard = target.ai.choose_torturer_attack(game_state, target)
            if not choose_discard and curses_remaining == 0:
                choose_discard = True

            if choose_discard:
                cards_to_discard = target.ai.choose_cards_to_discard(
                    game_state, target, list(target.hand), 2, reason="torturer"
                )
                for card in cards_to_discard:
                    if card in target.hand:
                        target.hand.remove(card)
                        game_state.discard_card(target, card)
                game_state.log_callback(
                    (
                        "action",
                        target.ai.name,
                        "discards 2 cards due to Torturer",
                        {
                            "discarded_cards": [c.name for c in cards_to_discard],
                            "remaining_hand": [c.name for c in target.hand],
                        },
                    )
                )
            else:
                gained = game_state.give_curse_to_player(target, to_hand=True)
                if gained:
                    game_state.log_callback(
                        (
                            "action",
                            target.ai.name,
                            "takes Curse to hand due to Torturer",
                            {
                                "curses_remaining": game_state.supply.get("Curse", 0),
                                "hand": [c.name for c in target.hand],
                            },
                        )
                    )

        for other in game_state.players:
            if other is player:
                continue
            game_state.attack_player(other, attack_target)
