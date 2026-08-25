# Gap report — goodolclint.uptime_kuma (2026-08-25)

## Verdict

The collection is green on every gate it currently runs (45 unit tests, flake8/pylint/ansible-lint clean, 90/90 integration tasks pass against `louislam/uptime-kuma:2`), and the *create / delete / re-run-unchanged* paths of every module work. The gaps are in what the gates do not cover: **five modules silently ignore drift on existing resources**, **three modules return server-side secrets in their result and diff**, `ansible-test sanity` has never run (two failures today), and unit coverage of `module_utils` is 41% against an 80% gate. None of the confirmed bugs is caught by the existing suites, because no integration target re-runs after an update and no unit test covers 7 of the 10 modules.

## Method

Five parallel lanes plus ground truth: Codex full scan (49/49 citations self-verified; converged with the other lanes on every HIGH and contributed A7, C11, C12, E6, E7), correctness reviewer, security reviewer, test-coverage reviewer, docs/CI/packaging sweep; then local runs of pytest+coverage, flake8, pylint, ansible-lint, `ansible-test sanity`, the full integration suite, and three probe playbooks/scripts against a fresh 2.x container to confirm or refute each hypothesis. Every finding below is marked **Live** (reproduced against the server), **Code** (verified by reading the code; not reproduced), or **Refuted**. Reviewer claims that did not survive verification are listed at the end so nobody chases them.

## Findings

### A. Idempotency defects — drift on existing resources is silently ignored

| ID | Sev | Where | Defect | Evidence |
|----|-----|-------|--------|----------|
| A1 | HIGH | `plugins/modules/uptime_kuma_notification.py:222` | `desired_check` compares only name/type/isDefault; any `notification_config` change (webhook URL, ntfy topic, …) reports `changed=False` and is never written. `edit_notification` is dead in practice. | Live: topic A→B, `changed=False`, server still A |
| A2 | HIGH | `plugins/modules/uptime_kuma_status_page.py:246-252` | Only title/theme/published/showTags/showPoweredBy/customCSS are compared; `description`, `footerText`, `googleAnalyticsId`, `showCertificateExpiry`, `domainNameList`, `publicGroupList` drift is ignored — the module cannot change which monitors a page shows after creation. The integration target hides it by dropping `description` from the re-run. | Live: description A→B, `changed=False` |
| A3 | MED | `plugins/modules/uptime_kuma_settings.py:173,222` | `steamAPIKey` is excluded as "write-only" but `getSettings` returns it; setting only `steam_api_key` reports `changed=False` and never writes. Order-dependent: it is written only when another setting also differs. | Live: steam-only → `changed=False`; raw `setSettings`+`getSettings` round-trips the key |
| A4 | MED | `plugins/modules/uptime_kuma_maintenance.py:267` | `timezoneOption` is excluded from comparison, but the server round-trips it verbatim (`UTC`→`UTC`); a `timezone` change is never applied. | Live: server returns `timezoneOption: UTC` |
| A5 | MED | `plugins/modules/uptime_kuma_api_key.py:188-209` | `expires` is only used on create; changing it on an existing key is a silent no-op. Uptime Kuma has no edit-key event, so the fix is to fail loudly (or delete+recreate). | Code |
| A6 | LOW | `plugins/modules/uptime_kuma_monitor_tag.py:117` | A tag assignment stored with `value: NULL` (UI-created) is not matched by the default `value: ""`; the first run inserts a duplicate row, then stabilises. | Live: run1 `changed=True`, 2 rows; run2 `changed=False` |
| A7 | MED | `plugins/modules/uptime_kuma_monitor.py:505`, `uptime_kuma_notification.py:223` | Write-only credentials (`mqttPassword`, `databaseConnectionString`, `smtpPassword`, …) are excluded from comparison and there is no alternate path, so a credential-only rotation is a silent no-op. ADR-002 accepts the exclusion but never defined how rotation happens. | Code |

### B. Secrets in output

| ID | Sev | Where | Defect | Evidence |
|----|-----|-------|--------|----------|
| B1 | HIGH | `uptime_kuma_notification.py:49,209,213-218,254` | `notification_config` is `no_log=False`; tokens/webhooks land in the return value, `--diff`, `invocation.module_args`, and syslog on the target. The DOCUMENTATION claims the opposite ("treated as no_log"). `WRITE_ONLY_FIELDS` exists but is only used for comparison, never for scrubbing. | Live: `ntfyaccesstoken` in `notification` return |
| B2 | HIGH | `uptime_kuma_monitor.py:466-468,494-532` | `getMonitor` returns the sensitive variant; `basic_auth_pass`, `oauth_client_secret`, `radiusPassword`, `radiusSecret`, `mqttPassword`, `tlsKey`, `pushToken`, `gamedigToken`, `rabbitmqPassword` are returned and diffed. Ansible masks only values passed as no_log params *this run*, so UI-set credentials leak (including on `state: absent`). | Live: all nine keys present in `monitor` return |
| B3 | MED | `uptime_kuma_settings.py:190-247` | `state: query` and every update return `steamAPIKey` in the clear. | Live: readback after set |
| B4 | MED | `uptime_kuma_login.py:94`, `uptime_kuma_api_key.py:177-184`, `roles/uptime_kuma/tasks/main.yml:14-26,153-165`, `tests/integration/run.yml:13-22` | Session token and created API key are returned unmasked with no guidance; role and run.yml `set_fact` the token without `no_log`, so it hits `-v` output and fact caches. Role creates API keys without registering or masking them. | Code |

