# Inheritance play dependencies

Inheritance owns one physical target in `PlayerState.inherited_action`. Its
printed name, types and constructor state remain intact; Estate has its own play
and then invokes the target's real methods. Neither the target nor an instruction
record is placed in Estate's physical zones.

Each play creates an `InheritedPlay` dependency record. Estate points to its own
records through `duration_targets`. The record captures nested Durations and
multiplier dependencies with the target's temporary dependency list isolated
from earlier plays. It is never an owned card.

Pending queues still contain the actual physical target. Parallel lists in
`inherited_duration_plays`, keyed by queue name and target object, associate each
callback with the Estate play that created it. The Duration scheduler consumes
those origins with the queue snapshot. Delayed callbacks can then attach new
Durations to the originating Estate, rather than all Estates sharing the target.
Recurring instructions carry their origin into their next queue occurrence.

Some legacy Duration implementations deduplicate a physical card's callbacks.
A permanently set-aside target instead keeps an occurrence per play so separate
Estates retain their own obligations. Royal Galley likewise resolves its stored
cards per originating play. Shared abilities cancelled on a gain remove their
callbacks; ownership lists are reconciled with the queues before retention.

Cargo Ship keeps one optional gain allowance per play. Its dependency records
route each allowance to the correct Estate and preserve the physical Cargo Ship
as the public gain-effect source. Each record captures its actual turn marker,
so an expired allowance cannot reactivate when that shared card is played later.
Markers contain player references, which survive copying a game, rather than
memory-address integers.

Regression coverage is in `tests/test_inheritance_reserve_duration.py`: distinct
and repeated Estates, immediate and delayed multipliers, unused versus consumed
Cargo Ship allowances, cancellation, storage conservation, copied games, and
independent Archive and Church batches. The published rules and compatibility
panel are linked from
[the HTML guide](../reports/strategies/capitalism-and-inheritance-rules-and-policy-compatibility.html).
This mechanism does not certify every target card's independent printed rules.

Flagship and Daimyo replay claims use the live Command predicate and reserve the
charges before instructions can play nested cards. Estate passes the claims to
its non-Command target. Replays use shared Action/Treasure handling, and the
physical replay source keeps the resulting Duration dependency. Daimyo records
the actual turn owner and turn counters so off-turn charges work on that turn
and expire before a later opponent's turn. Inherited Garrison has no gain-token
listener because publisher rules prohibit tokens on Garrison outside play.
