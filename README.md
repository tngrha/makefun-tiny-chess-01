# Tiny Chess

A compact alpha-beta chess engine in Python (standard library only), the entry
for make.fun's `tiny-chess-01` ($500).

`main.py` is a packed entrypoint (see `source.py` for the readable source and
`makefun compress` for how it was packed): a 0x88 board, incremental evaluation
(material + piece-square tables + bishop pair + endgame king centralisation), a
transposition table, killer moves, MVV-LVA ordering, quiescence over captures,
promotions and check evasions, and a fixed budget of 150,000 nodes per move, so
live and replay agree move for move.

Local checks: perft(4) from the start position is 197,281 and perft(3) on the
Kiwipete position is 97,862, both exact.
