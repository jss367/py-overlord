"""Implementation of the Bureaucrat attack."""

from ..base_card import Card, CardCost, CardStats, CardType


class Bureaucrat(Card):
    """Action - Attack ($4):

    Gain a Silver onto your deck. Each other player reveals a Victory card
    from their hand and puts it onto their deck (or reveals a hand with no
    Victory cards).
    """

    def __init__(self):
        super().__init__(
            name="Bureaucrat",
            cost=CardCost(coins=4),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.ATTACK],
        )

    def play_effect(self, game_state):
        from ..registry import get_card

        player = game_state.current_player

        # Gain a Silver onto your deck.
        if game_state.supply.get("Silver", 0) > 0:
            game_state.supply["Silver"] -= 1
            game_state.gain_card(player, get_card("Silver"), to_deck=True)

        def attack_target(target):
            victories = [card for card in target.hand if card.is_victory]
            if not victories:
                # Reveal a hand with no Victory cards.
                game_state.log_callback(
                    (
                        "action",
                        target.ai.name,
                        "reveals hand with no Victory cards (Bureaucrat)",
                        {"hand": [c.name for c in target.hand]},
                    )
                )
                return

            choice = target.ai.choose_card_to_topdeck_from_hand(
                game_state, target, list(victories), reason="bureaucrat"
            )
            if choice is None or choice not in victories:
                # Default: cheapest victory card.
                choice = min(
                    victories, key=lambda c: (c.cost.coins, c.name)
                )

            target.hand.remove(choice)
            target.deck.append(choice)
            game_state.log_callback(
                (
                    "action",
                    target.ai.name,
                    f"topdecks {choice} due to Bureaucrat",
                    {"topdecked": choice.name},
                )
            )

        for other in game_state.players:
            if other is player:
                continue
            game_state.attack_player(other, attack_target)
