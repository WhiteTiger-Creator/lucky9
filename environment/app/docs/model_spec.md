# Meridian-2 SE-draining chip-firing model

This is the authoritative definition of the Meridian-2 stabilization model. It
is a **directed, order-sensitive** variant of chip-firing. It is **not** the
textbook four-neighbour abelian sandpile, and — unlike the classical model — its
result depends on the order in which cells are fired, so the firing schedule
below is part of the contract.

## Grid and drops

The input (`/app/data/drops.json`) has the shape:

```json
{ "rows": R, "cols": C, "drops": [[row, col, count], ...] }
```

Start from an `R x C` grid of zeros (row indices `0..R-1` top to bottom, column
indices `0..C-1` left to right). Apply every drop in order, adding `count` chips
to cell `(row, col)`. Drops may target the same cell more than once.

## Firing schedule (mandated order)

A cell is **unstable** when it holds 4 or more chips. Stabilization proceeds one
firing at a time, in a fixed order:

1. Among all currently unstable cells, select the one with the smallest
   `(row, col)` in lexicographic order (smallest row first, then smallest
   column).
2. **Fire that cell exactly once** (see the firing rule below).
3. Repeat until no unstable cells remain.

The model is **not** order-independent: firing greedily (emptying a cell in one
step), or firing cells in any other order, produces a different final grid.
Fire exactly one cell, exactly once, per step, always choosing the smallest
index.

## Firing rule (one firing)

Let `c` be the number of chips on the cell **at the moment it is fired**, and
let the **surge** be `s = c // 8` (integer division). One firing:

* removes `4 + s` chips from the cell,
* sends **2 chips east** (to the cell one column to the right), and
* sends **2 + s chips south** (to the cell one row below).

The surge rides entirely south; east always receives exactly 2. Because `s`
depends on the cell's count at firing time, and that count depends on chips
delivered by earlier firings, the schedule above is what makes the result
well-defined.

Chips directed off the grid — east from the last column, or south from the last
row — leave the grid and are added to the **spill** total. Chips are never sent
north or west, so every firing drains toward the south-east and stabilization
always terminates.

## Output

Write `result.json` to the output directory (default `/app/output`) with
exactly these keys:

* `rows`, `cols` — copied from the input.
* `grid` — the stabilized grid as a list of `R` rows, each a list of `C`
  integers, every value in `0..3`.
* `total_firings` — the total number of single firings performed.
* `row_firings` — a list of `R` integers, the number of firings in each row.
* `spill` — the total chips that left the grid.
* `grid_checksum` — the SHA-256 hex digest of the stabilized grid serialized as
  follows: each row is its cell values rendered in decimal and joined by single
  spaces; rows are joined by a single newline (`\n`); there is no trailing
  newline. Hash the UTF-8 encoding of that string.

The command-line interface is `--input PATH` (default `/app/data/drops.json`)
and `--output-dir PATH` (default `/app/output`).
