# Gaining cards from the Supply

Use `GameState.gain_from_supply` when a card effect gains an exposed Supply
card. It removes the card and runs the existing gain effects and reactions in
one operation. The caller must not decrement the pile first.

```python
gained = state.gain_from_supply(player, chosen.name)
gained = state.gain_from_supply(player, chosen.name, destination="deck")
gained = state.gain_from_supply(player, chosen.name, destination="hand")
```

Build the choice menu using the effect's cost and type restrictions before
calling this method. The method checks availability and pile exposure; it does
not decide whether a card satisfies Workshop's cost limit, for example.

Pass the specific card name, including the exposed member of Knights, Ruins,
or a split pile. Empty, absent, covered, reserved Ferryman, and registered
non-Supply targets return `None`. If a nested effect has consumed the selected
card, the method does not substitute the next member of its pile.

The destination defaults to discard and describes initial placement. Trader
can replace the gain with Silver; Watchtower can move or trash the gained card;
Changeling can exchange it. The returned card reflects those replacements and
may no longer belong to the player. Invalid destinations raise `ValueError`
before removing a card. Errors during gain resolution propagate and do not roll
back reactions or effects that have already run.

## Migrating existing effects

Workshop, Remodel, Anvil, and Quartermaster use this operation through the
shared `gain_selected` helper. Armory and Artificer call it directly for gains
onto the deck. Shared decision recording remains around the committed gain;
Quartermaster still moves the resulting card to its mat after reactions.

Replace a caller's supply decrement or `take_top_supply_card` followed by
`gain_card` with this operation only when the card comes from the normal
Supply. Keep effect-specific selection and post-gain handling at the caller.
Preserve purchase hook ordering and special origins such as the trash,
non-Supply piles, and Ferryman's reserved pile. Those paths still use the
lower-level `gain_card` contract, which expects any supply removal to have
already happened.

`tests/test_gain_from_supply.py` checks pile accounting, reactions, nested
gains, stale selections, and seeded games. Its inventory checks count cards in
Supply, physical player zones, and trash, and reject duplicate physical card
locations and negative pile counts.
