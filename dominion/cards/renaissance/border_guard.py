"""Border Guard: Action ($2). +1 Action.

Reveal the top 2 cards of your deck (3 if the player owns the Lantern
artifact). Put one into hand and discard the others. If both/all are
Actions, also take the Horn or the Lantern (your choice; if both are
unowned, take Horn by default).
"""

from ..base_card import Card, CardCost, CardStats, CardType


class BorderGuard(Card):
    def __init__(self) -> None:
        super().__init__(
            name="Border Guard",
            cost=CardCost(coins=2),
            stats=CardStats(actions=1),
            types=[CardType.ACTION],
        )
        # Set by the Horn artifact when this card is played by the holder.
        self.horn_topdeck_pending = False

    def play_effect(self, game_state):
        player = game_state.current_player

        lantern = game_state.artifacts.get("Lantern")
        reveal_count = 3 if (lantern is not None and lantern.holder is player) else 2

        revealed: list = []
        for _ in range(reveal_count):
            if not player.deck and player.discard:
                player.shuffle_discard_into_deck()
            if not player.deck:
                break
            revealed.append(player.deck.pop())

        if not revealed:
            return

        # Snapshot Horn ownership BEFORE any artifact-take (taking the Horn
        # via "all Actions" shouldn't retroactively topdeck this play).
        horn_before = game_state.artifacts.get("Horn")
        horn_held_by_player_before = (
            horn_before is not None and horn_before.holder is player
        )

        # Pick which to keep: AI hook with sensible default — keep highest
        # cost Action, otherwise highest-cost card.
        keep = max(
            revealed,
            key=lambda c: (c.is_action, c.cost.coins, c.stats.cards, c.name),
        )
        revealed.remove(keep)
        player.hand.append(keep)
        for card in revealed:
            game_state.discard_card(player, card)

        # If all originally revealed cards were Actions, take Horn or Lantern.
        original_count = 1 + len(revealed)
        all_actions = keep.is_action and all(c.is_action for c in revealed)
        if all_actions and original_count == reveal_count:
            self._take_artifact(game_state, player)

        # Horn topdeck: if the player held the Horn before playing this card,
        # the Horn lets them topdeck it during cleanup.
        if horn_held_by_player_before and horn_before is not None:
            horn_before.on_holder_play_border_guard(game_state, player, self)

    @staticmethod
    def _take_artifact(game_state, player) -> None:
        horn = game_state.artifacts.get("Horn")
        lantern = game_state.artifacts.get("Lantern")

        # Determine ownership.
        horn_owned_by_self = horn is not None and horn.holder is player
        lantern_owned_by_self = lantern is not None and lantern.holder is player

        # Prefer the unowned one if exactly one is unowned by the player.
        if horn is not None and not horn_owned_by_self:
            game_state.take_artifact(player, "Horn")
            return
        if lantern is not None and not lantern_owned_by_self:
            game_state.take_artifact(player, "Lantern")
