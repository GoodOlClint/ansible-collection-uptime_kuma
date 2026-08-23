==========================================
goodolclint.uptime_kuma Release Notes
==========================================

.. contents:: Topics

v0.2.0
======

Release Summary
---------------
Targets Uptime Kuma 2.x. The ``uptime-kuma-api`` wrapper is replaced by an in-repo client on ``python-socketio`` (ADR 0001); integration tests run against ``louislam/uptime-kuma:2`` in CI.

Breaking Changes / Porting Guide
--------------------------------
- Requires ``python-socketio[client]`` instead of ``uptime-kuma-api`` on the control node.
- Uptime Kuma 1.x is no longer supported.
- Default ``api_timeout`` raised from 10 to 30 seconds.

Minor Changes
-------------
- uptime_kuma_monitor - new options ``timeout``, ``resend_interval``, ``json_path``, ``json_path_operator``, ``expected_value``, ``invert_keyword``, ``parent`` (group by name) and ``notification_names``.
- uptime_kuma_monitor - notification linkage compares as a set, so ``notification_ids`` no longer reports a change on every run.
- uptime_kuma role - passes the full monitor option set; new ``uptime_kuma_monitor_defaults``, ``uptime_kuma_monitor_tags`` and ``uptime_kuma_bootstrap_admin`` variables; logs in once and reuses the token (password logins are rate-limited to 20/min by Uptime Kuma).

Bugfixes
--------
- uptime_kuma_maintenance - ``cron`` and ``duration_minutes`` are only compared for ``strategy=cron``; other strategies no longer report a change on every run.
- uptime_kuma_status_page - lookups by slug work after creation (Uptime Kuma 2.x pushes the page list only at login).

New Modules
-----------
- goodolclint.uptime_kuma.uptime_kuma_login - Obtain a session token for reuse across tasks.
- goodolclint.uptime_kuma.uptime_kuma_setup - Create the initial admin account on a fresh instance.

v0.1.0
======

Release Summary
---------------
Initial release of the goodolclint.uptime_kuma collection.

New Modules
-----------
- goodolclint.uptime_kuma.uptime_kuma_api_key - Manage Uptime Kuma API keys.
- goodolclint.uptime_kuma.uptime_kuma_maintenance - Manage Uptime Kuma maintenance windows.
- goodolclint.uptime_kuma.uptime_kuma_monitor - Manage Uptime Kuma monitors.
- goodolclint.uptime_kuma.uptime_kuma_monitor_tag - Manage tags on Uptime Kuma monitors.
- goodolclint.uptime_kuma.uptime_kuma_notification - Manage Uptime Kuma notification providers.
- goodolclint.uptime_kuma.uptime_kuma_settings - Query and update Uptime Kuma instance settings.
- goodolclint.uptime_kuma.uptime_kuma_status_page - Manage Uptime Kuma public status pages.
- goodolclint.uptime_kuma.uptime_kuma_tag - Manage Uptime Kuma tags.

New Roles
---------
- goodolclint.uptime_kuma.uptime_kuma - Declaratively manage all Uptime Kuma resources via variable lists.
