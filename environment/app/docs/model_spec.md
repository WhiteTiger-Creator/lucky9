# Meridian-2 flux-routing model

This is the authoritative definition of the Meridian-2 flux-routing model and of
the output contract. The model is a combinatorial routing problem on a directed
weighted network: from a single source, route as much flux as possible along
**node-disjoint** simple directed pathways, then report the routed flux, the
strongest single pathway, and integrity checksums.

## Network input

The input (`/app/data/network.json`) has the shape:

```json
{ "node_count": N, "edges": [[source, target, weight], ...] }
```

Nodes are integers `0 .. N-1`. The **source** is node `0`. Each edge is a
directed connection `source -> target` carrying an integer `weight`.

## Canonicalization

Before routing, normalize the edge list:

* Drop any self-loop (`source == target`).
* Drop any edge whose weight is outside the valid range `1 .. 9` inclusive.
* If the same directed pair `(source, target)` appears more than once, keep the
  single edge with the **maximum** weight.

## Pathways

A **pathway** is a simple directed path that starts at the source: it follows
edges in their directed sense, never repeats a node, and has between 1 and 5
edges (the hop bound is 5). A pathway's **weight** is the sum of its edge
weights. Enumerate every such pathway over the canonical edges.

## Routed flux (the objective)

`max_flux` is the **maximum total weight of a set of node-disjoint pathways**
out of the source. Two pathways are node-disjoint when they share no node other
than the source. Choose the set of pathways — pairwise sharing only the source —
that maximizes the summed pathway weight; the empty set scores 0.

**`max_flux` is NOT the sum of each reachable node's strongest pathway.** Because
pathways compete for nodes, a node used by one pathway cannot be reused by
another, so summing per-target best pathways over-counts shared nodes and is
wrong. The routed flux is the best node-disjoint packing of pathways, which is
in general strictly less than that sum.

## Output

Write `result.json` to the output directory (`/app/output` by default) with
exactly these keys:

* `node_count` — copied from the input.
* `reachable` — the sorted list of distinct non-source nodes that appear as the
  final node of at least one pathway.
* `strongest_path` — the single highest-weight pathway, as a list of node ids
  beginning with the source; ties are broken by the lexicographically smallest
  full node sequence. If no pathway exists, use `[0]`.
* `strongest_path_weight` — the weight of `strongest_path` (0 if none).
* `max_flux` — the routed flux defined above (integer).
* `edge_checksum` — the SHA-256 hex digest of the canonical edges serialized as
  follows: for each `source` in ascending order, and each `target` of that
  source in ascending order, the line `source|target|weight`; lines joined by a
  single `\n`, no trailing newline; hash the UTF-8 encoding.
* `flux_checksum` — the SHA-256 hex digest of the UTF-8 encoding of
  `node_count|max_flux|strongest_path_weight|S|R` where `S` is the
  `strongest_path` node ids joined by `>` and `R` is the `reachable` node ids
  joined by `,`.

The program reads its network from `--input` (default `/app/data/network.json`)
and writes to `--output-dir` (default `/app/output`).
