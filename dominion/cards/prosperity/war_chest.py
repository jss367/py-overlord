from ..base_card import Card, CardCost, CardStats, CardType


class WarChest(Card):
    """Treasure ($5): +1 Buy. +$1.

    When you play this, the player to your left names a card. Gain a card
    costing up to $5 that wasn't named (this turn).

    Multi-shot: every War Chest played in a turn names a different card; the
    list of named cards is tracked on ``player.war_chest_named_this_turn``.
    """

    def __init__(self):
        super().__init__(
            name="War Chest",
            cost=CardCost(coins=5),
            stats=CardStats(coins=1, buys=1),
            types=[CardType.TREASURE],
        )

    def play_effect(self, game_state):
        from ..registry import get_card

        player = game_state.current_player
        idx = game_state.players.index(player)
        opponent = game_state.players[(idx + 1) % len(game_state.players)]

        # Build the supply view (cards still in supply with at least one copy).
        supply_choices = []
        for name, count in game_state.supply.items():
            if count <= 0:
                continue
            supply_choices.append(get_card(name))

        if not supply_choices:
            return

        named = opponent.ai.choose_card_for_war_chest(
            game_state, opponent, supply_choices
        )
        if named is None:
            named_name = supply_choices[0].name
        else:
            named_name = named.name

        if named_name not in player.war_chest_named_this_turn:
            player.war_chest_named_this_turn.append(named_name)

        # Gain a card costing up to $5 that wasn't named (this turn).
        gainable = []
        for name, count in game_state.supply.items():
            if count <= 0:
                continue
            if name in player.war_chest_named_this_turn:
                continue
            card = get_card(name)
            if card.cost.coins <= 5 and card.cost.potions == 0:
                gainable.append(card)

        if not gainable:
            return

        target = player.ai.choose_war_chest_gain(game_state, player, gainable)
        if target is None:
            return

        if game_state.supply.get(target.name, 0) <= 0:
            return

        game_state.supply[target.name] -= 1
        game_state.gain_card(player, get_card(target.name))
