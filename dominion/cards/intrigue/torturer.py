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
            curses_remaining = game_state.supply.get("Curse", 0)

            choose_discard = target.ai.choose_torturer_attack(game_state, target)
            if not choose_discard and curses_remaining == 0:
                choose_discard = True

            if choose_discard:
                max_discards = min(2, len(target.hand))
                if max_discards == 0 and curses_remaining > 0:
                    # The player cannot discard any cards, so they must take the Curse
                    choose_discard = False
                else:
                    cards_to_discard = target.ai.choose_cards_to_discard(
                        game_state,
                        target,
                        list(target.hand),
                        max_discards,
                        reason="torturer",
                    )
                    # Ensure we only discard cards actually still in hand
                    discarded: list[Card] = []
                    for card in cards_to_discard[:max_discards]:
                        if card in target.hand:
                            target.hand.remove(card)
                            game_state.discard_card(target, card)
                            discarded.append(card)

                    if discarded:
                        discard_count = len(discarded)
                        card_desc = "card" if discard_count == 1 else "cards"
                        game_state.log_callback(
                            (
                                "action",
                                target.ai.name,
                                f"discards {discard_count} {card_desc} due to Torturer",
                                {
                                    "discarded_cards": [c.name for c in discarded],
                                    "remaining_hand": [c.name for c in target.hand],
                                },
                            )
                        )
                    else:
                        choose_discard = False

            if not choose_discard:
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
