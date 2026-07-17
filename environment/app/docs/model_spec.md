# Meridian-2 network transport model

This is the authoritative definition of the Meridian-2 network transport model
and of the output contract. Meridian-2 is a directed flow network from the
statistical physics of transport: flux enters at a single source and is carried
downstream along **vertex-disjoint transport channels**. The physical observable
of interest is the maximum flux the network can sustain simultaneously across
such channels, together with the strongest single channel and integrity
checksums over the network state.

## Network state

The network (`/app/data/network.json`) has the shape:

```json
{ "node_count": N, "edges": [[source, target, weight], ...] }
```

Sites (nodes) are integers `0 .. N-1`. The **source** is site `0`. Each edge is a
directed link `source -> target` carrying an integer conductance `weight`.

## Conditioning the network

Before the flux is evaluated, condition the edge list:

* Drop any self-link (`source == target`).
* Drop any link whose weight is outside the physical range `1 .. 9` inclusive.
* If the same directed pair `(source, target)` occurs more than once, retain the
  single link of **maximum** weight.

## Transport channels

A **transport channel** is a simple directed path that begins at the source: it
follows links in their directed sense, never revisits a site, and spans between
1 and 5 links (the span bound is 5). A channel's **flux** is the sum of the
conductances along it. Enumerate every such channel over the conditioned links.

## Sustained flux (the observable)

`max_flux` is the **maximum total flux carried by a set of vertex-disjoint
transport channels** out of the source. Two channels are vertex-disjoint when
they share no site other than the source. Among all sets of channels that
pairwise share only the source, the sustained flux is the largest attainable sum
of channel fluxes; the empty set carries 0.

**`max_flux` is NOT the sum of each downstream site's strongest channel.** Because
channels contend for sites, a site occupied by one channel is unavailable to
another, so summing the strongest channel per site over-counts shared sites and
overstates the sustained flux. **It is also NOT obtained greedily** — repeatedly
committing the highest-flux still-available channel does not in general realise
the maximum. The sustained flux is the exact maximum over vertex-disjoint channel
sets.

## Output

Write `result.json` to the output directory (`/app/output` by default) with
exactly these keys:

* `node_count` — copied from the input.
* `reachable` — the sorted list of distinct non-source sites that terminate at
  least one channel.
* `strongest_path` — the single highest-flux channel, as a list of site ids
  beginning with the source; ties are broken by the lexicographically smallest
  full site sequence. If no channel exists, use `[0]`.
* `strongest_path_weight` — the flux of `strongest_path` (0 if none).
* `max_flux` — the sustained flux defined above (integer).
* `edge_checksum` — the SHA-256 hex digest of the conditioned links serialized as
  follows: for each `source` in ascending order, and each `target` of that source
  in ascending order, the line `source|target|weight`; lines joined by a single
  `\n`, no trailing newline; hash the UTF-8 encoding.
* `flux_checksum` — the SHA-256 hex digest of the UTF-8 encoding of
  `node_count|max_flux|strongest_path_weight|S|R` where `S` is the
  `strongest_path` site ids joined by `>` and `R` is the `reachable` site ids
  joined by `,`.

The program reads its network from `--input` (default `/app/data/network.json`)
and writes to `--output-dir` (default `/app/output`).
