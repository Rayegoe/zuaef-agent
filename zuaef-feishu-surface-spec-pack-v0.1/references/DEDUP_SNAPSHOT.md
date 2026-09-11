# Reference Snapshot — Two-layer Dedup

The current Channel SDK documents two dedup layers.

## Pipeline layer

Runs before full normalization and catches:
- webhook retries;
- WebSocket reconnect backfill.

Supports a custom `DedupStore` protocol with `seen()` and `mark()`.

## Safety layer

Runs before user handler dispatch and has its own seen cache.

## Multi-process warning

The SDK's shared cache interface does not provide an atomic SETNX-style contract for
strict cross-process coherence.

Therefore the upstream documentation recommends safe patterns such as:
- route events for one app to a single worker;
- make handlers idempotent by event/message IDs.

This Spec adopts exactly that rule for OPi5 v0.1.
