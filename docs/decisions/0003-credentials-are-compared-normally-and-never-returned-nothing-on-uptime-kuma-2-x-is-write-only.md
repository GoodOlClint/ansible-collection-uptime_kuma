# ADR 0003 — Credentials are compared like any other field and never returned; nothing on Uptime Kuma 2.x is write-only

- **Status:** Accepted
- **Date:** 2026-08-25
- **Deciders:** operator + agent
- **Context source:** docs/gap-report-2026-08-25.md findings A3, A7 · CONTRIBUTING.md ADR-002 (superseded) · server source of `louislam/uptime-kuma:2` read during the tranche-2 review

## Context

CONTRIBUTING.md ADR-002 assumed some credential fields are write-only (set but never read back) and excluded them from the idempotency comparison so they would not report `changed=true` on every run. The gap report showed the consequences: `steamAPIKey` was excluded although `getSettings` returns it, so a task setting only `steam_api_key` never wrote it (A3), and a rotated `mqtt_password` or `smtpPassword` was a silent no-op with no way to apply it (A7).

The first draft of this record kept the exclusion and added an `update_secrets` option as the rotation path. Reading the 2.x server source during review refuted the premise: `sendNotificationList` ships each notification's `config` JSON verbatim, and both the monitor list and `getMonitor` use `Monitor.toJSON()` with `includeSensitiveData` defaulting to true. Every credential the modules manage is readable by the authenticated client. The only value the server never returns is the `password` argument of `setSettings`, which is an authorisation for the `disableAuth` change, not a setting.

## Decision

- No field is treated as write-only. Every managed field, credentials included, is compared normally, so a rotated credential is detected and applied like any other change and a second run reports `changed=false`.
- Credentials are never part of a module's return value or diff (the tranche-1 scrub rule: `SENSITIVE_FIELDS` on monitors, the `id`/`name`/`type`/`isDefault`/`active` allow-list on notifications, `steamAPIKey` on settings). Comparing a value the module does not echo leaks nothing.
- There is no `update_secrets` option. `uptime_kuma_settings.password` stays a one-shot authorisation, required only when `disable_auth` flips from false to true (the transition the server checks).

## Rejected alternatives

- **Keep the exclusion and add `update_secrets: true` to force a write.** Solves a problem the server does not have, and a user who leaves it on to make rotation work gets `changed=true` on every run.
- **Always send supplied credentials and report `changed=true`.** Breaks the second-run contract for every play that carries a secret.
- **Document delete-and-recreate as the rotation path.** Loses monitor history and ids (status-page and tag references) and drops notification links.

## Consequences

- `WRITE_ONLY_FIELDS` is removed from the notification, monitor and settings modules; the monitor's former set is folded into `SENSITIVE_FIELDS` (output scrubbing only).
- If a future Uptime Kuma release stops returning a credential, that field becomes a perpetual change and this record must be revisited — the integration suite's rotate-then-rerun assertions will show it.
- CONTRIBUTING.md ADR-002 is superseded by this record.
