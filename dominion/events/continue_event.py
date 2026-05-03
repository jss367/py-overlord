"""The Continue event from Rising Sun."""

from dominion.cards.base_card import CardCost
from dominion.cards.registry import get_card

from .base_event import Event


class Continue(Event):
    """$8 Debt: Once per turn. Gain an Action card costing up to $4 that
    isn't an Attack card; return to your Action phase; play the gained card.
    +1 Action, +1 Buy.

    Cost is pure Debt — buying it takes 8 Debt.
    """

    def __init__(self):
        super().__init__("Continue", CardCost(coins=0, debt=8))

    def may_be_bought(self, game_state, player) -> bool:
        return not getattr(player, "continue_used_this_turn", False)

    def on_buy(self, game_state, player) -> None:
        player.continue_used_this_turn = True
        player.actions += 1
        player.buys += 1

        candidates = []
        for name, count in game_state.supply.items():
            if count <= 0:
                continue
            try:
                card = get_card(name)
            except ValueError:
                continue
            if not card.is_action:
                continue
            if card.is_attack:
                continue
            if card.is_command:
                continue
            if card.cost.potions > 0:
                continue
            if card.cost.coins > 4:
                continue
            if card.cost.debt > 0:
                continue
            if not card.may_be_bought(game_state):
                continue
            candidates.append(card)

        if not candidates:
            return

        chosen = player.ai.choose_continue_target(game_state, player, candidates)
        if chosen is None:
            return
        if game_state.supply.get(chosen.name, 0) <= 0:
            return

        game_state.supply[chosen.name] -= 1
        game_state.log_callback(
            ("supply_change", chosen.name, -1, game_state.supply[chosen.name])
        )
        gained = game_state.gain_card(player, chosen)

        # Locate the gained card in whichever post-gain zone it landed in.
        zone = None
        for candidate in (player.hand, player.discard, player.deck):
            if gained in candidate:
                zone = candidate
                break

        if zone is None:
            return

        zone.remove(gained)
        player.in_play.append(gained)

        # Per rulebook: "you return to your Action phase; and you play the
        # Action card you gained." Switch the phase back so the gain plays
        # under Action-phase semantics (Daimyo replays, Prophecy hooks).
        game_state.phase = "action"

        daimyo_replays = getattr(player, "daimyo_pending", 0)
        player.daimyo_pending = 0
        plays = 1 + daimyo_replays
        for _ in range(plays):
            gained.on_play(game_state)
            if game_state.prophecy is not None and game_state.prophecy.is_active:
                game_state.prophecy.on_play_action(game_state, player, gained)
                # Continue can't gain Attack cards, so on_play_attack is dead

        # Let the player use any remaining Action plays from hand. This loop
        # also picks up any Shadow cards now exposed in the deck.
        game_state.handle_action_phase()

        # Skip the Treasure phase per the general rule "you cannot play further
        # Treasures that turn after buying an Event," but return to Buy phase
        # so the outer buy loop continues and 'start of Buy phase' abilities
        # can repeat (Flourishing Trade in particular).
        game_state.phase = "buy"
        if (
            game_state.prophecy is not None
            and game_state.prophecy.is_active
            and game_state.prophecy.name == "Flourishing Trade"
            and player.actions > 0
        ):
            converted = player.actions
            player.actions = 0
            player.buys += converted
