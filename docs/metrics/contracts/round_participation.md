# Round Participation Contract

Accepted rounds are completed regulation or overtime rounds between valid start/end boundaries. Exclude warmup, incomplete, post-round and post-match events. A player is not absent merely because no kill, hurt, assist, blind, or death event exists; participation requires roster/connect/alive evidence. Disconnect/reconnect must split or qualify participation, never silently alter the denominator.

The shared `AcceptedMatchPhase` implementation owns completed-round discovery, the inclusive final round-end tick, and warmup/post-match exclusion. Match 124 has 20 accepted rounds; the event at tick 115232 is later than the final round-end tick 114168 and is excluded. The 17 activity rows are never a participation denominator.

Version `3.0.0` reparses retained roster, spawn, connect/disconnect and team
state. Quiet rounds are accepted when roster membership persists and no
in-round disconnect contradicts it. Match 124 has 20 participated rounds and a
complete K/A/S/T ledger. If this evidence is incomplete on another demo, the
affected match is blocked rather than partially trusted.
