# goodolclint.uptime_kuma — Build Instructions for Claude Code

## Service
Uptime Kuma — open-source, self-hosted monitoring tool for HTTP(s), TCP, DNS, and other protocols.

## API Reference
- Python API wrapper (documents all Socket.IO events): https://github.com/lucasheld/uptime-kuma-api
- Uptime Kuma source: https://github.com/louislam/uptime-kuma
- REST API tracking issue: https://github.com/louislam/uptime-kuma/issues/1109

## Mission
This collection provides Ansible modules for managing Uptime Kuma resources — monitors, notifications, status pages, tags, maintenance windows, and API keys — enabling declarative, idempotent configuration of Uptime Kuma instances as part of infrastructure-as-code workflows.

## API Notes
- **No REST API exists.** Uptime Kuma exposes only a Socket.IO (WebSocket) interface. There is no HTTP REST API.
- **Python wrapper**: The `uptime-kuma-api` package at https://github.com/lucasheld/uptime-kuma-api documents all available Socket.IO events and their payloads. This is the de facto API reference.
- **Socket.IO protocol**: The API uses Socket.IO 4.x over WebSocket. Communication is event-based: the client emits named events with JSON payloads and receives responses as events.
- **Auth**: Login event with username/password, or API key-based auth in newer versions.

## Stdlib Constraint
All module code must use only Python standard library modules — `urllib`, `json`, `http.client`. Do not import `requests`, `httpx`, or any third-party HTTP library. No pip dependencies beyond ansible-core are permitted.

**IMPORTANT — DECISION REQUIRED**: Before writing any module code, you must evaluate and document in CONTRIBUTING.md under Architecture Decisions which of the following paths to take. This is the FIRST task when opening this repo:

### OPTION A: stdlib Socket.IO implementation
Implement a minimal Socket.IO 4.x client in `module_utils/socketio_client.py` using only `http.client` and `socket` from the stdlib for the WebSocket upgrade and framing. This is viable but complex — it requires implementing the Engine.IO handshake, WebSocket frame parsing (RFC 6455), and Socket.IO event protocol from scratch.

### OPTION B: uptime-kuma-api pip dependency exception
Declare `uptime-kuma-api` as a documented pip dependency — an explicit, intentional exception to the stdlib-only rule. Document the exception clearly in README.md Requirements section and CONTRIBUTING.md Architecture Decisions. The exception must be justified: "No REST API exists; Socket.IO is the only interface; a stdlib implementation of Socket.IO 4.x is disproportionately complex for the value delivered."

### OPTION C: defer collection
If neither option is acceptable, mark the collection as DEFERRED in README.md with an explanation, and do not write module code until Uptime Kuma ships a REST API (tracked at https://github.com/louislam/uptime-kuma/issues/1109).

**Evaluate all three options, recommend one with written rationale, then implement. Do not ask for confirmation — make the decision and document it.**

## Build Phases

Work through these phases in order. Complete each phase fully before starting the next. Make a git commit at every checkpoint marked → GIT COMMIT.

### Phase 0 — Architecture Decision (MUST BE FIRST)
Evaluate Options A, B, and C above. Write the decision and full rationale in CONTRIBUTING.md under Architecture Decisions. Update README.md Requirements section if Option B is chosen.
→ GIT COMMIT: "docs: document Socket.IO architecture decision"

### Phase 1 — API Research
Study the uptime-kuma-api Python wrapper source to catalogue all Socket.IO events and their payloads. Produce a summary table:
  resource | events (emit/listen) | payload schema | notes
→ GIT COMMIT: "chore: add API research notes"

### Phase 2 — Base API Client
Build `plugins/module_utils/uptime_kuma_api.py` (or `socketio_client.py` if Option A) with:
- Client class appropriate to the chosen architecture
- Connection management (WebSocket lifecycle)
- Event emit/receive with timeout handling
- Auth flow (login event or API key)
- Response normalization returning `(result, changed, diff)` tuples
→ GIT COMMIT: "feat: add UptimeKumaClient base client"

### Phase 3 — Modules
Build one module per resource listed in the Resource Targets section.
→ GIT COMMIT per module: "feat: add uptime_kuma_<resource> module"

### Phase 4 — Integration Tests
→ GIT COMMIT: "test: add integration tests for uptime_kuma modules"

### Phase 5 — Unit Tests
→ GIT COMMIT: "test: add unit tests for uptime_kuma module logic"

### Phase 6 — Role
→ GIT COMMIT: "feat: add uptime_kuma convenience role"

### Phase 7 — CI/CD
→ GIT COMMIT: "chore: add GitHub Actions workflows"

### Phase 8 — Documentation Finalization
→ GIT COMMIT: "docs: finalize README, CONTRIBUTING, CHANGELOG, galaxy.yml"

### Phase 9 — Cleanup Pass
9a–9h as defined in global standards.

## Resource Targets
- `uptime_kuma_monitor` — manage monitors (HTTP, TCP, DNS, ping, etc.)
- `uptime_kuma_monitor_tag` — manage tags on monitors
- `uptime_kuma_notification` — manage notification providers
- `uptime_kuma_status_page` — manage public status pages
- `uptime_kuma_tag` — manage tags
- `uptime_kuma_maintenance` — manage maintenance windows
- `uptime_kuma_api_key` — manage API keys
- `uptime_kuma_settings` — query/update instance settings

## Special Considerations
- **No REST API**: This is the only collection in the goodolclint namespace that does not have a REST API. The architecture decision (Option A/B/C) is the most critical design choice and must be made and documented before any code is written.
- **Socket.IO complexity**: If Option A is chosen, the stdlib Socket.IO client will be the most complex piece of module_utils code in any goodolclint collection. It must handle: HTTP upgrade to WebSocket, WebSocket frame encoding/decoding (RFC 6455), Engine.IO packet protocol, Socket.IO event protocol, and reconnection logic.
- **If Option C (defer)**: Mark all resource targets as "DEFERRED" in this file and README.md. Do not write module code. The scaffold remains for future use.

## Quality Gates
Before marking this collection complete, all of the following must pass:
- [ ] Root docs: README.md, CONTRIBUTING.md, CHANGELOG.rst, galaxy.yml only
- [ ] Architecture decision documented in CONTRIBUTING.md
- [ ] FQCN used throughout all docs and examples
- [ ] ansible-lint profile=production: zero violations
- [ ] flake8: zero violations
- [ ] pylint: zero violations
- [ ] All DOCUMENTATION/EXAMPLES/RETURN blocks complete (no stubs)
- [ ] All modules idempotent (changed=false on second identical run)
- [ ] All modules support check_mode and diff_mode
- [ ] Unit test coverage >80% on module_utils/
- [ ] Integration test targets exist for all modules
- [ ] Git history clean (no RESEARCH.md, no artifacts)
- [ ] Dependency exception documented if Option B chosen
- [ ] Conventional commit messages throughout history
