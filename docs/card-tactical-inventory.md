# Card decision evidence inventory

Generated from `scripts/render_tactical_inventory.py` and the canonical card registry.
Run `PYTHONPATH=. python scripts/render_tactical_inventory.py` after adding cards or evidence.

This is the coverage source for [the shared-decision plan](card-tactical-defaults.md) and [parent #344](https://github.com/jss367/py-overlord/issues/344). Rules audits, engine wiring, and tactical evaluation are independent columns. Evaluated means measured on the declared panel, including losses; it does not certify strong play. Connected/tested does not imply evaluated. Needs forwarding and needs context remain open implementation work. Unreviewed means no claim in this audit, including for fixed-effect cards and their action order. Member cards and non-Supply cards are listed separately; counts are registered names, not kingdom piles.

Merged decision work: [#404](https://github.com/jss367/py-overlord/pull/404) (supply targets), [#403](https://github.com/jss367/py-overlord/pull/403) (free gains), [#402](https://github.com/jss367/py-overlord/pull/402) (trash/discard/storage), [#348](https://github.com/jss367/py-overlord/pull/348) (Courier). Source inspection is limited to the named hooks and linked tests.

## Coverage by expansion

| Expansion | Registered names | Scoped reviewed entries | Unreviewed entries |
| --- | ---: | ---: | ---: |
| Adventures | 38 | 2 | 36 |
| Alchemy | 12 | 0 | 12 |
| Allies | 49 | 1 | 48 |
| Base | 39 | 4 | 35 |
| Cornucopia | 32 | 0 | 32 |
| Dark Ages | 57 | 16 | 41 |
| Empires | 36 | 2 | 34 |
| Guilds | 13 | 0 | 13 |
| Hinterlands | 35 | 3 | 32 |
| Intrigue | 32 | 4 | 28 |
| Menagerie | 31 | 3 | 28 |
| Nocturne | 48 | 0 | 48 |
| Plunder | 55 | 1 | 54 |
| Promo | 12 | 1 | 11 |
| Prosperity | 36 | 4 | 32 |
| Renaissance | 25 | 0 | 25 |
| Rising Sun | 25 | 0 | 25 |
| Seaside | 35 | 1 | 34 |

Total: 610 registered names; 42 scoped entries; 568 unreviewed.

Priority: finish active kingdoms and #393 timing/response coverage, then review Base, Prosperity, Menagerie and the remaining expansions. Ironworks and Engineer expose additional free-gain context gaps; their hooks are not duplicated here.

## Scoped evidence

| Card | Expansion | Decision | Rules audit | Engine → AI wiring | Tactical evaluation | Evidence / follow-ups |
| --- | --- | --- | --- | --- | --- | --- |
| Artificer | Adventures | Discard budget / deck gain | Targeted regression audit; other interactions unreviewed | Connected/tested: [`dominion/ai/genetic_ai.py`](../dominion/ai/genetic_ai.py) → `choose_artificer_gain`, `choose_cards_to_discard` | Unreviewed | [`dominion/cards/adventures/artificer.py`](../dominion/cards/adventures/artificer.py); [`tests/test_kolkata_board_cards.py`](../tests/test_kolkata_board_cards.py); [#394](https://github.com/jss367/py-overlord/issues/394) |
| Gear | Adventures | Next-turn set-aside | Targeted regression audit; other interactions unreviewed | Connected/tested: [`dominion/ai/genetic_ai.py`](../dominion/ai/genetic_ai.py) → `choose_gear_set_aside` | Evaluated: fixed kingdom; engine score regressions | [`dominion/cards/adventures/gear.py`](../dominion/cards/adventures/gear.py); [`tests/test_set_aside_tactics.py`](../tests/test_set_aside_tactics.py); [`reports/strategies/trashing-discard-and-next-turn-card-decisions.html`](../reports/strategies/trashing-discard-and-next-turn-card-decisions.html); [#392](https://github.com/jss367/py-overlord/issues/392), [#398](https://github.com/jss367/py-overlord/issues/398) |
| Courier | Allies | Optional Action/Treasure play from discard | Targeted regression audit; other interactions unreviewed | Connected/tested: [`dominion/ai/genetic_ai.py`](../dominion/ai/genetic_ai.py) → `choose_courier_target` | Unreviewed | [`dominion/cards/allies/standalone.py`](../dominion/cards/allies/standalone.py); [`tests/test_courier.py`](../tests/test_courier.py); [#348](https://github.com/jss367/py-overlord/issues/348) |
| Chapel | Base | Optional bounded / mandatory trash | Targeted regression audit; other interactions unreviewed | Connected/tested: [`dominion/ai/genetic_ai.py`](../dominion/ai/genetic_ai.py) → `choose_card_to_trash` | Needs context: scenario coverage; strength not isolated | [`dominion/cards/base_set/chapel.py`](../dominion/cards/base_set/chapel.py); [`tests/test_set_aside_tactics.py`](../tests/test_set_aside_tactics.py); [#392](https://github.com/jss367/py-overlord/issues/392) |
| Moneylender | Base | Optional Copper trash | Targeted regression audit; other interactions unreviewed | Connected/tested: [`dominion/ai/genetic_ai.py`](../dominion/ai/genetic_ai.py) → `should_trash_copper_for_moneylender` | Unreviewed | [`dominion/cards/base_set/moneylender.py`](../dominion/cards/base_set/moneylender.py); [`tests/test_groundskeeper_margrave.py`](../tests/test_groundskeeper_margrave.py);  |
| Remodel | Base | Free gain / sacrifice / storage | Targeted regression audit; other interactions unreviewed | Connected/tested: [`dominion/ai/genetic_ai.py`](../dominion/ai/genetic_ai.py) → `choose_free_gain`, `choose_remodel_option` | Evaluated: mixed/regressing fixed panels | [`dominion/cards/base_set/remodel.py`](../dominion/cards/base_set/remodel.py); [`tests/test_free_gain_tactics.py`](../tests/test_free_gain_tactics.py); [`tests/test_free_gain_evaluation.py`](../tests/test_free_gain_evaluation.py); [`scripts/data/free_gain_tactics_evaluation-2026-10-08-anvil-adapter.json`](../scripts/data/free_gain_tactics_evaluation-2026-10-08-anvil-adapter.json); [`reports/strategies/free-gains-and-quartermaster-policy-evaluation.html`](../reports/strategies/free-gains-and-quartermaster-policy-evaluation.html); [#391](https://github.com/jss367/py-overlord/issues/391) |
| Workshop | Base | Free gain / sacrifice / storage | Targeted regression audit; other interactions unreviewed | Connected/tested: [`dominion/ai/genetic_ai.py`](../dominion/ai/genetic_ai.py) → `choose_free_gain` | Evaluated: mixed/regressing fixed panels | [`dominion/cards/base_set/workshop.py`](../dominion/cards/base_set/workshop.py); [`tests/test_free_gain_tactics.py`](../tests/test_free_gain_tactics.py); [`tests/test_free_gain_evaluation.py`](../tests/test_free_gain_evaluation.py); [`scripts/data/free_gain_tactics_evaluation-2026-10-08-anvil-adapter.json`](../scripts/data/free_gain_tactics_evaluation-2026-10-08-anvil-adapter.json); [`reports/strategies/free-gains-and-quartermaster-policy-evaluation.html`](../reports/strategies/free-gains-and-quartermaster-policy-evaluation.html); [#391](https://github.com/jss367/py-overlord/issues/391) |
| Armory | Dark Ages | Mandatory deck gain | Targeted regression audit; other interactions unreviewed | Connected/tested: [`dominion/ai/genetic_ai.py`](../dominion/ai/genetic_ai.py) → `choose_armory_gain` | Unreviewed | [`dominion/cards/dark_ages/armory.py`](../dominion/cards/dark_ages/armory.py); [`tests/test_kolkata_board_cards.py`](../tests/test_kolkata_board_cards.py); [#394](https://github.com/jss367/py-overlord/issues/394) |
| Band of Misfits | Dark Ages | Supply Action target | Targeted menus; open proxy/indirect-play/scheduling defects | Connected/tested: [`dominion/ai/genetic_ai.py`](../dominion/ai/genetic_ai.py) → `choose_band_of_misfits_target` | Evaluated: fixed non-Duration panel only | [`dominion/cards/dark_ages/band_of_misfits.py`](../dominion/cards/dark_ages/band_of_misfits.py); [`tests/test_shared_card_tactics.py`](../tests/test_shared_card_tactics.py); [`scripts/data/supply_action_evaluation.json`](../scripts/data/supply_action_evaluation.json); [`reports/strategies/supply-action-selection-evaluation.html`](../reports/strategies/supply-action-selection-evaluation.html); [#390](https://github.com/jss367/py-overlord/issues/390), [#395](https://github.com/jss367/py-overlord/issues/395), [#396](https://github.com/jss367/py-overlord/issues/396), [#397](https://github.com/jss367/py-overlord/issues/397), [#405](https://github.com/jss367/py-overlord/issues/405) |
| Counterfeit | Dark Ages | Optional Treasure replay/trash | Targeted regression audit; other interactions unreviewed | Connected/tested: [`dominion/ai/base_ai.py`](../dominion/ai/base_ai.py) → `should_replay_treasure_with_counterfeit` | Unreviewed | [`dominion/cards/dark_ages/counterfeit.py`](../dominion/cards/dark_ages/counterfeit.py); [`tests/test_recruiter_kitsune_rules.py`](../tests/test_recruiter_kitsune_rules.py);  |
| Dame Anna | Dark Ages | Shared victim trash; each member's extras unreviewed | Targeted regression audit; other interactions unreviewed | Connected/tested: [`dominion/ai/genetic_ai.py`](../dominion/ai/genetic_ai.py) → `choose_card_to_trash_for_knight_attack` | Unreviewed | [`dominion/cards/dark_ages/knights.py`](../dominion/cards/dark_ages/knights.py); [`tests/test_kolkata_board_cards.py`](../tests/test_kolkata_board_cards.py); [#394](https://github.com/jss367/py-overlord/issues/394) |
| Dame Josephine | Dark Ages | Shared victim trash; each member's extras unreviewed | Targeted regression audit; other interactions unreviewed | Connected/tested: [`dominion/ai/genetic_ai.py`](../dominion/ai/genetic_ai.py) → `choose_card_to_trash_for_knight_attack` | Unreviewed | [`dominion/cards/dark_ages/knights.py`](../dominion/cards/dark_ages/knights.py); [`tests/test_kolkata_board_cards.py`](../tests/test_kolkata_board_cards.py); [#394](https://github.com/jss367/py-overlord/issues/394) |
| Dame Molly | Dark Ages | Shared victim trash; each member's extras unreviewed | Targeted regression audit; other interactions unreviewed | Connected/tested: [`dominion/ai/genetic_ai.py`](../dominion/ai/genetic_ai.py) → `choose_card_to_trash_for_knight_attack` | Unreviewed | [`dominion/cards/dark_ages/knights.py`](../dominion/cards/dark_ages/knights.py); [`tests/test_kolkata_board_cards.py`](../tests/test_kolkata_board_cards.py); [#394](https://github.com/jss367/py-overlord/issues/394) |
| Dame Natalie | Dark Ages | Shared victim trash; each member's extras unreviewed | Targeted regression audit; other interactions unreviewed | Connected/tested: [`dominion/ai/genetic_ai.py`](../dominion/ai/genetic_ai.py) → `choose_card_to_trash_for_knight_attack` | Unreviewed | [`dominion/cards/dark_ages/knights.py`](../dominion/cards/dark_ages/knights.py); [`tests/test_kolkata_board_cards.py`](../tests/test_kolkata_board_cards.py); [#394](https://github.com/jss367/py-overlord/issues/394) |
| Dame Sylvia | Dark Ages | Shared victim trash; each member's extras unreviewed | Targeted regression audit; other interactions unreviewed | Connected/tested: [`dominion/ai/genetic_ai.py`](../dominion/ai/genetic_ai.py) → `choose_card_to_trash_for_knight_attack` | Unreviewed | [`dominion/cards/dark_ages/knights.py`](../dominion/cards/dark_ages/knights.py); [`tests/test_kolkata_board_cards.py`](../tests/test_kolkata_board_cards.py); [#394](https://github.com/jss367/py-overlord/issues/394) |
| Junk Dealer | Dark Ages | Optional bounded / mandatory trash | Targeted regression audit; other interactions unreviewed | Connected/tested: [`dominion/ai/genetic_ai.py`](../dominion/ai/genetic_ai.py) → `choose_card_to_trash_with_junk_dealer` | Needs context: scenario coverage; strength not isolated | [`dominion/cards/dark_ages/junk_dealer.py`](../dominion/cards/dark_ages/junk_dealer.py); [`tests/test_set_aside_tactics.py`](../tests/test_set_aside_tactics.py); [#392](https://github.com/jss367/py-overlord/issues/392) |
| Knights | Dark Ages | Shared victim trash; each member's extras unreviewed | Targeted regression audit; other interactions unreviewed | Connected/tested: [`dominion/ai/genetic_ai.py`](../dominion/ai/genetic_ai.py) → `choose_card_to_trash_for_knight_attack` | Unreviewed | [`dominion/cards/dark_ages/knights.py`](../dominion/cards/dark_ages/knights.py); [`tests/test_kolkata_board_cards.py`](../tests/test_kolkata_board_cards.py); [#394](https://github.com/jss367/py-overlord/issues/394) |
| Rogue | Dark Ages | Victim trash; trash-pile gain policy unreviewed | Targeted regression audit; other interactions unreviewed | Connected/tested: [`dominion/ai/genetic_ai.py`](../dominion/ai/genetic_ai.py) → `choose_card_to_trash_for_rogue_attack` | Unreviewed | [`dominion/cards/dark_ages/rogue.py`](../dominion/cards/dark_ages/rogue.py); [`tests/test_kolkata_board_cards.py`](../tests/test_kolkata_board_cards.py); [#394](https://github.com/jss367/py-overlord/issues/394) |
| Sir Bailey | Dark Ages | Shared victim trash; each member's extras unreviewed | Targeted regression audit; other interactions unreviewed | Connected/tested: [`dominion/ai/genetic_ai.py`](../dominion/ai/genetic_ai.py) → `choose_card_to_trash_for_knight_attack` | Unreviewed | [`dominion/cards/dark_ages/knights.py`](../dominion/cards/dark_ages/knights.py); [`tests/test_kolkata_board_cards.py`](../tests/test_kolkata_board_cards.py); [#394](https://github.com/jss367/py-overlord/issues/394) |
| Sir Destry | Dark Ages | Shared victim trash; each member's extras unreviewed | Targeted regression audit; other interactions unreviewed | Connected/tested: [`dominion/ai/genetic_ai.py`](../dominion/ai/genetic_ai.py) → `choose_card_to_trash_for_knight_attack` | Unreviewed | [`dominion/cards/dark_ages/knights.py`](../dominion/cards/dark_ages/knights.py); [`tests/test_kolkata_board_cards.py`](../tests/test_kolkata_board_cards.py); [#394](https://github.com/jss367/py-overlord/issues/394) |
| Sir Martin | Dark Ages | Shared victim trash; each member's extras unreviewed | Targeted regression audit; other interactions unreviewed | Connected/tested: [`dominion/ai/genetic_ai.py`](../dominion/ai/genetic_ai.py) → `choose_card_to_trash_for_knight_attack` | Unreviewed | [`dominion/cards/dark_ages/knights.py`](../dominion/cards/dark_ages/knights.py); [`tests/test_kolkata_board_cards.py`](../tests/test_kolkata_board_cards.py); [#394](https://github.com/jss367/py-overlord/issues/394) |
| Sir Michael | Dark Ages | Shared victim trash; each member's extras unreviewed | Targeted regression audit; other interactions unreviewed | Connected/tested: [`dominion/ai/genetic_ai.py`](../dominion/ai/genetic_ai.py) → `choose_card_to_trash_for_knight_attack` | Unreviewed | [`dominion/cards/dark_ages/knights.py`](../dominion/cards/dark_ages/knights.py); [`tests/test_kolkata_board_cards.py`](../tests/test_kolkata_board_cards.py); [#394](https://github.com/jss367/py-overlord/issues/394) |
| Sir Vander | Dark Ages | Shared victim trash; each member's extras unreviewed | Targeted regression audit; other interactions unreviewed | Connected/tested: [`dominion/ai/genetic_ai.py`](../dominion/ai/genetic_ai.py) → `choose_card_to_trash_for_knight_attack` | Unreviewed | [`dominion/cards/dark_ages/knights.py`](../dominion/cards/dark_ages/knights.py); [`tests/test_kolkata_board_cards.py`](../tests/test_kolkata_board_cards.py); [#394](https://github.com/jss367/py-overlord/issues/394) |
| Engineer | Empires | Optional self-trash and free gains via purchase selector | Targeted regression audit; other interactions unreviewed | Needs context: self-trash connected; gains reuse purchases: [`dominion/ai/base_ai.py`](../dominion/ai/base_ai.py) → `should_trash_engineer_for_extra_gains`, `choose_buy` | Needs context: gain destination / ownership | [`dominion/cards/empires/engineer.py`](../dominion/cards/empires/engineer.py); [`tests/test_recruiter_kitsune_rules.py`](../tests/test_recruiter_kitsune_rules.py); [#412](https://github.com/jss367/py-overlord/issues/412) |
| Overlord | Empires | Supply Action target | Targeted menus; open proxy/indirect-play/scheduling defects | Connected/tested: [`dominion/ai/genetic_ai.py`](../dominion/ai/genetic_ai.py) → `choose_overlord_target` | Evaluated: fixed non-Duration panel only | [`dominion/cards/empires/overlord.py`](../dominion/cards/empires/overlord.py); [`tests/test_shared_card_tactics.py`](../tests/test_shared_card_tactics.py); [`scripts/data/supply_action_evaluation.json`](../scripts/data/supply_action_evaluation.json); [`reports/strategies/supply-action-selection-evaluation.html`](../reports/strategies/supply-action-selection-evaluation.html); [#390](https://github.com/jss367/py-overlord/issues/390), [#395](https://github.com/jss367/py-overlord/issues/395), [#396](https://github.com/jss367/py-overlord/issues/396), [#397](https://github.com/jss367/py-overlord/issues/397), [#405](https://github.com/jss367/py-overlord/issues/405) |
| Scheme | Hinterlands | Clean-up topdeck | Targeted regression audit; other interactions unreviewed | Connected/tested: [`dominion/ai/genetic_ai.py`](../dominion/ai/genetic_ai.py) → `choose_card_to_topdeck_for_scheme` | Unreviewed | [`dominion/cards/hinterlands/scheme.py`](../dominion/cards/hinterlands/scheme.py); [`tests/test_kolkata_board_cards.py`](../tests/test_kolkata_board_cards.py); [#394](https://github.com/jss367/py-overlord/issues/394) |
| Spice Merchant | Hinterlands | Optional Treasure trash and mode | Targeted regression audit; other interactions unreviewed | Connected/tested: [`dominion/ai/genetic_ai.py`](../dominion/ai/genetic_ai.py) → `choose_treasure_to_trash_for_spice_merchant`, `choose_spice_merchant_mode` | Unreviewed | [`dominion/cards/hinterlands/spice_merchant.py`](../dominion/cards/hinterlands/spice_merchant.py); [`tests/test_kolkata_board_cards.py`](../tests/test_kolkata_board_cards.py); [#394](https://github.com/jss367/py-overlord/issues/394) |
| Stables | Hinterlands | Optional Treasure discard | Targeted regression audit; other interactions unreviewed | Connected/tested: [`dominion/ai/genetic_ai.py`](../dominion/ai/genetic_ai.py) → `choose_treasure_to_discard_for_stables` | Unreviewed | [`dominion/cards/hinterlands/stables.py`](../dominion/cards/hinterlands/stables.py); [`tests/test_kolkata_board_cards.py`](../tests/test_kolkata_board_cards.py); [#394](https://github.com/jss367/py-overlord/issues/394) |
| Courtier | Intrigue | Reveal and bonus combination | Targeted regression audit; other interactions unreviewed | Needs forwarding for reveal; bonuses connected/tested: [`dominion/ai/genetic_ai.py`](../dominion/ai/genetic_ai.py) → `choose_courtier_reveal`, `choose_courtier_options` | Unreviewed | [`dominion/cards/intrigue/courtier.py`](../dominion/cards/intrigue/courtier.py); [`tests/test_three_unused_kingdoms.py`](../tests/test_three_unused_kingdoms.py); [#344](https://github.com/jss367/py-overlord/issues/344) |
| Ironworks | Intrigue | Mandatory free gain via purchase selector | Targeted regression audit; other interactions unreviewed | Needs context: connected purchase priorities: [`dominion/ai/genetic_ai.py`](../dominion/ai/genetic_ai.py) → `choose_buy` | Needs context: no independent free-gain parameters | [`dominion/cards/intrigue/ironworks.py`](../dominion/cards/intrigue/ironworks.py); [`tests/test_suzhou_board_rules.py`](../tests/test_suzhou_board_rules.py); [#412](https://github.com/jss367/py-overlord/issues/412) |
| Minion | Intrigue | Money vs redraw | Targeted regression audit; other interactions unreviewed | Connected/tested: [`dominion/ai/genetic_ai.py`](../dominion/ai/genetic_ai.py) → `choose_minion_mode` | Unreviewed | [`dominion/cards/intrigue/minion.py`](../dominion/cards/intrigue/minion.py); [`tests/test_three_unused_kingdoms.py`](../tests/test_three_unused_kingdoms.py);  |
| Torturer | Intrigue | Attack mode and discards | Forwarding tests; full response/menu audit remains with #393 | Connected/tested: [`dominion/ai/genetic_ai.py`](../dominion/ai/genetic_ai.py) → `choose_torturer_attack`, `choose_cards_to_discard` | Needs context | [`dominion/cards/intrigue/torturer.py`](../dominion/cards/intrigue/torturer.py); [`tests/test_groundskeeper_margrave.py`](../tests/test_groundskeeper_margrave.py); [#393](https://github.com/jss367/py-overlord/issues/393), [#406](https://github.com/jss367/py-overlord/issues/406), [#408](https://github.com/jss367/py-overlord/issues/408) |
| Barge | Menagerie | Timing / gain destination | Existing card tests; strategy path absent | Needs forwarding: [`dominion/ai/genetic_ai.py`](../dominion/ai/genetic_ai.py) → `should_resolve_barge_now` | Needs context | [`dominion/cards/menagerie/barge.py`](../dominion/cards/menagerie/barge.py); [`tests/test_menagerie_cards.py`](../tests/test_menagerie_cards.py); [#393](https://github.com/jss367/py-overlord/issues/393), [#407](https://github.com/jss367/py-overlord/issues/407) |
| Bounty Hunter | Menagerie | Exile target / first-name bonus | Targeted regression audit; other interactions unreviewed | Connected/tested: [`dominion/ai/genetic_ai.py`](../dominion/ai/genetic_ai.py) → `choose_card_to_exile_for_bounty_hunter` | Evaluated: fixed money panel; no universal improvement | [`dominion/cards/menagerie/bounty_hunter.py`](../dominion/cards/menagerie/bounty_hunter.py); [`tests/test_card_tactics_evaluation.py`](../tests/test_card_tactics_evaluation.py); [`tests/test_genetic_ai_hooks.py`](../tests/test_genetic_ai_hooks.py); [`tests/test_menagerie_cards.py`](../tests/test_menagerie_cards.py); [`scripts/data/card_tactics_screen.json`](../scripts/data/card_tactics_screen.json); [`scripts/data/card_tactics_validation.json`](../scripts/data/card_tactics_validation.json); [`reports/strategies/card-reactions-investment-and-exile-evaluation.html`](../reports/strategies/card-reactions-investment-and-exile-evaluation.html); [#394](https://github.com/jss367/py-overlord/issues/394), [#413](https://github.com/jss367/py-overlord/issues/413) |
| Sleigh | Menagerie | Timing / gain destination | Existing card tests; strategy path absent | Needs forwarding: [`dominion/ai/genetic_ai.py`](../dominion/ai/genetic_ai.py) → `choose_sleigh_reaction` | Needs context | [`dominion/cards/menagerie/sleigh.py`](../dominion/cards/menagerie/sleigh.py); [`tests/test_menagerie_cards.py`](../tests/test_menagerie_cards.py); [#393](https://github.com/jss367/py-overlord/issues/393), [#409](https://github.com/jss367/py-overlord/issues/409), [#410](https://github.com/jss367/py-overlord/issues/410) |
| Quartermaster | Plunder | Free gain / sacrifice / storage | Targeted regression audit; other interactions unreviewed | Connected/tested: [`dominion/ai/genetic_ai.py`](../dominion/ai/genetic_ai.py) → `choose_free_gain`, `choose_quartermaster_option`, `choose_quartermaster_gain`, `quartermaster_take_all` | Evaluated: mixed/regressing fixed panels | [`dominion/cards/plunder/kingdom_cards.py`](../dominion/cards/plunder/kingdom_cards.py); [`tests/test_free_gain_tactics.py`](../tests/test_free_gain_tactics.py); [`tests/test_free_gain_evaluation.py`](../tests/test_free_gain_evaluation.py); [`scripts/data/free_gain_tactics_evaluation-2026-10-08-anvil-adapter.json`](../scripts/data/free_gain_tactics_evaluation-2026-10-08-anvil-adapter.json); [`reports/strategies/free-gains-and-quartermaster-policy-evaluation.html`](../reports/strategies/free-gains-and-quartermaster-policy-evaluation.html); [#391](https://github.com/jss367/py-overlord/issues/391) |
| Captain | Promo | Supply Action target | Targeted menus; open proxy/indirect-play/scheduling defects | Connected/tested: [`dominion/ai/genetic_ai.py`](../dominion/ai/genetic_ai.py) → `choose_captain_target` | Evaluated: fixed non-Duration panel only | [`dominion/cards/promo/captain.py`](../dominion/cards/promo/captain.py); [`tests/test_shared_card_tactics.py`](../tests/test_shared_card_tactics.py); [`scripts/data/supply_action_evaluation.json`](../scripts/data/supply_action_evaluation.json); [`reports/strategies/supply-action-selection-evaluation.html`](../reports/strategies/supply-action-selection-evaluation.html); [#390](https://github.com/jss367/py-overlord/issues/390), [#395](https://github.com/jss367/py-overlord/issues/395), [#396](https://github.com/jss367/py-overlord/issues/396), [#397](https://github.com/jss367/py-overlord/issues/397), [#405](https://github.com/jss367/py-overlord/issues/405) |
| Anvil | Prosperity | Free gain / sacrifice / storage | Targeted regression audit; other interactions unreviewed | Connected/tested: [`dominion/ai/genetic_ai.py`](../dominion/ai/genetic_ai.py) → `choose_free_gain`, `choose_anvil_option`, `choose_anvil_gain`, `choose_anvil_treasure_to_discard` | Evaluated: mixed/regressing fixed panels | [`dominion/cards/prosperity/anvil.py`](../dominion/cards/prosperity/anvil.py); [`tests/test_free_gain_tactics.py`](../tests/test_free_gain_tactics.py); [`tests/test_free_gain_evaluation.py`](../tests/test_free_gain_evaluation.py); [`scripts/data/free_gain_tactics_evaluation-2026-10-08-anvil-adapter.json`](../scripts/data/free_gain_tactics_evaluation-2026-10-08-anvil-adapter.json); [`reports/strategies/free-gains-and-quartermaster-policy-evaluation.html`](../reports/strategies/free-gains-and-quartermaster-policy-evaluation.html); [#391](https://github.com/jss367/py-overlord/issues/391) |
| Clerk | Prosperity | Attack response / start-turn reaction | Targeted regression audit; other interactions unreviewed | Connected/tested: [`dominion/ai/genetic_ai.py`](../dominion/ai/genetic_ai.py) → `choose_card_to_topdeck_for_clerk`, `should_play_clerk_reaction` | Evaluated: fixed money panel; Clerk reaction timing unchanged | [`dominion/cards/prosperity/clerk.py`](../dominion/cards/prosperity/clerk.py); [`tests/test_card_tactics_evaluation.py`](../tests/test_card_tactics_evaluation.py); [`tests/test_genetic_ai_hooks.py`](../tests/test_genetic_ai_hooks.py); [`tests/test_prosperity_cards.py`](../tests/test_prosperity_cards.py); [`scripts/data/card_tactics_screen.json`](../scripts/data/card_tactics_screen.json); [`scripts/data/card_tactics_validation.json`](../scripts/data/card_tactics_validation.json); [`reports/strategies/card-reactions-investment-and-exile-evaluation.html`](../reports/strategies/card-reactions-investment-and-exile-evaluation.html); [#394](https://github.com/jss367/py-overlord/issues/394), [#413](https://github.com/jss367/py-overlord/issues/413) |
| Investment | Prosperity | Mandatory hand trash / self-trash mode | Targeted regression audit; other interactions unreviewed | Connected/tested: [`dominion/ai/genetic_ai.py`](../dominion/ai/genetic_ai.py) → `choose_investment_mode`, `choose_card_to_trash` | Evaluated: fixed money panel; no universal improvement | [`dominion/cards/prosperity/investment.py`](../dominion/cards/prosperity/investment.py); [`tests/test_card_tactics_evaluation.py`](../tests/test_card_tactics_evaluation.py); [`tests/test_genetic_ai_hooks.py`](../tests/test_genetic_ai_hooks.py); [`tests/test_prosperity_cards.py`](../tests/test_prosperity_cards.py); [`scripts/data/card_tactics_screen.json`](../scripts/data/card_tactics_screen.json); [`scripts/data/card_tactics_validation.json`](../scripts/data/card_tactics_validation.json); [`reports/strategies/card-reactions-investment-and-exile-evaluation.html`](../reports/strategies/card-reactions-investment-and-exile-evaluation.html); [#394](https://github.com/jss367/py-overlord/issues/394), [#411](https://github.com/jss367/py-overlord/issues/411), [#413](https://github.com/jss367/py-overlord/issues/413) |
| Watchtower | Prosperity | Gain reaction | Targeted regression audit; other interactions unreviewed | Connected/tested: [`dominion/ai/genetic_ai.py`](../dominion/ai/genetic_ai.py) → `choose_watchtower_reaction` | Evaluated: fixed money panel; no universal improvement | [`dominion/cards/prosperity/watchtower.py`](../dominion/cards/prosperity/watchtower.py); [`tests/test_card_tactics_evaluation.py`](../tests/test_card_tactics_evaluation.py); [`tests/test_genetic_ai_hooks.py`](../tests/test_genetic_ai_hooks.py); [`tests/test_prosperity_cards.py`](../tests/test_prosperity_cards.py); [`scripts/data/card_tactics_screen.json`](../scripts/data/card_tactics_screen.json); [`scripts/data/card_tactics_validation.json`](../scripts/data/card_tactics_validation.json); [`reports/strategies/card-reactions-investment-and-exile-evaluation.html`](../reports/strategies/card-reactions-investment-and-exile-evaluation.html); [#394](https://github.com/jss367/py-overlord/issues/394), [#413](https://github.com/jss367/py-overlord/issues/413) |
| Haven | Seaside | Next-turn set-aside | Targeted regression audit; other interactions unreviewed | Connected/tested: [`dominion/ai/genetic_ai.py`](../dominion/ai/genetic_ai.py) → `choose_card_to_set_aside_for_haven` | Evaluated: fixed kingdom; engine score regressions | [`dominion/cards/seaside/haven.py`](../dominion/cards/seaside/haven.py); [`tests/test_set_aside_tactics.py`](../tests/test_set_aside_tactics.py); [`reports/strategies/trashing-discard-and-next-turn-card-decisions.html`](../reports/strategies/trashing-discard-and-next-turn-card-decisions.html); [#392](https://github.com/jss367/py-overlord/issues/392), [#398](https://github.com/jss367/py-overlord/issues/398) |

## Explicitly unreviewed cards

Each row has unreviewed rules, wiring and tactical quality in this inventory. A source link identifies the implementation to audit, not evidence of correctness.

| Card | Expansion | Decision | Rules | Wiring | Tactics | Source |
| --- | --- | --- | --- | --- | --- | --- |
| Amulet | Adventures | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/adventures/amulet.py`](../dominion/cards/adventures/amulet.py) |
| Bridge Troll | Adventures | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/adventures/bridge_troll.py`](../dominion/cards/adventures/bridge_troll.py) |
| Caravan Guard | Adventures | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/adventures/caravan_guard.py`](../dominion/cards/adventures/caravan_guard.py) |
| Champion | Adventures | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/adventures/page.py`](../dominion/cards/adventures/page.py) |
| Coin of the Realm | Adventures | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/adventures/coin_of_the_realm.py`](../dominion/cards/adventures/coin_of_the_realm.py) |
| Disciple | Adventures | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/adventures/peasant.py`](../dominion/cards/adventures/peasant.py) |
| Distant Lands | Adventures | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/adventures/distant_lands.py`](../dominion/cards/adventures/distant_lands.py) |
| Dungeon | Adventures | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/adventures/dungeon.py`](../dominion/cards/adventures/dungeon.py) |
| Duplicate | Adventures | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/adventures/duplicate.py`](../dominion/cards/adventures/duplicate.py) |
| Fugitive | Adventures | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/adventures/peasant.py`](../dominion/cards/adventures/peasant.py) |
| Giant | Adventures | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/adventures/giant.py`](../dominion/cards/adventures/giant.py) |
| Guide | Adventures | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/adventures/guide.py`](../dominion/cards/adventures/guide.py) |
| Haunted Woods | Adventures | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/adventures/haunted_woods.py`](../dominion/cards/adventures/haunted_woods.py) |
| Hero | Adventures | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/adventures/page.py`](../dominion/cards/adventures/page.py) |
| Hireling | Adventures | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/adventures/hireling.py`](../dominion/cards/adventures/hireling.py) |
| Lost City | Adventures | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/adventures/lost_city.py`](../dominion/cards/adventures/lost_city.py) |
| Magpie | Adventures | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/adventures/magpie.py`](../dominion/cards/adventures/magpie.py) |
| Messenger | Adventures | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/adventures/messenger.py`](../dominion/cards/adventures/messenger.py) |
| Miser | Adventures | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/adventures/miser.py`](../dominion/cards/adventures/miser.py) |
| Page | Adventures | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/adventures/page.py`](../dominion/cards/adventures/page.py) |
| Peasant | Adventures | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/adventures/peasant.py`](../dominion/cards/adventures/peasant.py) |
| Port | Adventures | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/adventures/port.py`](../dominion/cards/adventures/port.py) |
| Ranger | Adventures | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/adventures/ranger.py`](../dominion/cards/adventures/ranger.py) |
| Ratcatcher | Adventures | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/adventures/ratcatcher.py`](../dominion/cards/adventures/ratcatcher.py) |
| Raze | Adventures | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/adventures/raze.py`](../dominion/cards/adventures/raze.py) |
| Relic | Adventures | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/adventures/relic.py`](../dominion/cards/adventures/relic.py) |
| Royal Carriage | Adventures | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/adventures/royal_carriage.py`](../dominion/cards/adventures/royal_carriage.py) |
| Soldier | Adventures | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/adventures/peasant.py`](../dominion/cards/adventures/peasant.py) |
| Storyteller | Adventures | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/adventures/storyteller.py`](../dominion/cards/adventures/storyteller.py) |
| Swamp Hag | Adventures | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/adventures/swamp_hag.py`](../dominion/cards/adventures/swamp_hag.py) |
| Teacher | Adventures | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/adventures/peasant.py`](../dominion/cards/adventures/peasant.py) |
| Transmogrify | Adventures | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/adventures/transmogrify.py`](../dominion/cards/adventures/transmogrify.py) |
| Treasure Hunter | Adventures | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/adventures/page.py`](../dominion/cards/adventures/page.py) |
| Treasure Trove | Adventures | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/adventures/treasure_trove.py`](../dominion/cards/adventures/treasure_trove.py) |
| Warrior | Adventures | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/adventures/page.py`](../dominion/cards/adventures/page.py) |
| Wine Merchant | Adventures | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/adventures/wine_merchant.py`](../dominion/cards/adventures/wine_merchant.py) |
| Alchemist | Alchemy | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/alchemy/alchemist.py`](../dominion/cards/alchemy/alchemist.py) |
| Apothecary | Alchemy | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/alchemy/apothecary.py`](../dominion/cards/alchemy/apothecary.py) |
| Apprentice | Alchemy | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/alchemy/apprentice.py`](../dominion/cards/alchemy/apprentice.py) |
| Familiar | Alchemy | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/alchemy/familiar.py`](../dominion/cards/alchemy/familiar.py) |
| Golem | Alchemy | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/alchemy/golem.py`](../dominion/cards/alchemy/golem.py) |
| Herbalist | Alchemy | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/alchemy/herbalist.py`](../dominion/cards/alchemy/herbalist.py) |
| Philosopher's Stone | Alchemy | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/alchemy/philosophers_stone.py`](../dominion/cards/alchemy/philosophers_stone.py) |
| Potion | Alchemy | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/alchemy/potion.py`](../dominion/cards/alchemy/potion.py) |
| Scrying Pool | Alchemy | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/alchemy/scrying_pool.py`](../dominion/cards/alchemy/scrying_pool.py) |
| Transmute | Alchemy | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/alchemy/transmute.py`](../dominion/cards/alchemy/transmute.py) |
| University | Alchemy | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/alchemy/university.py`](../dominion/cards/alchemy/university.py) |
| Vineyard | Alchemy | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/alchemy/vineyard.py`](../dominion/cards/alchemy/vineyard.py) |
| Acolyte | Allies | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/allies/augurs.py`](../dominion/cards/allies/augurs.py) |
| Archer | Allies | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/allies/clashes.py`](../dominion/cards/allies/clashes.py) |
| Barbarian | Allies | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/allies/barbarian.py`](../dominion/cards/allies/barbarian.py) |
| Battle Plan | Allies | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/allies/clashes.py`](../dominion/cards/allies/clashes.py) |
| Bauble | Allies | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/allies/standalone.py`](../dominion/cards/allies/standalone.py) |
| Blacksmith | Allies | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/allies/townsfolk.py`](../dominion/cards/allies/townsfolk.py) |
| Broker | Allies | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/allies/standalone.py`](../dominion/cards/allies/standalone.py) |
| Capital City | Allies | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/allies/standalone.py`](../dominion/cards/allies/standalone.py) |
| Carpenter | Allies | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/allies/standalone.py`](../dominion/cards/allies/standalone.py) |
| Conjurer | Allies | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/allies/wizards.py`](../dominion/cards/allies/wizards.py) |
| Contract | Allies | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/allies/standalone.py`](../dominion/cards/allies/standalone.py) |
| Distant Shore | Allies | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/allies/odysseys.py`](../dominion/cards/allies/odysseys.py) |
| Elder | Allies | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/allies/townsfolk.py`](../dominion/cards/allies/townsfolk.py) |
| Emissary | Allies | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/allies/standalone.py`](../dominion/cards/allies/standalone.py) |
| Galleria | Allies | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/allies/standalone.py`](../dominion/cards/allies/standalone.py) |
| Garrison | Allies | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/allies/forts.py`](../dominion/cards/allies/forts.py) |
| Guildmaster | Allies | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/allies/standalone.py`](../dominion/cards/allies/standalone.py) |
| Herb Gatherer | Allies | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/allies/augurs.py`](../dominion/cards/allies/augurs.py) |
| Highwayman | Allies | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/plunder/highwayman.py`](../dominion/cards/plunder/highwayman.py) |
| Hill Fort | Allies | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/allies/forts.py`](../dominion/cards/allies/forts.py) |
| Hunter | Allies | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/allies/standalone.py`](../dominion/cards/allies/standalone.py) |
| Importer | Allies | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/allies/standalone.py`](../dominion/cards/allies/standalone.py) |
| Innkeeper | Allies | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/allies/standalone.py`](../dominion/cards/allies/standalone.py) |
| Lich | Allies | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/allies/wizards.py`](../dominion/cards/allies/wizards.py) |
| Marquis | Allies | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/allies/standalone.py`](../dominion/cards/allies/standalone.py) |
| Merchant Camp | Allies | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/allies/standalone.py`](../dominion/cards/allies/standalone.py) |
| Miller | Allies | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/allies/townsfolk.py`](../dominion/cards/allies/townsfolk.py) |
| Modify | Allies | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/allies/modify.py`](../dominion/cards/allies/modify.py) |
| Old Map | Allies | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/allies/odysseys.py`](../dominion/cards/allies/odysseys.py) |
| Royal Galley | Allies | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/allies/standalone.py`](../dominion/cards/allies/standalone.py) |
| Sentinel | Allies | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/allies/standalone.py`](../dominion/cards/allies/standalone.py) |
| Sibyl | Allies | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/allies/augurs.py`](../dominion/cards/allies/augurs.py) |
| Skirmisher | Allies | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/allies/standalone.py`](../dominion/cards/allies/standalone.py) |
| Sorcerer | Allies | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/allies/wizards.py`](../dominion/cards/allies/wizards.py) |
| Sorceress | Allies | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/allies/augurs.py`](../dominion/cards/allies/augurs.py) |
| Specialist | Allies | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/allies/standalone.py`](../dominion/cards/allies/standalone.py) |
| Stronghold | Allies | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/allies/forts.py`](../dominion/cards/allies/forts.py) |
| Student | Allies | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/allies/wizards.py`](../dominion/cards/allies/wizards.py) |
| Sunken Treasure | Allies | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/allies/odysseys.py`](../dominion/cards/allies/odysseys.py) |
| Swap | Allies | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/allies/standalone.py`](../dominion/cards/allies/standalone.py) |
| Sycophant | Allies | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/allies/standalone.py`](../dominion/cards/allies/standalone.py) |
| Tent | Allies | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/allies/forts.py`](../dominion/cards/allies/forts.py) |
| Territory | Allies | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/allies/clashes.py`](../dominion/cards/allies/clashes.py) |
| Town | Allies | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/allies/standalone.py`](../dominion/cards/allies/standalone.py) |
| Town Crier | Allies | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/allies/townsfolk.py`](../dominion/cards/allies/townsfolk.py) |
| Underling | Allies | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/allies/standalone.py`](../dominion/cards/allies/standalone.py) |
| Voyage | Allies | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/allies/odysseys.py`](../dominion/cards/allies/odysseys.py) |
| Warlord | Allies | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/allies/clashes.py`](../dominion/cards/allies/clashes.py) |
| Adventurer | Base | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/base_set/adventurer.py`](../dominion/cards/base_set/adventurer.py) |
| Artisan | Base | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/base_set/artisan.py`](../dominion/cards/base_set/artisan.py) |
| Bandit | Base | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/base_set/bandit.py`](../dominion/cards/base_set/bandit.py) |
| Bureaucrat | Base | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/base_set/bureaucrat.py`](../dominion/cards/base_set/bureaucrat.py) |
| Cellar | Base | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/base_set/cellar.py`](../dominion/cards/base_set/cellar.py) |
| Chancellor | Base | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/base_set/chancellor.py`](../dominion/cards/base_set/chancellor.py) |
| Copper | Base | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/treasures.py`](../dominion/cards/treasures.py) |
| Council Room | Base | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/base_set/council_room.py`](../dominion/cards/base_set/council_room.py) |
| Curse | Base | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/victory.py`](../dominion/cards/victory.py) |
| Duchy | Base | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/victory.py`](../dominion/cards/victory.py) |
| Estate | Base | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/victory.py`](../dominion/cards/victory.py) |
| Feast | Base | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/base_set/feast.py`](../dominion/cards/base_set/feast.py) |
| Festival | Base | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/base_set/festival.py`](../dominion/cards/base_set/festival.py) |
| Gardens | Base | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/base_set/gardens.py`](../dominion/cards/base_set/gardens.py) |
| Gold | Base | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/treasures.py`](../dominion/cards/treasures.py) |
| Harbinger | Base | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/base_set/harbinger.py`](../dominion/cards/base_set/harbinger.py) |
| Laboratory | Base | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/base_set/laboratory.py`](../dominion/cards/base_set/laboratory.py) |
| Library | Base | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/base_set/library.py`](../dominion/cards/base_set/library.py) |
| Market | Base | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/base_set/market.py`](../dominion/cards/base_set/market.py) |
| Merchant | Base | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/base_set/merchant.py`](../dominion/cards/base_set/merchant.py) |
| Militia | Base | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/base_set/militia.py`](../dominion/cards/base_set/militia.py) |
| Mine | Base | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/base_set/mine.py`](../dominion/cards/base_set/mine.py) |
| Moat | Base | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/base_set/moat.py`](../dominion/cards/base_set/moat.py) |
| Poacher | Base | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/base_set/poacher.py`](../dominion/cards/base_set/poacher.py) |
| Province | Base | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/victory.py`](../dominion/cards/victory.py) |
| Sentry | Base | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/base_set/sentry.py`](../dominion/cards/base_set/sentry.py) |
| Silver | Base | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/treasures.py`](../dominion/cards/treasures.py) |
| Smithy | Base | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/base_set/smithy.py`](../dominion/cards/base_set/smithy.py) |
| Spy | Base | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/base_set/spy.py`](../dominion/cards/base_set/spy.py) |
| Thief | Base | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/base_set/thief.py`](../dominion/cards/base_set/thief.py) |
| Throne Room | Base | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/base_set/throne_room.py`](../dominion/cards/base_set/throne_room.py) |
| Vassal | Base | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/base_set/vassal.py`](../dominion/cards/base_set/vassal.py) |
| Village | Base | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/base_set/village.py`](../dominion/cards/base_set/village.py) |
| Witch | Base | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/base_set/witch.py`](../dominion/cards/base_set/witch.py) |
| Woodcutter | Base | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/base_set/woodcutter.py`](../dominion/cards/base_set/woodcutter.py) |
| Bag of Gold | Cornucopia | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/cornucopia/prizes.py`](../dominion/cards/cornucopia/prizes.py) |
| Carnival | Cornucopia | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/cornucopia/carnival.py`](../dominion/cards/cornucopia/carnival.py) |
| Coronet | Cornucopia | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/cornucopia/rewards.py`](../dominion/cards/cornucopia/rewards.py) |
| Courser | Cornucopia | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/cornucopia/rewards.py`](../dominion/cards/cornucopia/rewards.py) |
| Demesne | Cornucopia | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/cornucopia/rewards.py`](../dominion/cards/cornucopia/rewards.py) |
| Diadem | Cornucopia | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/cornucopia/prizes.py`](../dominion/cards/cornucopia/prizes.py) |
| Fairgrounds | Cornucopia | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/cornucopia/fairgrounds.py`](../dominion/cards/cornucopia/fairgrounds.py) |
| Farmhands | Cornucopia | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/cornucopia/farmhands.py`](../dominion/cards/cornucopia/farmhands.py) |
| Farming Village | Cornucopia | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/cornucopia/farming_village.py`](../dominion/cards/cornucopia/farming_village.py) |
| Farrier | Cornucopia | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/cornucopia/farrier.py`](../dominion/cards/cornucopia/farrier.py) |
| Ferryman | Cornucopia | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/cornucopia/ferryman.py`](../dominion/cards/cornucopia/ferryman.py) |
| Followers | Cornucopia | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/cornucopia/prizes.py`](../dominion/cards/cornucopia/prizes.py) |
| Footpad | Cornucopia | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/cornucopia/footpad.py`](../dominion/cards/cornucopia/footpad.py) |
| Fortune Teller | Cornucopia | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/cornucopia/fortune_teller.py`](../dominion/cards/cornucopia/fortune_teller.py) |
| Hamlet | Cornucopia | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/cornucopia/hamlet.py`](../dominion/cards/cornucopia/hamlet.py) |
| Harvest | Cornucopia | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/cornucopia/harvest.py`](../dominion/cards/cornucopia/harvest.py) |
| Horn of Plenty | Cornucopia | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/cornucopia/horn_of_plenty.py`](../dominion/cards/cornucopia/horn_of_plenty.py) |
| Horse Traders | Cornucopia | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/cornucopia/horse_traders.py`](../dominion/cards/cornucopia/horse_traders.py) |
| Housecarl | Cornucopia | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/cornucopia/rewards.py`](../dominion/cards/cornucopia/rewards.py) |
| Huge Turnip | Cornucopia | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/cornucopia/rewards.py`](../dominion/cards/cornucopia/rewards.py) |
| Hunting Party | Cornucopia | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/cornucopia/hunting_party.py`](../dominion/cards/cornucopia/hunting_party.py) |
| Infirmary | Cornucopia | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/cornucopia/infirmary.py`](../dominion/cards/cornucopia/infirmary.py) |
| Jester | Cornucopia | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/cornucopia/jester.py`](../dominion/cards/cornucopia/jester.py) |
| Joust | Cornucopia | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/cornucopia/joust.py`](../dominion/cards/cornucopia/joust.py) |
| Menagerie | Cornucopia | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/cornucopia/menagerie.py`](../dominion/cards/cornucopia/menagerie.py) |
| Princess | Cornucopia | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/cornucopia/prizes.py`](../dominion/cards/cornucopia/prizes.py) |
| Remake | Cornucopia | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/cornucopia/remake.py`](../dominion/cards/cornucopia/remake.py) |
| Renown | Cornucopia | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/cornucopia/rewards.py`](../dominion/cards/cornucopia/rewards.py) |
| Shop | Cornucopia | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/cornucopia/shop.py`](../dominion/cards/cornucopia/shop.py) |
| Tournament | Cornucopia | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/cornucopia/tournament.py`](../dominion/cards/cornucopia/tournament.py) |
| Trusty Steed | Cornucopia | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/cornucopia/prizes.py`](../dominion/cards/cornucopia/prizes.py) |
| Young Witch | Cornucopia | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/cornucopia/young_witch.py`](../dominion/cards/cornucopia/young_witch.py) |
| Abandoned Mine | Dark Ages | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/dark_ages/ruins.py`](../dominion/cards/dark_ages/ruins.py) |
| Altar | Dark Ages | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/dark_ages/altar.py`](../dominion/cards/dark_ages/altar.py) |
| Bandit Camp | Dark Ages | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/dark_ages/bandit_camp.py`](../dominion/cards/dark_ages/bandit_camp.py) |
| Beggar | Dark Ages | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/dark_ages/beggar.py`](../dominion/cards/dark_ages/beggar.py) |
| Catacombs | Dark Ages | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/dark_ages/catacombs.py`](../dominion/cards/dark_ages/catacombs.py) |
| Count | Dark Ages | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/dark_ages/count.py`](../dominion/cards/dark_ages/count.py) |
| Cultist | Dark Ages | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/dark_ages/cultist.py`](../dominion/cards/dark_ages/cultist.py) |
| Death Cart | Dark Ages | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/dark_ages/death_cart.py`](../dominion/cards/dark_ages/death_cart.py) |
| Feodum | Dark Ages | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/dark_ages/feodum.py`](../dominion/cards/dark_ages/feodum.py) |
| Forager | Dark Ages | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/dark_ages/forager.py`](../dominion/cards/dark_ages/forager.py) |
| Fortress | Dark Ages | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/dark_ages/fortress.py`](../dominion/cards/dark_ages/fortress.py) |
| Graverobber | Dark Ages | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/dark_ages/graverobber.py`](../dominion/cards/dark_ages/graverobber.py) |
| Hermit | Dark Ages | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/dark_ages/hermit.py`](../dominion/cards/dark_ages/hermit.py) |
| Hovel | Dark Ages | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/dark_ages/shelters.py`](../dominion/cards/dark_ages/shelters.py) |
| Hunting Grounds | Dark Ages | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/dark_ages/hunting_grounds.py`](../dominion/cards/dark_ages/hunting_grounds.py) |
| Ironmonger | Dark Ages | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/dark_ages/ironmonger.py`](../dominion/cards/dark_ages/ironmonger.py) |
| Madman | Dark Ages | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/dark_ages/madman.py`](../dominion/cards/dark_ages/madman.py) |
| Marauder | Dark Ages | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/dark_ages/marauder.py`](../dominion/cards/dark_ages/marauder.py) |
| Market Square | Dark Ages | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/dark_ages/market_square.py`](../dominion/cards/dark_ages/market_square.py) |
| Mercenary | Dark Ages | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/dark_ages/mercenary.py`](../dominion/cards/dark_ages/mercenary.py) |
| Mystic | Dark Ages | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/dark_ages/mystic.py`](../dominion/cards/dark_ages/mystic.py) |
| Necropolis | Dark Ages | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/dark_ages/shelters.py`](../dominion/cards/dark_ages/shelters.py) |
| Overgrown Estate | Dark Ages | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/dark_ages/shelters.py`](../dominion/cards/dark_ages/shelters.py) |
| Pillage | Dark Ages | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/dark_ages/pillage.py`](../dominion/cards/dark_ages/pillage.py) |
| Poor House | Dark Ages | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/dark_ages/poor_house.py`](../dominion/cards/dark_ages/poor_house.py) |
| Procession | Dark Ages | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/dark_ages/procession.py`](../dominion/cards/dark_ages/procession.py) |
| Rats | Dark Ages | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/dark_ages/rats.py`](../dominion/cards/dark_ages/rats.py) |
| Rebuild | Dark Ages | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/dark_ages/rebuild.py`](../dominion/cards/dark_ages/rebuild.py) |
| Ruined Library | Dark Ages | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/dark_ages/ruins.py`](../dominion/cards/dark_ages/ruins.py) |
| Ruined Market | Dark Ages | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/dark_ages/ruins.py`](../dominion/cards/dark_ages/ruins.py) |
| Ruined Village | Dark Ages | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/dark_ages/ruins.py`](../dominion/cards/dark_ages/ruins.py) |
| Ruins | Dark Ages | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/dark_ages/ruins.py`](../dominion/cards/dark_ages/ruins.py) |
| Sage | Dark Ages | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/dark_ages/sage.py`](../dominion/cards/dark_ages/sage.py) |
| Scavenger | Dark Ages | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/dark_ages/scavenger.py`](../dominion/cards/dark_ages/scavenger.py) |
| Spoils | Dark Ages | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/dark_ages/spoils.py`](../dominion/cards/dark_ages/spoils.py) |
| Squire | Dark Ages | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/dark_ages/squire.py`](../dominion/cards/dark_ages/squire.py) |
| Storeroom | Dark Ages | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/dark_ages/storeroom.py`](../dominion/cards/dark_ages/storeroom.py) |
| Survivors | Dark Ages | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/dark_ages/ruins.py`](../dominion/cards/dark_ages/ruins.py) |
| Urchin | Dark Ages | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/dark_ages/urchin.py`](../dominion/cards/dark_ages/urchin.py) |
| Vagrant | Dark Ages | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/dark_ages/vagrant.py`](../dominion/cards/dark_ages/vagrant.py) |
| Wandering Minstrel | Dark Ages | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/hinterlands/wandering_minstrel.py`](../dominion/cards/hinterlands/wandering_minstrel.py) |
| Archive | Empires | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/empires/archive.py`](../dominion/cards/empires/archive.py) |
| Bustling Village | Empires | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/empires/bustling_village.py`](../dominion/cards/empires/bustling_village.py) |
| Capital | Empires | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/empires/capital.py`](../dominion/cards/empires/capital.py) |
| Catapult | Empires | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/empires/catapult.py`](../dominion/cards/empires/catapult.py) |
| Chariot Race | Empires | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/empires/chariot_race.py`](../dominion/cards/empires/chariot_race.py) |
| Charm | Empires | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/empires/charm.py`](../dominion/cards/empires/charm.py) |
| City Quarter | Empires | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/empires/city_quarter.py`](../dominion/cards/empires/city_quarter.py) |
| Crown | Empires | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/empires/crown.py`](../dominion/cards/empires/crown.py) |
| Crumbling Castle | Empires | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/empires/castles.py`](../dominion/cards/empires/castles.py) |
| Emporium | Empires | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/empires/emporium.py`](../dominion/cards/empires/emporium.py) |
| Encampment | Empires | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/empires/encampment.py`](../dominion/cards/empires/encampment.py) |
| Enchantress | Empires | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/empires/enchantress.py`](../dominion/cards/empires/enchantress.py) |
| Farmers' Market | Empires | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/empires/farmers_market.py`](../dominion/cards/empires/farmers_market.py) |
| Fortune | Empires | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/empires/fortune.py`](../dominion/cards/empires/fortune.py) |
| Forum | Empires | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/empires/forum.py`](../dominion/cards/empires/forum.py) |
| Gladiator | Empires | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/empires/gladiator.py`](../dominion/cards/empires/gladiator.py) |
| Grand Castle | Empires | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/empires/castles.py`](../dominion/cards/empires/castles.py) |
| Groundskeeper | Empires | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/empires/groundskeeper.py`](../dominion/cards/empires/groundskeeper.py) |
| Haunted Castle | Empires | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/empires/castles.py`](../dominion/cards/empires/castles.py) |
| Humble Castle | Empires | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/empires/castles.py`](../dominion/cards/empires/castles.py) |
| King's Castle | Empires | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/empires/castles.py`](../dominion/cards/empires/castles.py) |
| Legionary | Empires | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/empires/legionary.py`](../dominion/cards/empires/legionary.py) |
| Opulent Castle | Empires | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/empires/castles.py`](../dominion/cards/empires/castles.py) |
| Patrician | Empires | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/empires/patrician.py`](../dominion/cards/empires/patrician.py) |
| Plunder | Empires | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/empires/plunder.py`](../dominion/cards/empires/plunder.py) |
| Rocks | Empires | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/empires/rocks.py`](../dominion/cards/empires/rocks.py) |
| Royal Blacksmith | Empires | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/empires/royal_blacksmith.py`](../dominion/cards/empires/royal_blacksmith.py) |
| Sacrifice | Empires | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/empires/sacrifice.py`](../dominion/cards/empires/sacrifice.py) |
| Settlers | Empires | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/empires/settlers.py`](../dominion/cards/empires/settlers.py) |
| Small Castle | Empires | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/empires/castles.py`](../dominion/cards/empires/castles.py) |
| Sprawling Castle | Empires | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/empires/castles.py`](../dominion/cards/empires/castles.py) |
| Temple | Empires | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/empires/temple.py`](../dominion/cards/empires/temple.py) |
| Villa | Empires | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/empires/villa.py`](../dominion/cards/empires/villa.py) |
| Wild Hunt | Empires | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/empires/wild_hunt.py`](../dominion/cards/empires/wild_hunt.py) |
| Advisor | Guilds | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/guilds/advisor.py`](../dominion/cards/guilds/advisor.py) |
| Baker | Guilds | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/guilds/baker.py`](../dominion/cards/guilds/baker.py) |
| Butcher | Guilds | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/guilds/butcher.py`](../dominion/cards/guilds/butcher.py) |
| Candlestick Maker | Guilds | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/guilds/candlestick_maker.py`](../dominion/cards/guilds/candlestick_maker.py) |
| Doctor | Guilds | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/guilds/doctor.py`](../dominion/cards/guilds/doctor.py) |
| Herald | Guilds | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/guilds/herald.py`](../dominion/cards/guilds/herald.py) |
| Journeyman | Guilds | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/guilds/journeyman.py`](../dominion/cards/guilds/journeyman.py) |
| Masterpiece | Guilds | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/guilds/masterpiece.py`](../dominion/cards/guilds/masterpiece.py) |
| Merchant Guild | Guilds | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/guilds/merchant_guild.py`](../dominion/cards/guilds/merchant_guild.py) |
| Plaza | Guilds | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/guilds/plaza.py`](../dominion/cards/guilds/plaza.py) |
| Soothsayer | Guilds | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/guilds/soothsayer.py`](../dominion/cards/guilds/soothsayer.py) |
| Stonemason | Guilds | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/guilds/stonemason.py`](../dominion/cards/guilds/stonemason.py) |
| Taxman | Guilds | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/guilds/taxman.py`](../dominion/cards/guilds/taxman.py) |
| Berserker | Hinterlands | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/hinterlands/berserker.py`](../dominion/cards/hinterlands/berserker.py) |
| Border Village | Hinterlands | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/hinterlands/border_village.py`](../dominion/cards/hinterlands/border_village.py) |
| Cache | Hinterlands | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/hinterlands/cache.py`](../dominion/cards/hinterlands/cache.py) |
| Cartographer | Hinterlands | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/hinterlands/cartographer.py`](../dominion/cards/hinterlands/cartographer.py) |
| Cauldron | Hinterlands | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/hinterlands/cauldron.py`](../dominion/cards/hinterlands/cauldron.py) |
| Crossroads | Hinterlands | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/hinterlands/crossroads.py`](../dominion/cards/hinterlands/crossroads.py) |
| Develop | Hinterlands | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/hinterlands/develop.py`](../dominion/cards/hinterlands/develop.py) |
| Duchess | Hinterlands | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/hinterlands/duchess.py`](../dominion/cards/hinterlands/duchess.py) |
| Embassy | Hinterlands | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/hinterlands/embassy.py`](../dominion/cards/hinterlands/embassy.py) |
| Farmland | Hinterlands | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/hinterlands/farmland.py`](../dominion/cards/hinterlands/farmland.py) |
| Fool's Gold | Hinterlands | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/hinterlands/fools_gold.py`](../dominion/cards/hinterlands/fools_gold.py) |
| Guard Dog | Hinterlands | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/hinterlands/guard_dog.py`](../dominion/cards/hinterlands/guard_dog.py) |
| Haggler | Hinterlands | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/hinterlands/haggler.py`](../dominion/cards/hinterlands/haggler.py) |
| Highway | Hinterlands | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/hinterlands/highway.py`](../dominion/cards/hinterlands/highway.py) |
| Ill-Gotten Gains | Hinterlands | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/hinterlands/ill_gotten_gains.py`](../dominion/cards/hinterlands/ill_gotten_gains.py) |
| Inn | Hinterlands | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/hinterlands/inn.py`](../dominion/cards/hinterlands/inn.py) |
| Jack of All Trades | Hinterlands | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/hinterlands/jack_of_all_trades.py`](../dominion/cards/hinterlands/jack_of_all_trades.py) |
| Mandarin | Hinterlands | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/hinterlands/mandarin.py`](../dominion/cards/hinterlands/mandarin.py) |
| Margrave | Hinterlands | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/hinterlands/margrave.py`](../dominion/cards/hinterlands/margrave.py) |
| Noble Brigand | Hinterlands | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/hinterlands/noble_brigand.py`](../dominion/cards/hinterlands/noble_brigand.py) |
| Nomad Camp | Hinterlands | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/hinterlands/nomad_camp.py`](../dominion/cards/hinterlands/nomad_camp.py) |
| Nomads | Hinterlands | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/hinterlands/nomads.py`](../dominion/cards/hinterlands/nomads.py) |
| Oasis | Hinterlands | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/hinterlands/oasis.py`](../dominion/cards/hinterlands/oasis.py) |
| Oracle | Hinterlands | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/hinterlands/oracle.py`](../dominion/cards/hinterlands/oracle.py) |
| Silk Road | Hinterlands | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/hinterlands/silk_road.py`](../dominion/cards/hinterlands/silk_road.py) |
| Souk | Hinterlands | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/hinterlands/souk.py`](../dominion/cards/hinterlands/souk.py) |
| Trader | Hinterlands | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/hinterlands/trader.py`](../dominion/cards/hinterlands/trader.py) |
| Trail | Hinterlands | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/hinterlands/trail.py`](../dominion/cards/hinterlands/trail.py) |
| Tunnel | Hinterlands | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/hinterlands/tunnel.py`](../dominion/cards/hinterlands/tunnel.py) |
| Weaver | Hinterlands | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/hinterlands/weaver.py`](../dominion/cards/hinterlands/weaver.py) |
| Wheelwright | Hinterlands | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/hinterlands/wheelwright.py`](../dominion/cards/hinterlands/wheelwright.py) |
| Witch's Hut | Hinterlands | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/hinterlands/witchs_hut.py`](../dominion/cards/hinterlands/witchs_hut.py) |
| Baron | Intrigue | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/intrigue/baron.py`](../dominion/cards/intrigue/baron.py) |
| Bridge | Intrigue | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/intrigue/bridge.py`](../dominion/cards/intrigue/bridge.py) |
| Conspirator | Intrigue | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/intrigue/conspirator.py`](../dominion/cards/intrigue/conspirator.py) |
| Coppersmith | Intrigue | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/intrigue/coppersmith.py`](../dominion/cards/intrigue/coppersmith.py) |
| Courtyard | Intrigue | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/intrigue/courtyard.py`](../dominion/cards/intrigue/courtyard.py) |
| Diplomat | Intrigue | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/intrigue/diplomat.py`](../dominion/cards/intrigue/diplomat.py) |
| Duke | Intrigue | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/intrigue/duke.py`](../dominion/cards/intrigue/duke.py) |
| Farm | Intrigue | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/intrigue/farm.py`](../dominion/cards/intrigue/farm.py) |
| Great Hall | Intrigue | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/intrigue/great_hall.py`](../dominion/cards/intrigue/great_hall.py) |
| Lurker | Intrigue | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/intrigue/lurker.py`](../dominion/cards/intrigue/lurker.py) |
| Masquerade | Intrigue | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/intrigue/masquerade.py`](../dominion/cards/intrigue/masquerade.py) |
| Mill | Intrigue | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/hinterlands/mill.py`](../dominion/cards/hinterlands/mill.py) |
| Mining Village | Intrigue | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/intrigue/mining_village.py`](../dominion/cards/intrigue/mining_village.py) |
| Nobles | Intrigue | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/intrigue/nobles.py`](../dominion/cards/intrigue/nobles.py) |
| Patrol | Intrigue | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/intrigue/patrol.py`](../dominion/cards/intrigue/patrol.py) |
| Pawn | Intrigue | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/intrigue/pawn.py`](../dominion/cards/intrigue/pawn.py) |
| Replace | Intrigue | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/intrigue/replace.py`](../dominion/cards/intrigue/replace.py) |
| Saboteur | Intrigue | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/intrigue/saboteur.py`](../dominion/cards/intrigue/saboteur.py) |
| Scout | Intrigue | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/intrigue/scout.py`](../dominion/cards/intrigue/scout.py) |
| Secret Chamber | Intrigue | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/intrigue/secret_chamber.py`](../dominion/cards/intrigue/secret_chamber.py) |
| Secret Passage | Intrigue | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/intrigue/secret_passage.py`](../dominion/cards/intrigue/secret_passage.py) |
| Shanty Town | Intrigue | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/intrigue/shanty_town.py`](../dominion/cards/intrigue/shanty_town.py) |
| Steward | Intrigue | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/intrigue/steward.py`](../dominion/cards/intrigue/steward.py) |
| Swindler | Intrigue | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/intrigue/swindler.py`](../dominion/cards/intrigue/swindler.py) |
| Trading Post | Intrigue | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/seaside/trading_post.py`](../dominion/cards/seaside/trading_post.py) |
| Tribute | Intrigue | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/intrigue/tribute.py`](../dominion/cards/intrigue/tribute.py) |
| Upgrade | Intrigue | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/intrigue/upgrade.py`](../dominion/cards/intrigue/upgrade.py) |
| Wishing Well | Intrigue | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/intrigue/wishing_well.py`](../dominion/cards/intrigue/wishing_well.py) |
| Animal Fair | Menagerie | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/menagerie/animal_fair.py`](../dominion/cards/menagerie/animal_fair.py) |
| Black Cat | Menagerie | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/menagerie/black_cat.py`](../dominion/cards/menagerie/black_cat.py) |
| Camel Train | Menagerie | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/menagerie/camel_train.py`](../dominion/cards/menagerie/camel_train.py) |
| Cardinal | Menagerie | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/menagerie/cardinal.py`](../dominion/cards/menagerie/cardinal.py) |
| Cavalry | Menagerie | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/menagerie/cavalry.py`](../dominion/cards/menagerie/cavalry.py) |
| Coven | Menagerie | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/menagerie/coven.py`](../dominion/cards/menagerie/coven.py) |
| Destrier | Menagerie | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/menagerie/destrier.py`](../dominion/cards/menagerie/destrier.py) |
| Displace | Menagerie | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/menagerie/displace.py`](../dominion/cards/menagerie/displace.py) |
| Falconer | Menagerie | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/menagerie/falconer.py`](../dominion/cards/menagerie/falconer.py) |
| Fisherman | Menagerie | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/plunder/fisherman.py`](../dominion/cards/plunder/fisherman.py) |
| Gatekeeper | Menagerie | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/menagerie/gatekeeper.py`](../dominion/cards/menagerie/gatekeeper.py) |
| Goatherd | Menagerie | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/menagerie/goatherd.py`](../dominion/cards/menagerie/goatherd.py) |
| Groom | Menagerie | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/menagerie/groom.py`](../dominion/cards/menagerie/groom.py) |
| Horse | Menagerie | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/menagerie/horse.py`](../dominion/cards/menagerie/horse.py) |
| Hostelry | Menagerie | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/menagerie/hostelry.py`](../dominion/cards/menagerie/hostelry.py) |
| Hunting Lodge | Menagerie | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/menagerie/hunting_lodge.py`](../dominion/cards/menagerie/hunting_lodge.py) |
| Kiln | Menagerie | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/menagerie/kiln.py`](../dominion/cards/menagerie/kiln.py) |
| Livery | Menagerie | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/menagerie/livery.py`](../dominion/cards/menagerie/livery.py) |
| Mastermind | Menagerie | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/menagerie/mastermind.py`](../dominion/cards/menagerie/mastermind.py) |
| Paddock | Menagerie | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/menagerie/paddock.py`](../dominion/cards/menagerie/paddock.py) |
| Sanctuary | Menagerie | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/menagerie/sanctuary.py`](../dominion/cards/menagerie/sanctuary.py) |
| Scrap | Menagerie | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/menagerie/scrap.py`](../dominion/cards/menagerie/scrap.py) |
| Sheepdog | Menagerie | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/menagerie/sheepdog.py`](../dominion/cards/menagerie/sheepdog.py) |
| Snowy Village | Menagerie | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/promo/snowy_village.py`](../dominion/cards/promo/snowy_village.py) |
| Stockpile | Menagerie | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/menagerie/stockpile.py`](../dominion/cards/menagerie/stockpile.py) |
| Supplies | Menagerie | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/menagerie/supplies.py`](../dominion/cards/menagerie/supplies.py) |
| Village Green | Menagerie | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/menagerie/village_green.py`](../dominion/cards/menagerie/village_green.py) |
| Wayfarer | Menagerie | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/menagerie/wayfarer.py`](../dominion/cards/menagerie/wayfarer.py) |
| Bard | Nocturne | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/nocturne/bard.py`](../dominion/cards/nocturne/bard.py) |
| Bat | Nocturne | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/nocturne/spirits/bat.py`](../dominion/cards/nocturne/spirits/bat.py) |
| Blessed Village | Nocturne | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/nocturne/blessed_village.py`](../dominion/cards/nocturne/blessed_village.py) |
| Cemetery | Nocturne | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/nocturne/cemetery.py`](../dominion/cards/nocturne/cemetery.py) |
| Changeling | Nocturne | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/nocturne/changeling.py`](../dominion/cards/nocturne/changeling.py) |
| Cobbler | Nocturne | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/nocturne/cobbler.py`](../dominion/cards/nocturne/cobbler.py) |
| Conclave | Nocturne | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/nocturne/conclave.py`](../dominion/cards/nocturne/conclave.py) |
| Crypt | Nocturne | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/nocturne/crypt.py`](../dominion/cards/nocturne/crypt.py) |
| Cursed Gold | Nocturne | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/nocturne/heirlooms/cursed_gold.py`](../dominion/cards/nocturne/heirlooms/cursed_gold.py) |
| Cursed Village | Nocturne | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/nocturne/cursed_village.py`](../dominion/cards/nocturne/cursed_village.py) |
| Den of Sin | Nocturne | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/nocturne/den_of_sin.py`](../dominion/cards/nocturne/den_of_sin.py) |
| Devil's Workshop | Nocturne | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/nocturne/devils_workshop.py`](../dominion/cards/nocturne/devils_workshop.py) |
| Druid | Nocturne | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/nocturne/druid.py`](../dominion/cards/nocturne/druid.py) |
| Exorcist | Nocturne | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/nocturne/exorcist.py`](../dominion/cards/nocturne/exorcist.py) |
| Faithful Hound | Nocturne | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/nocturne/faithful_hound.py`](../dominion/cards/nocturne/faithful_hound.py) |
| Fool | Nocturne | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/nocturne/fool.py`](../dominion/cards/nocturne/fool.py) |
| Ghost | Nocturne | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/nocturne/spirits/ghost.py`](../dominion/cards/nocturne/spirits/ghost.py) |
| Ghost Town | Nocturne | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/nocturne/ghost_town.py`](../dominion/cards/nocturne/ghost_town.py) |
| Goat | Nocturne | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/nocturne/heirlooms/goat.py`](../dominion/cards/nocturne/heirlooms/goat.py) |
| Guardian | Nocturne | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/nocturne/guardian.py`](../dominion/cards/nocturne/guardian.py) |
| Haunted Mirror | Nocturne | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/nocturne/heirlooms/haunted_mirror.py`](../dominion/cards/nocturne/heirlooms/haunted_mirror.py) |
| Idol | Nocturne | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/nocturne/idol.py`](../dominion/cards/nocturne/idol.py) |
| Imp | Nocturne | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/nocturne/spirits/imp.py`](../dominion/cards/nocturne/spirits/imp.py) |
| Leprechaun | Nocturne | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/nocturne/leprechaun.py`](../dominion/cards/nocturne/leprechaun.py) |
| Lucky Coin | Nocturne | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/nocturne/heirlooms/lucky_coin.py`](../dominion/cards/nocturne/heirlooms/lucky_coin.py) |
| Magic Lamp | Nocturne | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/nocturne/heirlooms/magic_lamp.py`](../dominion/cards/nocturne/heirlooms/magic_lamp.py) |
| Monastery | Nocturne | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/nocturne/monastery.py`](../dominion/cards/nocturne/monastery.py) |
| Necromancer | Nocturne | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/nocturne/necromancer.py`](../dominion/cards/nocturne/necromancer.py) |
| Night Watchman | Nocturne | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/nocturne/night_watchman.py`](../dominion/cards/nocturne/night_watchman.py) |
| Pasture | Nocturne | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/nocturne/heirlooms/pasture.py`](../dominion/cards/nocturne/heirlooms/pasture.py) |
| Pixie | Nocturne | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/nocturne/pixie.py`](../dominion/cards/nocturne/pixie.py) |
| Pooka | Nocturne | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/nocturne/pooka.py`](../dominion/cards/nocturne/pooka.py) |
| Pouch | Nocturne | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/nocturne/heirlooms/pouch.py`](../dominion/cards/nocturne/heirlooms/pouch.py) |
| Raider | Nocturne | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/nocturne/raider.py`](../dominion/cards/nocturne/raider.py) |
| Sacred Grove | Nocturne | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/nocturne/sacred_grove.py`](../dominion/cards/nocturne/sacred_grove.py) |
| Secret Cave | Nocturne | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/nocturne/secret_cave.py`](../dominion/cards/nocturne/secret_cave.py) |
| Shepherd | Nocturne | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/nocturne/shepherd.py`](../dominion/cards/nocturne/shepherd.py) |
| Skulk | Nocturne | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/nocturne/skulk.py`](../dominion/cards/nocturne/skulk.py) |
| Tormentor | Nocturne | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/nocturne/tormentor.py`](../dominion/cards/nocturne/tormentor.py) |
| Tracker | Nocturne | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/nocturne/tracker.py`](../dominion/cards/nocturne/tracker.py) |
| Tragic Hero | Nocturne | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/nocturne/tragic_hero.py`](../dominion/cards/nocturne/tragic_hero.py) |
| Vampire | Nocturne | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/nocturne/vampire.py`](../dominion/cards/nocturne/vampire.py) |
| Werewolf | Nocturne | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/nocturne/werewolf.py`](../dominion/cards/nocturne/werewolf.py) |
| Will-o'-Wisp | Nocturne | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/nocturne/spirits/will_o_wisp.py`](../dominion/cards/nocturne/spirits/will_o_wisp.py) |
| Wish | Nocturne | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/nocturne/spirits/wish.py`](../dominion/cards/nocturne/spirits/wish.py) |
| Zombie Apprentice | Nocturne | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/nocturne/spirits/zombie_apprentice.py`](../dominion/cards/nocturne/spirits/zombie_apprentice.py) |
| Zombie Mason | Nocturne | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/nocturne/spirits/zombie_mason.py`](../dominion/cards/nocturne/spirits/zombie_mason.py) |
| Zombie Spy | Nocturne | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/nocturne/spirits/zombie_spy.py`](../dominion/cards/nocturne/spirits/zombie_spy.py) |
| Abundance | Plunder | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/plunder/kingdom_cards.py`](../dominion/cards/plunder/kingdom_cards.py) |
| Amphora | Plunder | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/plunder/loot_cards.py`](../dominion/cards/plunder/loot_cards.py) |
| Buried Treasure | Plunder | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/plunder/kingdom_cards.py`](../dominion/cards/plunder/kingdom_cards.py) |
| Cabin Boy | Plunder | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/plunder/kingdom_cards.py`](../dominion/cards/plunder/kingdom_cards.py) |
| Cage | Plunder | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/plunder/kingdom_cards.py`](../dominion/cards/plunder/kingdom_cards.py) |
| Crew | Plunder | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/plunder/crew.py`](../dominion/cards/plunder/crew.py) |
| Crucible | Plunder | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/plunder/kingdom_cards.py`](../dominion/cards/plunder/kingdom_cards.py) |
| Cutthroat | Plunder | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/plunder/kingdom_cards.py`](../dominion/cards/plunder/kingdom_cards.py) |
| Doubloons | Plunder | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/plunder/loot_cards.py`](../dominion/cards/plunder/loot_cards.py) |
| Endless Chalice | Plunder | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/plunder/loot_cards.py`](../dominion/cards/plunder/loot_cards.py) |
| Enlarge | Plunder | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/plunder/kingdom_cards.py`](../dominion/cards/plunder/kingdom_cards.py) |
| Figurehead | Plunder | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/plunder/loot_cards.py`](../dominion/cards/plunder/loot_cards.py) |
| Figurine | Plunder | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/plunder/kingdom_cards.py`](../dominion/cards/plunder/kingdom_cards.py) |
| First Mate | Plunder | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/plunder/first_mate.py`](../dominion/cards/plunder/first_mate.py) |
| Flagship | Plunder | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/plunder/flagship.py`](../dominion/cards/plunder/flagship.py) |
| Fortune Hunter | Plunder | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/plunder/kingdom_cards.py`](../dominion/cards/plunder/kingdom_cards.py) |
| Frigate | Plunder | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/plunder/kingdom_cards.py`](../dominion/cards/plunder/kingdom_cards.py) |
| Gondola | Plunder | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/plunder/kingdom_cards.py`](../dominion/cards/plunder/kingdom_cards.py) |
| Grotto | Plunder | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/plunder/kingdom_cards.py`](../dominion/cards/plunder/kingdom_cards.py) |
| Hammer | Plunder | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/plunder/loot_cards.py`](../dominion/cards/plunder/loot_cards.py) |
| Harbor Village | Plunder | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/plunder/harbor_village.py`](../dominion/cards/plunder/harbor_village.py) |
| Insignia | Plunder | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/plunder/loot_cards.py`](../dominion/cards/plunder/loot_cards.py) |
| Jewelled Egg | Plunder | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/plunder/kingdom_cards.py`](../dominion/cards/plunder/kingdom_cards.py) |
| Jewels | Plunder | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/plunder/loot_cards.py`](../dominion/cards/plunder/loot_cards.py) |
| King's Cache | Plunder | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/plunder/kingdom_cards.py`](../dominion/cards/plunder/kingdom_cards.py) |
| Landing Party | Plunder | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/plunder/kingdom_cards.py`](../dominion/cards/plunder/kingdom_cards.py) |
| Longship | Plunder | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/plunder/kingdom_cards.py`](../dominion/cards/plunder/kingdom_cards.py) |
| Mapmaker | Plunder | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/plunder/kingdom_cards.py`](../dominion/cards/plunder/kingdom_cards.py) |
| Maroon | Plunder | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/plunder/kingdom_cards.py`](../dominion/cards/plunder/kingdom_cards.py) |
| Mining Road | Plunder | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/plunder/kingdom_cards.py`](../dominion/cards/plunder/kingdom_cards.py) |
| Orb | Plunder | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/plunder/loot_cards.py`](../dominion/cards/plunder/loot_cards.py) |
| Pendant | Plunder | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/plunder/kingdom_cards.py`](../dominion/cards/plunder/kingdom_cards.py) |
| Pickaxe | Plunder | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/plunder/pickaxe.py`](../dominion/cards/plunder/pickaxe.py) |
| Pilgrim | Plunder | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/allies/pilgrim.py`](../dominion/cards/allies/pilgrim.py) |
| Prize Goat | Plunder | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/plunder/loot_cards.py`](../dominion/cards/plunder/loot_cards.py) |
| Puzzle Box | Plunder | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/plunder/loot_cards.py`](../dominion/cards/plunder/loot_cards.py) |
| Rope | Plunder | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/plunder/kingdom_cards.py`](../dominion/cards/plunder/kingdom_cards.py) |
| Sack of Loot | Plunder | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/plunder/kingdom_cards.py`](../dominion/cards/plunder/kingdom_cards.py) |
| Search | Plunder | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/plunder/kingdom_cards.py`](../dominion/cards/plunder/kingdom_cards.py) |
| Secluded Shrine | Plunder | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/plunder/kingdom_cards.py`](../dominion/cards/plunder/kingdom_cards.py) |
| Sextant | Plunder | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/plunder/loot_cards.py`](../dominion/cards/plunder/loot_cards.py) |
| Shaman | Plunder | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/plunder/kingdom_cards.py`](../dominion/cards/plunder/kingdom_cards.py) |
| Shield | Plunder | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/plunder/loot_cards.py`](../dominion/cards/plunder/loot_cards.py) |
| Silver Mine | Plunder | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/plunder/kingdom_cards.py`](../dominion/cards/plunder/kingdom_cards.py) |
| Siren | Plunder | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/plunder/kingdom_cards.py`](../dominion/cards/plunder/kingdom_cards.py) |
| Spell Scroll | Plunder | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/plunder/loot_cards.py`](../dominion/cards/plunder/loot_cards.py) |
| Staff | Plunder | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/plunder/loot_cards.py`](../dominion/cards/plunder/loot_cards.py) |
| Stowaway | Plunder | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/plunder/kingdom_cards.py`](../dominion/cards/plunder/kingdom_cards.py) |
| Swamp Shacks | Plunder | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/plunder/kingdom_cards.py`](../dominion/cards/plunder/kingdom_cards.py) |
| Sword | Plunder | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/plunder/loot_cards.py`](../dominion/cards/plunder/loot_cards.py) |
| Taskmaster | Plunder | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/allies/taskmaster.py`](../dominion/cards/allies/taskmaster.py) |
| Tools | Plunder | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/plunder/kingdom_cards.py`](../dominion/cards/plunder/kingdom_cards.py) |
| Trickster | Plunder | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/plunder/trickster.py`](../dominion/cards/plunder/trickster.py) |
| Wealthy Village | Plunder | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/allies/wealthy_village.py`](../dominion/cards/allies/wealthy_village.py) |
| Avanto | Promo | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/promo/avanto.py`](../dominion/cards/promo/avanto.py) |
| Black Market | Promo | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/promo/black_market.py`](../dominion/cards/promo/black_market.py) |
| Church | Promo | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/promo/church.py`](../dominion/cards/promo/church.py) |
| Dismantle | Promo | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/promo/dismantle.py`](../dominion/cards/promo/dismantle.py) |
| Envoy | Promo | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/promo/envoy.py`](../dominion/cards/promo/envoy.py) |
| Governor | Promo | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/promo/governor.py`](../dominion/cards/promo/governor.py) |
| Marchland | Promo | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/promo/marchland.py`](../dominion/cards/promo/marchland.py) |
| Prince | Promo | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/promo/prince.py`](../dominion/cards/promo/prince.py) |
| Sauna | Promo | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/promo/sauna.py`](../dominion/cards/promo/sauna.py) |
| Stash | Promo | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/promo/stash.py`](../dominion/cards/promo/stash.py) |
| Walled Village | Promo | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/promo/walled_village.py`](../dominion/cards/promo/walled_village.py) |
| Bank | Prosperity | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/prosperity/bank.py`](../dominion/cards/prosperity/bank.py) |
| Bishop | Prosperity | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/prosperity/bishop.py`](../dominion/cards/prosperity/bishop.py) |
| Charlatan | Prosperity | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/prosperity/charlatan.py`](../dominion/cards/prosperity/charlatan.py) |
| City | Prosperity | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/prosperity/city.py`](../dominion/cards/prosperity/city.py) |
| Collection | Prosperity | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/allies/collection.py`](../dominion/cards/allies/collection.py) |
| Colony | Prosperity | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/prosperity/colony.py`](../dominion/cards/prosperity/colony.py) |
| Contraband | Prosperity | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/prosperity/contraband.py`](../dominion/cards/prosperity/contraband.py) |
| Counting House | Prosperity | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/prosperity/counting_house.py`](../dominion/cards/prosperity/counting_house.py) |
| Crystal Ball | Prosperity | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/prosperity/crystal_ball.py`](../dominion/cards/prosperity/crystal_ball.py) |
| Expand | Prosperity | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/prosperity/expand.py`](../dominion/cards/prosperity/expand.py) |
| Forge | Prosperity | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/prosperity/forge.py`](../dominion/cards/prosperity/forge.py) |
| Goons | Prosperity | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/prosperity/goons.py`](../dominion/cards/prosperity/goons.py) |
| Grand Market | Prosperity | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/prosperity/grand_market.py`](../dominion/cards/prosperity/grand_market.py) |
| Hoard | Prosperity | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/prosperity/hoard.py`](../dominion/cards/prosperity/hoard.py) |
| King's Court | Prosperity | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/prosperity/kings_court.py`](../dominion/cards/prosperity/kings_court.py) |
| Loan | Prosperity | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/prosperity/loan.py`](../dominion/cards/prosperity/loan.py) |
| Magnate | Prosperity | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/prosperity/magnate.py`](../dominion/cards/prosperity/magnate.py) |
| Mint | Prosperity | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/prosperity/mint.py`](../dominion/cards/prosperity/mint.py) |
| Monument | Prosperity | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/prosperity/monument.py`](../dominion/cards/prosperity/monument.py) |
| Mountebank | Prosperity | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/prosperity/mountebank.py`](../dominion/cards/prosperity/mountebank.py) |
| Peddler | Prosperity | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/prosperity/peddler.py`](../dominion/cards/prosperity/peddler.py) |
| Platinum | Prosperity | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/prosperity/platinum.py`](../dominion/cards/prosperity/platinum.py) |
| Quarry | Prosperity | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/prosperity/quarry.py`](../dominion/cards/prosperity/quarry.py) |
| Rabble | Prosperity | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/prosperity/rabble.py`](../dominion/cards/prosperity/rabble.py) |
| Royal Seal | Prosperity | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/prosperity/royal_seal.py`](../dominion/cards/prosperity/royal_seal.py) |
| Talisman | Prosperity | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/prosperity/talisman.py`](../dominion/cards/prosperity/talisman.py) |
| Tiara | Prosperity | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/prosperity/tiara.py`](../dominion/cards/prosperity/tiara.py) |
| Trade Route | Prosperity | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/prosperity/trade_route.py`](../dominion/cards/prosperity/trade_route.py) |
| Vault | Prosperity | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/prosperity/vault.py`](../dominion/cards/prosperity/vault.py) |
| Venture | Prosperity | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/prosperity/venture.py`](../dominion/cards/prosperity/venture.py) |
| War Chest | Prosperity | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/prosperity/war_chest.py`](../dominion/cards/prosperity/war_chest.py) |
| Workers' Village | Prosperity | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/prosperity/workers_village.py`](../dominion/cards/prosperity/workers_village.py) |
| Acting Troupe | Renaissance | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/renaissance/acting_troupe.py`](../dominion/cards/renaissance/acting_troupe.py) |
| Border Guard | Renaissance | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/renaissance/border_guard.py`](../dominion/cards/renaissance/border_guard.py) |
| Cargo Ship | Renaissance | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/renaissance/cargo_ship.py`](../dominion/cards/renaissance/cargo_ship.py) |
| Ducat | Renaissance | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/renaissance/ducat.py`](../dominion/cards/renaissance/ducat.py) |
| Experiment | Renaissance | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/renaissance/experiment.py`](../dominion/cards/renaissance/experiment.py) |
| Flag Bearer | Renaissance | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/renaissance/flag_bearer.py`](../dominion/cards/renaissance/flag_bearer.py) |
| Hideout | Renaissance | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/renaissance/hideout.py`](../dominion/cards/renaissance/hideout.py) |
| Improve | Renaissance | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/renaissance/improve.py`](../dominion/cards/renaissance/improve.py) |
| Inventor | Renaissance | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/renaissance/inventor.py`](../dominion/cards/renaissance/inventor.py) |
| Lackeys | Renaissance | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/renaissance/lackeys.py`](../dominion/cards/renaissance/lackeys.py) |
| Mountain Village | Renaissance | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/renaissance/mountain_village.py`](../dominion/cards/renaissance/mountain_village.py) |
| Old Witch | Renaissance | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/renaissance/old_witch.py`](../dominion/cards/renaissance/old_witch.py) |
| Patron | Renaissance | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/renaissance/patron.py`](../dominion/cards/renaissance/patron.py) |
| Priest | Renaissance | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/renaissance/priest.py`](../dominion/cards/renaissance/priest.py) |
| Recruiter | Renaissance | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/renaissance/recruiter.py`](../dominion/cards/renaissance/recruiter.py) |
| Research | Renaissance | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/renaissance/research.py`](../dominion/cards/renaissance/research.py) |
| Scepter | Renaissance | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/renaissance/scepter.py`](../dominion/cards/renaissance/scepter.py) |
| Scholar | Renaissance | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/renaissance/scholar.py`](../dominion/cards/renaissance/scholar.py) |
| Sculptor | Renaissance | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/renaissance/sculptor.py`](../dominion/cards/renaissance/sculptor.py) |
| Seer | Renaissance | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/renaissance/seer.py`](../dominion/cards/renaissance/seer.py) |
| Silk Merchant | Renaissance | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/renaissance/silk_merchant.py`](../dominion/cards/renaissance/silk_merchant.py) |
| Spices | Renaissance | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/renaissance/spices.py`](../dominion/cards/renaissance/spices.py) |
| Swashbuckler | Renaissance | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/renaissance/swashbuckler.py`](../dominion/cards/renaissance/swashbuckler.py) |
| Treasurer | Renaissance | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/renaissance/treasurer.py`](../dominion/cards/renaissance/treasurer.py) |
| Villain | Renaissance | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/renaissance/villain.py`](../dominion/cards/renaissance/villain.py) |
| Alley | Rising Sun | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/rising_sun/alley.py`](../dominion/cards/rising_sun/alley.py) |
| Aristocrat | Rising Sun | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/rising_sun/aristocrat.py`](../dominion/cards/rising_sun/aristocrat.py) |
| Artist | Rising Sun | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/rising_sun/artist.py`](../dominion/cards/rising_sun/artist.py) |
| Change | Rising Sun | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/rising_sun/change.py`](../dominion/cards/rising_sun/change.py) |
| Craftsman | Rising Sun | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/rising_sun/craftsman.py`](../dominion/cards/rising_sun/craftsman.py) |
| Daimyo | Rising Sun | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/rising_sun/daimyo.py`](../dominion/cards/rising_sun/daimyo.py) |
| Fishmonger | Rising Sun | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/rising_sun/fishmonger.py`](../dominion/cards/rising_sun/fishmonger.py) |
| Gold Mine | Rising Sun | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/rising_sun/gold_mine.py`](../dominion/cards/rising_sun/gold_mine.py) |
| Imperial Envoy | Rising Sun | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/rising_sun/imperial_envoy.py`](../dominion/cards/rising_sun/imperial_envoy.py) |
| Kitsune | Rising Sun | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/rising_sun/kitsune.py`](../dominion/cards/rising_sun/kitsune.py) |
| Litter | Rising Sun | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/rising_sun/litter.py`](../dominion/cards/rising_sun/litter.py) |
| Mountain Shrine | Rising Sun | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/rising_sun/mountain_shrine.py`](../dominion/cards/rising_sun/mountain_shrine.py) |
| Ninja | Rising Sun | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/rising_sun/ninja.py`](../dominion/cards/rising_sun/ninja.py) |
| Poet | Rising Sun | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/rising_sun/poet.py`](../dominion/cards/rising_sun/poet.py) |
| Rice | Rising Sun | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/rising_sun/rice.py`](../dominion/cards/rising_sun/rice.py) |
| Rice Broker | Rising Sun | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/rising_sun/rice_broker.py`](../dominion/cards/rising_sun/rice_broker.py) |
| River Shrine | Rising Sun | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/rising_sun/river_shrine.py`](../dominion/cards/rising_sun/river_shrine.py) |
| Riverboat | Rising Sun | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/rising_sun/riverboat.py`](../dominion/cards/rising_sun/riverboat.py) |
| Ronin | Rising Sun | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/rising_sun/ronin.py`](../dominion/cards/rising_sun/ronin.py) |
| Root Cellar | Rising Sun | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/rising_sun/root_cellar.py`](../dominion/cards/rising_sun/root_cellar.py) |
| Rustic Village | Rising Sun | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/rising_sun/rustic_village.py`](../dominion/cards/rising_sun/rustic_village.py) |
| Samurai | Rising Sun | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/rising_sun/samurai.py`](../dominion/cards/rising_sun/samurai.py) |
| Snake Witch | Rising Sun | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/rising_sun/snake_witch.py`](../dominion/cards/rising_sun/snake_witch.py) |
| Tanuki | Rising Sun | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/rising_sun/tanuki.py`](../dominion/cards/rising_sun/tanuki.py) |
| Tea House | Rising Sun | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/rising_sun/tea_house.py`](../dominion/cards/rising_sun/tea_house.py) |
| Ambassador | Seaside | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/seaside/ambassador.py`](../dominion/cards/seaside/ambassador.py) |
| Astrolabe | Seaside | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/plunder/astrolabe.py`](../dominion/cards/plunder/astrolabe.py) |
| Bazaar | Seaside | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/seaside/bazaar.py`](../dominion/cards/seaside/bazaar.py) |
| Blockade | Seaside | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/seaside/blockade.py`](../dominion/cards/seaside/blockade.py) |
| Caravan | Seaside | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/seaside/caravan.py`](../dominion/cards/seaside/caravan.py) |
| Corsair | Seaside | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/seaside/corsair.py`](../dominion/cards/seaside/corsair.py) |
| Cutpurse | Seaside | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/seaside/cutpurse.py`](../dominion/cards/seaside/cutpurse.py) |
| Embargo | Seaside | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/seaside/embargo.py`](../dominion/cards/seaside/embargo.py) |
| Explorer | Seaside | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/seaside/explorer.py`](../dominion/cards/seaside/explorer.py) |
| Fishing Village | Seaside | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/seaside/fishing_village.py`](../dominion/cards/seaside/fishing_village.py) |
| Ghost Ship | Seaside | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/seaside/ghost_ship.py`](../dominion/cards/seaside/ghost_ship.py) |
| Island | Seaside | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/seaside/island.py`](../dominion/cards/seaside/island.py) |
| Lighthouse | Seaside | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/seaside/lighthouse.py`](../dominion/cards/seaside/lighthouse.py) |
| Lookout | Seaside | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/seaside/lookout.py`](../dominion/cards/seaside/lookout.py) |
| Merchant Ship | Seaside | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/seaside/merchant_ship.py`](../dominion/cards/seaside/merchant_ship.py) |
| Monkey | Seaside | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/seaside/monkey.py`](../dominion/cards/seaside/monkey.py) |
| Native Village | Seaside | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/seaside/native_village.py`](../dominion/cards/seaside/native_village.py) |
| Navigator | Seaside | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/seaside/navigator.py`](../dominion/cards/seaside/navigator.py) |
| Outpost | Seaside | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/seaside/outpost.py`](../dominion/cards/seaside/outpost.py) |
| Pearl Diver | Seaside | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/seaside/pearl_diver.py`](../dominion/cards/seaside/pearl_diver.py) |
| Pirate | Seaside | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/seaside/pirate.py`](../dominion/cards/seaside/pirate.py) |
| Pirate Ship | Seaside | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/seaside/pirate_ship.py`](../dominion/cards/seaside/pirate_ship.py) |
| Sailor | Seaside | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/seaside/sailor.py`](../dominion/cards/seaside/sailor.py) |
| Salvager | Seaside | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/seaside/salvager.py`](../dominion/cards/seaside/salvager.py) |
| Sea Chart | Seaside | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/seaside/sea_chart.py`](../dominion/cards/seaside/sea_chart.py) |
| Sea Hag | Seaside | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/seaside/sea_hag.py`](../dominion/cards/seaside/sea_hag.py) |
| Sea Witch | Seaside | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/seaside/sea_witch.py`](../dominion/cards/seaside/sea_witch.py) |
| Smugglers | Seaside | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/seaside/smugglers.py`](../dominion/cards/seaside/smugglers.py) |
| Tactician | Seaside | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/seaside/tactician.py`](../dominion/cards/seaside/tactician.py) |
| Tide Pools | Seaside | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/seaside/tide_pools.py`](../dominion/cards/seaside/tide_pools.py) |
| Treasure Map | Seaside | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/seaside/treasure_map.py`](../dominion/cards/seaside/treasure_map.py) |
| Treasury | Seaside | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/seaside/treasury.py`](../dominion/cards/seaside/treasury.py) |
| Warehouse | Seaside | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/seaside/warehouse.py`](../dominion/cards/seaside/warehouse.py) |
| Wharf | Seaside | Unreviewed | Unreviewed | Unreviewed | Unreviewed | [`dominion/cards/seaside/wharf.py`](../dominion/cards/seaside/wharf.py) |

## Optimizer coverage is separate

Bounty Hunter's `bounty_hunter_exile_priority` already round-trips through `dominion/simulation/structured_genome.py`, mutates in the genetic trainer, and has tests in `tests/test_structured_genome.py`. This exposes priority rules, not the complete contextual bonus policy in the benchmark. Free-gain preferences also round-trip, but arbitrary Python Watchtower, Clerk, Investment, supply-target, timing and storage overrides are not automatically searchable genes. A callable hook and a parameterized policy are separate claims.

Baseline-change rule: freeze the candidate and purchases before fresh seat-balanced validation, record decision firings and raw seed outcomes, and reevaluate every affected registered strategy on its own board before changing production defaults. This measurement changes no defaults; existing supply, free-gain and storage studies contain their own strategy reevaluations. Historical standings remain historical evidence.
