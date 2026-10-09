from ..base_card import Card, CardCost, CardStats, CardType
from dominion.ai import tactical_defaults


class Torturer(Card):
    def __init__(self):
        super().__init__(
            name="Torturer",
            cost=CardCost(coins=5),
            stats=CardStats(cards=3),
            types=[CardType.ACTION, CardType.ATTACK],
        )

    def play_effect(self, game_state):
        """Each other player chooses discard two or gain a Curse to hand.

        Either choice remains legal with an empty hand or exhausted Curse pile.
        A chosen discard is mandatory: sanitize physical selections and fill a
        short/invalid answer rather than silently switching the response mode.
        """
        player = game_state.current_player

        def attack_target(target):
            if target.ai.choose_torturer_attack(game_state, target):
                choices = list(target.hand)
                count = min(2, len(choices))
                picks = target.ai.choose_cards_to_discard(
                    game_state, target, list(choices), count, reason="torturer",
                )
                fallback = tactical_defaults.torturer_discards(
                    game_state, target, choices, len(choices),
                )
                selected = []
                for card in list(picks or []) + fallback:
                    if any(card is c for c in choices) and not any(card is c for c in selected):
                        selected.append(card)
                        if len(selected) == count:
                            break
                # An empty hand pays zero discards. Remove the selected batch
                # before discard reactions draw or play cards from that hand.
                for card in selected:
                    target.hand.remove(card)
                game_state.discard_cards(target, selected)
                if selected:
                    game_state.log_callback((
                        "action", target.ai.name,
                        f"discards {len(selected)} cards due to Torturer",
                        {"discarded_cards": [c.name for c in selected],
                         "remaining_hand": [c.name for c in target.hand]},
                    ))
            elif game_state.give_curse_to_player(target, to_hand=True):
                game_state.log_callback((
                    "action", target.ai.name, "takes Curse to hand due to Torturer",
                    {"curses_remaining": game_state.supply.get("Curse", 0),
                     "hand": [c.name for c in target.hand]},
                ))

        start = game_state.players.index(player)
        for other in game_state.players[start + 1:] + game_state.players[:start]:
            game_state.attack_player(other, attack_target)