### C. Client robustness (`plugins/module_utils/uptime_kuma_api.py`)

| ID | Sev | Line | Defect |
|----|-----|------|--------|
| C1 | MED | 362-367 | `get_status_page_config` maps *every* `UptimeKumaError` (including ack timeout) to "page does not exist" → a slow server makes `state: present` try to create a duplicate and `state: absent` silently skip. |
| C2 | MED | 191-197 | Only `TimeoutError` is caught; `ConnectionError`/`DisconnectedError`/`BadNamespaceError` escape as raw tracebacks (`MODULE FAILURE`) if the server drops mid-run. |
| C3 | MED | 369-380 | `open_url` `HTTPError`/`URLError` and `JSONDecodeError` in `get_status_page` are not translated to `UptimeKumaError` → traceback on any status-page update behind a proxy/error page. |
| C4 | MED | 232-233 | `setup` is retried but is not idempotent: if attempt 1 succeeds server-side but the ack exceeds 10 s, attempt 2 fails "already initialized" and the module reports failure on a run that worked. |
| C5 | LOW | 215-220 | `_expect` ignores the wait result; a missed re-push surfaces as `notification <id> not found` instead of a timeout. |
| C6 | LOW | 160-165 | 2FA-enabled account: `login` returns `ok: true` without `token`; `uptime_kuma_login` exits successfully with `token: None`. |
| C7 | LOW | 518-519 | `_comparable` calls `int()` on any all-`True` dict's keys → `ValueError` on a future non-numeric field. |
| C8 | LOW | 371 | `slug` interpolated into the URL path without `quote()`. |
| C9 | LOW | 223-226, 357-359, 431-435 | Dead code: `version`, `get_status_pages`, `pause_maintenance`, `resume_maintenance` are called by nothing. |
| C10 | LOW | `uptime_kuma_monitor.py:529`, `uptime_kuma_api_key.py:202`, `uptime_kuma_status_page.py:228` | Check-mode diff is empty when only `active` changes; check-mode create returns an object without `slug`/`title`. |
| C11 | LOW | `uptime_kuma_monitor.py:488-491` | Creating with `active: false` fetches the monitor *before* pausing it, so the returned object and diff show `active: true`. |
| C12 | INFO | 193 | `socketio.Client.call` is documented upstream as not thread-safe; no module calls it concurrently today, so this is latent. Document the client as single-thread. |

### D. Test and CI gaps

