# Contributing to goodolclint.uptime_kuma

## Development Prerequisites

- Python >= 3.9
- ansible-core >= 2.14
- antsibull-changelog
- Docker (for integration tests)

## Architecture Decisions

### ADR-001: Socket.IO Client Strategy (Option B — uptime-kuma-api dependency)

**Status:** Accepted
**Date:** 2026-03-13
**Context:** Uptime Kuma does not expose a REST API. The only programmatic interface
is a Socket.IO 4.x (WebSocket) event-based protocol. Three options were evaluated:

| Option | Description | Verdict |
|--------|-------------|---------|
| A — stdlib Socket.IO | Implement a minimal Socket.IO 4.x client using only `http.client` and `socket` from the Python stdlib | Rejected |
| B — uptime-kuma-api dependency | Declare `uptime-kuma-api` as a documented pip dependency exception | **Accepted** |
| C — defer collection | Do not write module code until Uptime Kuma ships a REST API | Rejected |

**Decision:** Option B — declare `uptime-kuma-api` as an explicit, documented pip
dependency exception to the stdlib-only rule.

**Rationale:**

1. **No REST API exists.** Uptime Kuma's only programmatic interface is Socket.IO
   over WebSocket. There is no HTTP endpoint to call with `urllib` or `http.client`.
   The REST API is tracked at https://github.com/louislam/uptime-kuma/issues/1109
   but has not been implemented.

2. **Option A is disproportionately complex.** A stdlib Socket.IO client requires
   implementing: HTTP-to-WebSocket upgrade handshake, RFC 6455 WebSocket frame
   encoding/decoding (binary framing, masking, fragmentation), Engine.IO packet
   protocol (open/close/ping/pong/message), Socket.IO event protocol
   (connect/disconnect/event/ack), and reconnection logic. This would be hundreds
   of lines of complex, error-prone networking code that duplicates well-tested
   existing libraries.

3. **Option C provides no user value.** The REST API tracking issue has been open
   since 2022 with no implementation timeline. Deferring indefinitely means the
   collection never ships.

4. **uptime-kuma-api is the de facto standard.** It is listed on the official
   Uptime Kuma wiki under third-party addons. While it is a community project
   (authored by lucasheld, not the Uptime Kuma core team), it is the most widely
   used Python wrapper for Uptime Kuma.

**Third-party dependency acknowledgment:** `uptime-kuma-api` is a third-party
community wrapper, not an official SDK. This is an intentional, documented exception
to the stdlib-only constraint. The exception is justified because no first-party SDK
exists and no REST API is available.

**Transitive dependencies:** `uptime-kuma-api` depends on `python-socketio[client]`
and `packaging`. These are pulled in transitively.

**Risks and mitigations:**

- **Maintenance lag:** The latest release (1.2.1) was September 2023. Mitigation:
  pin to a known-good version range and document supported Uptime Kuma versions.
- **Breaking changes:** Uptime Kuma's Socket.IO API is not guaranteed stable.
  Mitigation: integration tests against a specific Uptime Kuma version in CI.
- **Supply chain:** Single-maintainer project. Mitigation: vendor or fork if the
  project becomes abandoned.

### ADR-002: Write-Only Field Handling

**Status:** Accepted
**Date:** 2026-03-13
**Context:** Some API fields (e.g., passwords, notification webhook URLs in certain
providers) are write-only — they can be set but are not returned by the API in
subsequent reads.

**Decision:** Write-only fields are excluded from idempotency comparisons. A module
will not report `changed=True` solely because a write-only field cannot be read back
for comparison. Each module documents which fields are write-only in its
DOCUMENTATION block.

**Rationale:** Comparing a user-supplied value against a field that always returns
`null` or a masked value would cause false-positive `changed=True` on every run,
breaking idempotency.

## Running Tests

### Unit tests

```bash
python -m pytest tests/unit/
```

### Integration tests

```bash
ansible-test integration --docker
```

## Adding a New Module

1. Add module file to `plugins/modules/uptime_kuma_<resource>.py`
2. Implement DOCUMENTATION, EXAMPLES, RETURN blocks (no stubs)
3. Implement idempotency logic using the base API client
4. Add unit tests under `tests/unit/plugins/modules/`
5. Add integration test target under `tests/integration/targets/`
6. Add a changelog fragment

## PR Guidelines

- Idempotency verified (run twice, assert changed=false on second run)
- ansible-lint profile=production clean
- All DOCUMENTATION/EXAMPLES/RETURN blocks complete
- FQCN used throughout all examples
- Changelog fragment present

## Release Procedure

1. Update version in galaxy.yml
2. Run: `antsibull-changelog release`
3. Commit: `chore: release vX.Y.Z`
4. Tag: `git tag vX.Y.Z`
5. Push tag to trigger release workflow
