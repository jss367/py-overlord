"""Transmogrify (Adventures) — $4 Action-Reserve."""

from ..base_card import Card, CardCost, CardStats, CardType


class Transmogrify(Card):
    def __init__(self):
        super().__init__(
            name="Transmogrify",
            cost=CardCost(coins=4),
            stats=CardStats(actions=1),
            types=[CardType.ACTION, CardType.RESERVE],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        game_state.set_aside_on_tavern(player, self)

    def on_call_from_tavern(self, game_state, player, trigger, *args, **kwargs):
        from ..registry import get_card

        if trigger != "start_of_turn":
            return False
        if not player.hand:
            return False
        if not player.ai.should_call_from_tavern(
            game_state, player, self, trigger, *args
        ):
            return False
        # Trash a card from hand.
        target = player.ai.choose_card_to_transmogrify(
            game_state, player, list(player.hand)
        )
        if target is None or target not in player.hand:
            return False
        player.hand.remove(target)
        game_state.trash_card(player, target)
        max_cost = target.cost.coins + 1
        # Gain a card costing up to $1 more, putting it into your hand.
        candidates = []
        for name, count in game_state.supply.items():
            if count <= 0:
                continue
            try:
                card = get_card(name)
            except ValueError:
                continue
            if card.cost.coins <= max_cost and card.cost.potions <= player.potions:
                candidates.append(card)
        if candidates:
            choice = player.ai.choose_gain_for_transmogrify(
                game_state, player, candidates
            )
            if choice is not None and game_state.supply.get(choice.name, 0) > 0:
                game_state.supply[choice.name] -= 1
                gained = game_state.gain_card(player, get_card(choice.name))
                if gained in player.discard:
                    player.discard.remove(gained)
                    player.hand.append(gained)
                elif gained in player.deck:
                    player.deck.remove(gained)
                    player.hand.append(gained)
        game_state.call_from_tavern(player, self)
        return True
