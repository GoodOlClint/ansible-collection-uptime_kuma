# goodolclint.uptime_kuma — Build Instructions for Claude Code

## Service
Uptime Kuma — open-source, self-hosted monitoring tool for HTTP(s), TCP, DNS, and other protocols.

## API Reference
- Python API wrapper (documents all Socket.IO events): https://github.com/lucasheld/uptime-kuma-api
- Uptime Kuma source: https://github.com/louislam/uptime-kuma
- REST API tracking issue: https://github.com/louislam/uptime-kuma/issues/1109

## Mission
This collection provides Ansible modules for managing Uptime Kuma resources — monitors, notifications, status pages, tags, maintenance windows, and API keys — enabling declarative, idempotent configuration of Uptime Kuma instances as part of infrastructure-as-code workflows.

## Architecture
- Decisions live in `docs/decisions/`. Binding: [ADR 0001](docs/decisions/0001-in-repo-python-socketio-client-replaces-the-uptime-kuma-api-wrapper-uptime-kuma-2-x-only.md) — in-repo `python-socketio` client, Uptime Kuma 2.x only. `plugins/module_utils/uptime_kuma_api.py` is the single protocol layer; modules never emit Socket.IO events directly.
- Write-only credentials: [ADR 0003](docs/decisions/0003-credentials-are-compared-normally-and-never-returned-nothing-on-uptime-kuma-2-x-is-write-only.md) — nothing on 2.x is write-only: credentials are compared like any other field and never returned.
- PR review gating: [ADR 0002](docs/decisions/0002-pr-review-gating-tamper-proof-claude-review-as-a-required-check-codeowners-for-policy-paths.md) — instructions in `.github/review-prompt.md`, materialized from main; `claude-review` is a required check; CODEOWNERS mirrors the prompt's defer list.
- Dev instance: `tests/dev/docker-compose.yml` (`louislam/uptime-kuma:2`). Integration targets run against it locally and against the same image in CI.

## API Notes
- **No REST API exists.** Uptime Kuma exposes only a Socket.IO (WebSocket) interface. There is no HTTP REST API.
- **Python wrapper**: The `uptime-kuma-api` package at https://github.com/lucasheld/uptime-kuma-api documents all available Socket.IO events and their payloads. This is the de facto API reference.
- **Socket.IO protocol**: The API uses Socket.IO 4.x over WebSocket. Communication is event-based: the client emits named events with JSON payloads and receives responses as events.
- **Auth**: Login event with username/password, or API key-based auth in newer versions.

@~/Source/ansible-collection-standards.md

## Constraints (repo-specific)
The Socket.IO client decision (stdlib client vs. `uptime-kuma-api` vs. defer) is settled by [ADR 0001](docs/decisions/0001-in-repo-python-socketio-client-replaces-the-uptime-kuma-api-wrapper-uptime-kuma-2-x-only.md): an in-repo client on `python-socketio[client]`, the one documented exception to the shared stdlib-only rule. Do not re-open it.

## Build Phase Details (repo-specific)

### Phase 0 — Architecture Decision (done)
Settled by ADR 0001 (in-repo `python-socketio` client, 2.x only) and recorded in CONTRIBUTING.md and README.md. Nothing to do here.

### Phase 1 — API Research
Study the uptime-kuma-api Python wrapper source to catalogue all Socket.IO events and their payloads. Produce a summary table:
  resource | events (emit/listen) | payload schema | notes

### Phase 2 — Base API Client
`plugins/module_utils/uptime_kuma_api.py` provides:
- Client class appropriate to the chosen architecture
- Connection management (WebSocket lifecycle)
- Event emit/receive with timeout handling
- Auth flow (login event or API key)
- Response normalization returning `(result, changed, diff)` tuples
→ GIT COMMIT: "feat: add UptimeKumaClient base client"

## Resource Targets
- `uptime_kuma_monitor` — manage monitors (HTTP, TCP, DNS, ping, etc.)
- `uptime_kuma_monitor_tag` — manage tags on monitors
- `uptime_kuma_notification` — manage notification providers
- `uptime_kuma_status_page` — manage public status pages
- `uptime_kuma_tag` — manage tags
- `uptime_kuma_maintenance` — manage maintenance windows
- `uptime_kuma_api_key` — manage API keys
- `uptime_kuma_settings` — query/update instance settings
- `uptime_kuma_setup` — create the initial admin account
- `uptime_kuma_login` — obtain a session token for reuse

## Special Considerations
- **No REST API**: This is the only collection in the goodolclint namespace without a REST API; the protocol layer is the in-repo Socket.IO client (ADR 0001). Event names and payload shapes are pinned by the integration suite against `louislam/uptime-kuma:2`; verify a server behaviour against that image (or the upstream source) before relying on it.
- **Credentials**: nothing the modules manage is write-only on 2.x (ADR 0003); credentials are compared normally and never returned.

## Quality Gates (repo-specific)
In addition to the shared Quality Gates:
- [ ] Architecture decision documented in CONTRIBUTING.md
- [ ] `python-socketio[client]` remains the only pip dependency and stays documented as the exception to the shared "Stdlib-only confirmed" gate
