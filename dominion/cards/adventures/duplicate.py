"""Duplicate (Adventures) — $4 Action-Reserve."""

from ..base_card import Card, CardCost, CardStats, CardType


class Duplicate(Card):
    def __init__(self):
        super().__init__(
            name="Duplicate",
            cost=CardCost(coins=4),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.RESERVE],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        game_state.set_aside_on_tavern(player, self)

    def on_call_from_tavern(self, game_state, player, trigger, *args, **kwargs):
        if trigger != "gain":
            return False
        if not args:
            return False
        gained_card = args[0]
        if gained_card is None:
            return False
        from ..allies._rules import effective_cost
        cost = kwargs.get("cost_at_gain") or effective_cost(game_state, gained_card)
        if cost.coins > 6 or cost.potions or cost.debt:
            return False
        pile = game_state.supply_pile_key(gained_card.name)
        if not player.ai.should_call_from_tavern(
            game_state, player, self, trigger, *args
        ):
            return False
        # Calling moves the Reserve into play even if no copy can be gained.
        # Consume it before the nested gain so it cannot re-enter itself.
        if self not in player.tavern_mat:
            return False
        player.tavern_mat.remove(self)
        player.in_play.append(self)
        if player is not game_state.turn_player:
            pending = getattr(game_state, "_off_turn_called_duplicates", [])
            pending.append((player, self))
            game_state._off_turn_called_duplicates = pending
        copy = None
        if pile not in game_state.non_supply_pile_names and game_state.top_supply_card(pile) == gained_card.name:
            copy = game_state.take_top_supply_card(pile)
        if copy is not None:
            game_state.gain_card(player, copy)
        return True
