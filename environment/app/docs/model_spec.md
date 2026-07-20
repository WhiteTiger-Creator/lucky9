# Meridian-2 network transport — output contract

This document is the **output contract only**: it fixes the network input shape,
the exact `result.json` key set, and the byte-level checksum serialization. It
does **not** define how the values are derived. Link conditioning and validity
bounds, the channel span bound, the sustained-flux objective, the tie-broken
routed channel set, the residual packing, the per-hop efficiency aggregates, the
site-conditioning and damping rules, and the dispatch admission, class and
ordering layers are settled in `/app/incident/flux_calibration_log.md`; reconcile the governing
(latest) calibration decision for each rule there.

## Network state

The network (`/app/data/network.json`) has the shape:

```json
{ "node_count": N, "edges": [[source, target, weight], ...] }
```

Sites (nodes) are integers `0 .. N-1`. The **source** is site `0`. Each edge is a
directed link `source -> target` carrying an integer conductance `weight`. How
the link list is conditioned (self-loops, weight bounds, duplicate handling), the
channel span bound, and every derived observable are governed by the calibration
log, not by this contract.

## Site conditioning state

Site conditioning is read from `/app/data/site_conditioning.json`, an object of the
shape:

```json
{ "sites": [ {"site": S, "damping": D}, ... ] }
```

This path is **fixed and absolute**. `--input` selects the network only; it never
relocates the conditioning file. How entries are validated, how repeated sites are
collapsed, and how damping enters the observables are governed by the calibration
log, not by this contract.


## Output

Write `result.json` to the output directory (`/app/output` by default) with
exactly these keys. What each derived value **means** is fixed by the calibration
log; this contract fixes only the key set and the serializations below.

* `node_count` — copied from the input.
* `reachable` — the sorted list of distinct non-source sites that terminate at
  least one channel (channel definition per the log).
* `strongest_path` — the single highest-flux channel as a list of site ids from
  the source; ties broken by the lexicographically smallest full site sequence;
  `[0]` if no channel exists.
* `strongest_path_weight` — the flux of `strongest_path` (0 if none).
* `max_flux` — the sustained-flux observable (see the calibration log).
* `flux_paths` — the tie-broken routed set's channels (each a site-id list from
  the source), sorted ascending (selection and tie-break per the log).
* `flux_path_count` — the number of channels in `flux_paths`.
* `flux_node_count` — the number of distinct non-source sites used by the routed set.
* `residual_flux` — the residual packing total (see the log).
* `total_path_efficiency` — sum of per-hop efficiency over the routed channels (per log).
* `max_path_efficiency` — the largest per-hop efficiency over the routed channels (per log).
* `mean_flux_floor` — the floored mean of the sustained flux over the routed count (per log).
* `saturated_endpoints` — the terminal site ids (ascending) of the routed channels
  admitted to the saturated set by the sequential throughput ledger (per the log).
* `saturated_channel_count` — the number of ids in `saturated_endpoints`.
* `max_throughput` — the maximum per-channel throughput over the routed channels.
* `throughput_ledger_checksum` — the SHA-256 hex digest of the ledger rows serialized
  as follows: for each routed channel in `flux_paths` order, the line
  `endpoint|throughput|c|carry_out` where `endpoint` is the channel's terminal site,
  and `c` is `1` if the channel is saturated else `0`; lines joined by a single `\n`,
  no trailing newline; hash the UTF-8 encoding (throughput/flag/carry_out per the log).
* `total_damping` — the summed site damping accumulated over **all** routed channels
  (per the log; dispatched or not).
* `dispatched_endpoints` — a JSON **array** of the terminal site ids (ascending) of the
  routed channels admitted by the dispatch floor (per the log).
* `dispatched_channel_count` — the number of ids in `dispatched_endpoints`.
* `total_conditioned_flux` — sum of conditioned flux over the dispatched channels (per log).
* `max_conditioned_flux` — the largest conditioned flux over the dispatched channels,
  `0` when none are dispatched (per log).
* `class_counts` — a JSON **object** whose keys are exactly the three class names
  `primary`, `secondary`, `tertiary`, in that order, mapping to the number of dispatched
  channels in each class. All three keys are always present, emitting `0` for a class
  with no dispatched channels. These three lowercase strings are the only accepted class
  labels; which class a channel earns is governed by the calibration log.
* `dispatch_order` — a JSON **array** of the dispatched channels' terminal site ids in the
  log's dispatch ordering (this is an ordering, **not** sorted ascending; contrast
  `dispatched_endpoints`, which is sorted).
The dispatch fields describe the dispatch list AFTER the capacity cap defined in the
calibration log, not before it.

* `dispatch_checksum` — the SHA-256 hex digest of the dispatch rows serialized as
  follows: for each dispatched channel in `dispatch_order` order, the line
  `endpoint|class|conditioned_flux|damped_flux|damping_sum`; lines joined by a single
  `\n`, no trailing newline; hash the UTF-8 encoding (each value per the log).
* `edge_checksum` — the SHA-256 hex digest of the conditioned links serialized as
  follows: for each `source` in ascending order, and each `target` of that source
  in ascending order, the line `source|target|weight`; lines joined by a single
  `\n`, no trailing newline; hash the UTF-8 encoding.
* `flux_checksum` — the SHA-256 hex digest of the UTF-8 encoding of
  `node_count|max_flux|strongest_path_weight|S|R|flux_node_count|residual_flux|total_path_efficiency|max_path_efficiency|mean_flux_floor|saturated_channel_count|max_throughput|SE|total_damping|total_conditioned_flux|max_conditioned_flux|dispatched_channel_count|DO|P`
  where `SE` is `saturated_endpoints` comma-joined ascending, `DO` is `dispatch_order` comma-joined in dispatch order, `S` is the `strongest_path` site ids joined by `>`, `R` is the
  `reachable` site ids joined by `,`, and `P` joins the `flux_paths` channels
  with `;`, each channel's site ids joined by `>`.

The program reads its network from `--input` (default `/app/data/network.json`)
and writes to `--output-dir` (default `/app/output`).
