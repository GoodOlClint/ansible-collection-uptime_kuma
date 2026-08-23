# ADR 0001 — In-repo python-socketio client replaces the uptime-kuma-api wrapper; Uptime Kuma 2.x only

- **Status:** Approved
- **Date:** 2026-08-23
- **Deciders:** operator + agent
- **Context source:** docs/homelab-gap-report.md · CONTRIBUTING.md ADR-001 · live probe of the homelab instance (2026-08-23)

## Context

CONTRIBUTING.md ADR-001 chose Option B: depend on the `uptime-kuma-api` pip wrapper rather than write a Socket.IO client. That wrapper (lucasheld, last release 1.2.1, September 2023) documents support for Uptime Kuma 1.21.3–1.23.2 only and has had no commits in three years. The only consumer of this collection runs `louislam/uptime-kuma:2`. A live probe showed the wrapper connects and logs in against 2.x only with a 30s timeout, and its monitor/settings builders gate fields on `info.version`, which 2.x withholds before login.

The v2 fork (`exaland/uptime-kuma-api-v2`) targets 2.0.0-beta.2, has two substantive commits in 14 months, and is single-maintainer. It moves the pin; it does not remove the risk.

The collection uses 44 wrapper methods. Underneath they are ~60 named Socket.IO events with `{ok, msg, ...}` replies. The wrapper's transport layer is `python-socketio`; its value-add is per-type payload defaults and camelCase conversion, which is exactly the part that drifts per Kuma version and must be re-verified anyway.

## Decision

`plugins/module_utils/uptime_kuma_api.py` owns the Uptime Kuma protocol directly on top of `python-socketio[client]`: connect, `login` / `loginByToken` / `setup`, and a `_call(event, *args)` helper. Every module talks to Kuma only through this client.

The pip dependency exception stands in spirit but changes target: the collection requires `python-socketio[client]` (maintained; author of Flask-SocketIO), not `uptime-kuma-api`. No RFC 6455 / Engine.IO code lives in this repo.

The client targets **Uptime Kuma 2.x only**. No version gating, no 1.x payload shapes. Supported version is stated in `README.md` and enforced by CI against `louislam/uptime-kuma:2`.

Payload shapes and event names are pinned by integration tests that run in CI against a real 2.x container. A module that has no v2 integration test is not considered ported.

## Rejected alternatives

- **Keep `uptime-kuma-api` and shim around it.** Dead upstream; the shims would accumulate on every Kuma release and we would still need the v2 CI container to know when it broke.
- **Switch to `uptime-kuma-api-v2`.** Same bus factor, less track record, pinned to a beta. Trading one stale wrapper for another.
- **Option A from ADR-001 (stdlib Socket.IO).** Still disproportionate: Engine.IO handshake, WebSocket framing, ping/pong and reconnection for no user-visible gain over a maintained protocol library.
- **Support 1.23.x and 2.x.** No known consumer on 1.x; doubles the CI matrix and reintroduces the version gating that is the wrapper's weakest part.

## Consequences

- CONTRIBUTING.md ADR-001 is superseded by this record; README Requirements change from `uptime-kuma-api` to `python-socketio[client]`.
- CI gains a `louislam/uptime-kuma:2` service container and the integration targets run on every push. A local `docker compose` dev instance (`tests/dev/`) mirrors it.
- The collection gains a `uptime_kuma_setup` module (first-run admin creation) because the new client exposes the `setup` event and rebuild-as-routine in the homelab needs unattended bootstrap.
- Kuma 2.x protocol changes are now this repo's problem to track, with the CI container as the tripwire.
- Version pin policy: `galaxy.yml` major bumps track Kuma major bumps.