| ID | Sev | Gap |
|----|-----|-----|
| D1 | HIGH | `ansible-test sanity` is not in CI and has never run. Today it fails `validate-modules` twice: `uptime_kuma_login.py` docs reference non-existent option `api_token`; `uptime_kuma_monitor.py` `keyword` needs `no_log=False`. |
| D2 | HIGH | Unit coverage: `module_utils` **41%** (gate >80%); `api_key`, `login`, `maintenance`, `monitor_tag`, `notification`, `settings`, `setup`, `status_page` at **0%**. CI runs pytest without `--cov`. |
| D3 | HIGH | No integration target re-runs after an update except `settings`; notification/maintenance/status_page have no update path at all. This is exactly why A1–A4 shipped. |
| D4 | MED | Untested in any suite: check-mode create/update results, monitor `active: false` (pause) and API-key enable, `diff` payloads, maintenance strategies other than `manual`, `setup` first run (`first is changed` never asserted), `login` (fixture only), the role entirely. |
| D5 | MED | Six targets (`monitor`, `tag`, `notification`, `maintenance`, `status_page`, `api_key`) have no `always:` cleanup; a mid-target failure poisons the next local run. |
| D6 | LOW | Test quality: settings target restores a hard-coded `keep_data_period_days: 180` instead of the queried original (mutates a real dev instance); duplicate basename `test_uptime_kuma_api.py` in two dirs (issue #14); `sys.path.insert(0, ".")` in three tests; `test_create_new_tag` runs `_run_module` twice against an all-MagicMock client before its real assertion; `test_uptime_kuma_api.py:37` asserts the timeout equals the constant the code reads (tautology); module tests use bare MagicMock clients so reply-shape drift (`monitorID`, `keyID`) is unpinned. |
| D7 | MED | Workflows: `claude.yml:32-43` fires on any `@claude` mention from any GitHub user with `contents: write` and no author gate; `ci.yml` has no `permissions:` block; `release.yml` passes `GALAXY_API_KEY` on argv and publishes on tag without gating on CI; no `concurrency:`; lint tool versions float. |

### E. Docs, packaging, role

| ID | Sev | Gap |
|----|-----|-----|
| E1 | HIGH | `changelogs/changelog.yaml` does not exist, but `config.yaml` sets `changes_file: changelog.yaml` + `keep_fragments: false`. The documented release step `antsibull-changelog release` will regenerate `CHANGELOG.rst` from empty history and drop the hand-written v0.1.0–v0.2.1 sections; `release.yml`'s grep gate would not catch it. |
| E2 | MED | `CONTRIBUTING.md`: "Running Tests" says `ansible-test integration --docker` (no `aliases`, cannot work; real entry is `ansible-playbook tests/integration/run.yml`); the Architecture Decisions body still presents Option B / `uptime-kuma-api` as Accepted with only a one-line "superseded" header. |
| E3 | MED | Version floors disagree: `meta/runtime.yml` `>=2.16.0` vs README/CONTRIBUTING/role `2.14`; Python `>=3.9` claimed, CI proves 3.10–3.12. |
| E4 | MED | Role drops 8 options each for maintenance, status_page, settings while `roles/uptime_kuma/README.md` claims parity (issue #10). |
| E6 | MED | Docs vs behaviour: `uptime_kuma_maintenance` documents `duration_minutes` generally and uses it in non-cron examples, but `_build_maintenance_kwargs` (line 198-200) sends it only for `strategy: cron`. `uptime_kuma_monitor` claims "all monitor types" but its `choices` omit 2.x types (`snmp`, `rabbitmq`, `smtp`, `manual`). README says `python-socketio` is needed on the "control node"; modules run on the execution host unless `delegate_to: localhost`. |
| E7 | LOW | Input validation is thin: no type-specific `required_if` (e.g. `url` for `http`, `hostname` for `port`/`ping`), no numeric bounds on `interval`/`timeout`/`port`, `time_range` is `elements: dict` with no suboptions, and `disable_auth` is documented as needing `password` with no constraint. Server-side errors catch most of these late. |
| E5 | LOW | `CLAUDE.md:28` still carries the "DECISION REQUIRED" Option A/B/C gate that ADR 0001 already settled. Module docs lack `requirements:` (python-socketio), `attributes:` (check/diff mode), and per-option `version_added:`; `CLAUDE.md` Resource Targets omits `uptime_kuma_login`/`uptime_kuma_setup`; `uptime_kuma_argument_spec` has no `required_one_of` for credentials; `galaxy.yml` lacks `documentation:` and its `description` mentions only monitors; `claude.yml` carries a stale comment about "issue #43" from another repo. |

### Refuted (do not chase)

- `editTag` reply lacks a `tag` key → **Refuted**, 2.x returns `{ok, msg, tag}`.
- Maintenance `active: false` is not idempotent → **Refuted**, round-trips cleanly.
- `monitor_tag` re-adds on every run → only one duplicate for NULL-valued rows (A6), then stable.
- Server rejects `timeout` > `interval` → **Refuted**, `interval: 20`/`timeout: 48` accepted.
- `actions/*@v7` pins violate the house rule → the rule is a floor ("current major"); v7 is current and CI is green. Not a gap.
- The Explore lane's "root docs only" gate → `CLAUDE.md` is required by the review workflow; amend the gate wording, don't remove the file.

## Closure plan

Ordered by blast radius; each tranche is one PR sized to review in one sitting, test-pinned, and lands with a changelog fragment. Existing issues are folded in where they belong rather than duplicated.

| # | Tranche | Scope | Acceptance | Size |
|---|---------|-------|------------|------|
| 0 | **Make the gates real** | Add `ansible-test sanity` job to `ci.yml` and fix D1's two failures. Add `--cov=plugins --cov-fail-under=40` to the unit job (ratchet to 80 in tranche 5). Consolidate the two `test_uptime_kuma_api.py` files (#14), drop `sys.path` hacks. Author `changelogs/changelog.yaml` reproducing v0.1.0–v0.2.1 and verify `antsibull-changelog generate` is a no-op against `CHANGELOG.rst` (E1). | sanity green; coverage floor enforced; `antsibull-changelog lint` + `generate` clean | S |
| 1 | **Stop leaking secrets** | One `scrub(data, keys)` helper in `module_utils`; apply at every `exit_json`/`compute_diff` site in notification, monitor, settings using the existing `WRITE_ONLY_FIELDS` sets (extend monitor's with `tlsKey`, `tlsCert`, `tlsCa`, `pushToken`, `gamedigToken`, `rabbitmqPassword`). Add `notification_config` values to `module.no_log_values`. Fix the false doc claim (B1). `no_log: true` on role login/set_fact/notification/api_key tasks and `run.yml`; RETURN docs for `login.token` and `api_key.key` say to register with `no_log`. Correct the `steamAPIKey` comment. | Unit test per module asserting no scrubbed key in `result` or `diff`; integration asserts `notification` return lacks config keys | M |
| 2 | **Fix drift detection** | A1: compare `kwargs` minus `applyExisting`. A2: compare all of `save_kwargs`; compare `publicGroupList` against the public endpoint normalised to name/weight/monitor ids. A3: drop `steamAPIKey` from the exclusion. A4: normalise `timezoneOption` (`None` ↔ `SAME_AS_SERVER`) instead of excluding. A5: fail with a delete-and-recreate message when `expires` differs. A6: `(tag.get("value") or "") == (value or "")`. A7: add a single `update_secrets: bool` option (monitor, notification, settings) that forces a write when supplied write-only values may have changed; amend ADR-002 to name the excluded keys per module and point at this option as the rotation path. E6: confirm on the server whether `durationMinutes` applies to recurring strategies, then either send it for all or narrow the docs; add `disable_auth`→`password` `required_if`. | Each target gains: update task → `is changed`, verbatim re-run → `is not changed`, drift task on a previously-ignored field → `is changed` (D3). Unit tests for each compare path. | M |
| 3 | **Client robustness** | C1: distinct `UptimeKumaTimeout` so only `ok: false` maps to "not found". C2: catch `SocketIOError` in `_call`. C3: wrap `open_url`/`json.loads`. C4: drop `retry=True` from `setup` (or re-check `needSetup` between attempts). C5: raise on `_expect` timeout. C6: raise when login returns no token. C7: gate `_comparable` on numeric keys. C8: `quote(slug)`. C9: delete dead methods. C11: pause before the final `get_monitor` on create. Fold in issue #13 (wait for `info` before the first request — the upstream-recommended workaround for [uptime-kuma#7710](https://github.com/louislam/uptime-kuma/issues/7710); derive per-attempt timeout from `api_timeout`; bound password-login retries). Consider `_ansible_no_log=True` on `login`/`api_key` create results as the B4 mechanism. | Unit tests for every new branch (mock `sio.call`), taking `module_utils` coverage past 80% | M |
| 4 | **Workflow hardening** | `claude.yml`: author-association gate, drop `contents: write` unless the bot must push. `ci.yml`: top-level `permissions: contents: read`, `concurrency:`, pin lint tool versions. `release.yml`: secret via `env:`, require the CI workflow to be green for the tagged SHA before publishing. Remove the stale "#43" comment. | Workflows lint clean; a tag on a red commit does not publish | S |
| 5 | **Test debt** | Unit tests for the seven 0% modules (create/no-change/update/delete/check-mode/fail paths, `fail_json` raising). Integration: `always:` cleanup in the six targets; check-mode create/update asserts; `setup` first-run and `login` asserts; a role target (two monitors + `monitor_defaults`, second run no changes); maintenance `recurring-weekday` and `cron`. Ratchet `--cov-fail-under` to 80. Fix D6 quality items. | Coverage ≥80% on `module_utils`, every module ≥70%; standards Phase 4 sequence present in every target | L |
| 6 | **Docs & role** | Role passes every module option (#10) and its README becomes true. CONTRIBUTING: rewrite Architecture Decisions to state the current answer inline (ADR 0001) and fix the test instructions. Align version floors (pick 2.16 / Python 3.10 to match CI, or extend CI). Add `requirements:`, `attributes:`, `version_added:` to module docs; add the missing 2.x monitor types (or state the subset); `required_one_of` for credentials plus the E7 type-specific `required_if` and numeric bounds; README execution-host wording; drop the stale `CLAUDE.md` gate; `CLAUDE.md` Resource Targets += login/setup; `galaxy.yml` `documentation:`. Amend the standards "root docs only" gate to allow `CLAUDE.md`. | sanity + ansible-doc clean; role integration target from tranche 5 passes | M |
| — | **Parked** | #15 (API-key login): Uptime Kuma 2.x API keys authenticate only the HTTP `/metrics` and push endpoints, not the Socket.IO `login` event; expect to close as not-possible after a source check and instead rely on tranche 3's token reuse. | | |

Tranches 0–2 close every HIGH. Tranches 1 and 2 touch the same three modules and are kept separate on purpose: tranche 1 changes what is *returned*, tranche 2 changes what is *compared*, and each is independently testable.
