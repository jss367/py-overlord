from ..base_card import Card, CardCost, CardStats, CardType


class Crypt(Card):
    """Implementation of the Nocturne card ``Crypt``."""

    def __init__(self):
        super().__init__(
            name="Crypt",
            cost=CardCost(coins=5),
            stats=CardStats(actions=1),
            types=[CardType.ACTION, CardType.DURATION],
        )
        self.set_aside: list = []
        self.duration_persistent = False

    def play_effect(self, game_state):
        player = game_state.current_player
        treasures = [card for card in player.hand if card.is_treasure]

        selected: list = []
        if treasures:
            chosen = player.ai.choose_treasures_to_set_aside_for_crypt(
                game_state, player, treasures
            )

            remaining_choices = list(treasures)
            for card in chosen:
                if card in remaining_choices:
                    remaining_choices.remove(card)
                    selected.append(card)

            for card in selected:
                player.hand.remove(card)

        # Extend instead of replacing so Throne Room style effects work.
        if selected:
            self.set_aside.extend(selected)
            self.duration_persistent = True
            if self not in player.duration:
                player.duration.append(self)
        elif self.set_aside:
            # Already have set-aside cards from a previous play; keep duration active.
            self.duration_persistent = True
            if self not in player.duration:
                player.duration.append(self)
        else:
            # No treasures were set aside – ensure previous state is cleared.
            self.set_aside = []
            self.duration_persistent = False

    def on_duration(self, game_state):
        player = game_state.current_player

        if not self.set_aside:
            self.duration_persistent = False
            return

        choice = player.ai.choose_treasure_to_return_from_crypt(
            game_state, player, list(self.set_aside)
        )
        if choice not in self.set_aside:
            # Fallback to returning the first set-aside treasure.
            choice = self.set_aside[0]

        self.set_aside.remove(choice)
        player.hand.append(choice)

        self.duration_persistent = bool(self.set_aside)
