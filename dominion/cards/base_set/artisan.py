"""Implementation of the Artisan card."""

from ..base_card import Card, CardCost, CardStats, CardType


class Artisan(Card):
    """Action ($6): Gain a card to your hand costing up to $5.

    Put a card from your hand onto your deck.
    """

    def __init__(self):
        super().__init__(
            name="Artisan",
            cost=CardCost(coins=6),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        from ..registry import get_card

        player = game_state.current_player

        # 1) Gain a card costing up to $5 to hand.
        options = []
        for name, count in game_state.supply.items():
            if count <= 0:
                continue
            candidate = get_card(name)
            if candidate.cost.coins > 5:
                continue
            if candidate.cost.potions > 0 or candidate.cost.debt > 0:
                continue
            options.append(candidate)

        if options:
            chosen = player.ai.choose_buy(game_state, options + [None])
            if chosen is None or chosen not in options:
                chosen = max(options, key=lambda c: (c.cost.coins, c.is_action, c.name))

            if game_state.supply.get(chosen.name, 0) > 0:
                game_state.supply[chosen.name] -= 1
                gained = game_state.gain_card(player, chosen)
                if gained is not None:
                    if gained in player.discard:
                        player.discard.remove(gained)
                    elif gained in player.deck:
                        player.deck.remove(gained)
                    if gained not in player.hand:
                        player.hand.append(gained)

        # 2) Put a card from hand onto your deck.
        if not player.hand:
            return

        topdeck_choice = player.ai.choose_card_to_topdeck_from_hand(
            game_state, player, list(player.hand), reason="artisan"
        )
        if topdeck_choice is None or topdeck_choice not in player.hand:
            topdeck_choice = min(
                player.hand, key=lambda c: (c.cost.coins, c.name)
            )

        player.hand.remove(topdeck_choice)
        player.deck.append(topdeck_choice)
        game_state.log_callback(
            (
                "action",
                player.ai.name,
                f"puts {topdeck_choice} onto deck via Artisan",
                {"topdecked": topdeck_choice.name},
            )
        )
