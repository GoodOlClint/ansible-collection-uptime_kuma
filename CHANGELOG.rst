======================================
goodolclint.uptime\_kuma Release Notes
======================================

.. contents:: Topics

v0.3.0
======

Release Summary
---------------

Drift detection and credential comparison across every module, create-time validation for each targeted monitor type, monitors created with ``active=false`` are never started, sensitive fields scrubbed from results and diffs. Contains breaking changes and one deprecation; see the sections below.

Minor Changes
-------------

- all modules - document ``requirements`` and check/diff mode support in ``attributes``; the documented ansible-core floor is 2.16, matching ``meta/runtime.yml`` and CI.
- all modules - the ``api_username``, ``api_password`` and ``api_token`` descriptions state the credential constraints.
- client - removed the unused ``version`` property and ``get_status_pages``, ``pause_maintenance`` and ``resume_maintenance`` methods.
- uptime_kuma_login and uptime_kuma_api_key - document that the returned token / key is in clear and the registering task should set ``no_log``.
- uptime_kuma_maintenance - ``duration_minutes`` documentation now states it only applies to ``strategy=cron``.
- uptime_kuma_maintenance - ``time_range`` documentation states that ``seconds`` is optional and defaults to 0.
- uptime_kuma_monitor - accepts the monitor types Uptime Kuma 2.x has added (manual, ntp, oracledb, sip-options, websocket-upgrade).
- uptime_kuma_monitor and uptime_kuma_notification - credentials are compared like every other field, so a rotated password or token is applied and the next run reports no change; they are still never part of the result or diff (ADR 0003). The previous "write-only" exclusion made credential rotation a silent no-op.
- uptime_kuma_monitor_tag - returns a diff for added and removed assignments.
- uptime_kuma_notification - documentation states that a key removed from ``notification_config`` is not removed on the server.
- uptime_kuma_status_page - ``google_analytics_id`` is stored as Uptime Kuma 2.x ``analyticsId`` with ``analyticsType=google`` (the 1.x key it used before was ignored by the server); the public group list is fetched only when ``public_group_list`` is managed.
- uptime_kuma_status_page - managing ``public_group_list`` reads the page once instead of twice.

Breaking Changes / Porting Guide
--------------------------------

- Python 3.9 is no longer supported on the host the modules run on; the floor is 3.10 (the CI matrix).
- the eight resource modules - require ``api_password`` or ``api_token`` at argument-spec level, and reject ``api_token`` together with ``api_password``; ``api_username`` may accompany a token and is ignored. Tasks that set both must drop ``api_password``; instances with authentication disabled must now supply a credential (the previous documentation said none was needed).
- uptime_kuma_api_key - a different ``expires`` on an existing key now fails with a remove-and-recreate message instead of being silently ignored (Uptime Kuma cannot edit a key's expiry).
- uptime_kuma_monitor - ``accepted_statuscodes`` no longer defaults to ``200-299`` on every run, so an unset option no longer resets a value edited in the UI; when unset on create it defaults to ``200-299``, or to the ``1000`` close code for ``websocket-upgrade`` monitors, which were previously created permanently down.
- uptime_kuma_monitor - creating a monitor without the option(s) its type needs now fails up front instead of creating a permanently-down monitor: ``url`` for http, keyword, json-query, real-browser and websocket-upgrade (plus ``keyword`` for keyword, ``json_path`` and ``expected_value`` for json-query); ``hostname`` for ping, dns, ntp, radius and tailscale-ping; ``hostname`` and ``port`` for port, sip-options, steam, gamedig and mqtt (plus ``mqtt_topic``); ``docker_container`` and ``docker_host`` for docker; ``database_connection_string`` for sqlserver, postgres, mysql, mongodb, redis and oracledb. Updates still merge into the server's copy.
- uptime_kuma_monitor - the returned ``monitor`` and diff omit every field Uptime Kuma classifies as sensitive (``headers``, ``body``, ``basic_auth_pass``, ``bearer_token``, ``tlsKey``, ``pushToken``, ...); a push monitor's URL is read in the UI.
- uptime_kuma_monitor_tag - ``state=absent`` on an assignment stored with a NULL value now fails with an explanation (the server cannot match it) instead of silently reporting no change (the module's empty value never matched the NULL row, so it never issued a delete).
- uptime_kuma_notification - the returned ``notification`` carries only ``id``, ``name``, ``type``, ``isDefault`` and ``active``; provider configuration keys (webhook URLs, tokens, ...) are no longer part of the result or diff.
- uptime_kuma_settings - the returned ``settings`` and diff omit ``steamAPIKey``.
- uptime_kuma_status_page - ``published`` no longer has any effect: Uptime Kuma 2.x does not change it after creation, so it is neither sent nor compared (it previously reported ``changed=true`` on every run when set to ``false``).

Deprecated Features
-------------------

- uptime_kuma_status_page - ``published`` is deprecated and will be removed in version 1.0.0; Uptime Kuma 2.x ignores it after creation.

Security Fixes
--------------

- uptime_kuma role - the login, session-token and API-key tasks run with ``no_log`` so the admin session token and newly created API keys no longer reach ``-v`` output. Created keys are available to the caller as ``uptime_kuma_api_keys_result.results[*].key`` on the run that created them.
- uptime_kuma_monitor - every field Uptime Kuma classifies as sensitive (``headers``, ``body``, ``basic_auth_pass``, ``oauth_client_secret``, ``tlsKey``, ``pushToken``, ``radiusPassword``, ``mqttPassword``, ``databaseConnectionString``, ...) is omitted from the returned ``monitor`` and the diff, and ``headers``/``body`` are now ``no_log``. They were returned in clear for monitors whose secrets were set in the UI or by another task.
- uptime_kuma_notification - ``notification_config`` is now ``no_log`` (values under credential-looking keys stay masked; other values are unmasked so results remain readable), and provider configuration is no longer part of the returned ``notification`` or the diff at all. Previously provider secrets appeared in task output, ``--diff``, ``invocation.module_args`` and the target's syslog, while the documentation claimed they were treated as no_log.
- uptime_kuma_settings - ``steamAPIKey`` is omitted from the returned ``settings`` and the diff (``state=query`` returned it in clear).

Bugfixes
--------

- client - Socket.IO transport errors (connection dropped, namespace not connected) and HTTP/JSON errors when reading a public status page now fail with a message instead of a traceback.
- client - ``setup`` is no longer retried; a retry after a slow first-boot ack reported failure on a run that had succeeded.
- client - a missing list re-push after a mutation now reports a timeout instead of a misleading "not found".
- client - a public status page body that is not a JSON object is reported as a read error instead of an ``AttributeError``.
- client - the retried requests (``login``, ``loginByToken``, ``needSetup``) wait at least 10 s per attempt (``api_timeout``, floored at 10) instead of a fixed 3 s. Uptime Kuma 2.5 can take about 3.5 s to answer a password login, so every attempt timed out (``Authentication failed: Timed out waiting for 'login' reply``) while the server logged one successful login per retry and each retry consumed the 20/min password-login budget.
- client - the status page slug is URL-encoded in the public endpoint path.
- uptime_kuma role - passes every module option through for maintenance windows, status pages and settings; eight options each were silently dropped, so scheduled maintenance strategies could not be expressed through the role although the role README said they could.
- uptime_kuma_login - a login that succeeds without returning a token (2FA-enabled account) now fails instead of returning ``token: null``.
- uptime_kuma_maintenance - a changed ``timezone`` on an existing window is now applied.
- uptime_kuma_monitor - creating a monitor with ``active=false`` now sends ``active`` in the create payload so the server never starts it; previously the monitor was created running and paused a round trip later, so its target was probed once anyway.
- uptime_kuma_monitor and uptime_kuma_api_key - the check-mode diff and result now show the predicted ``active`` state (they showed the current one).
- uptime_kuma_monitor_tag - a tag assignment stored with an empty (NULL) value no longer gets a duplicate row on the first run.
- uptime_kuma_notification - changes to ``notification_config`` on an existing notification are now detected and applied; previously only ``name``, ``notification_type`` and ``is_default`` were compared, so a changed webhook URL or topic reported ``changed=false`` and was never written.
- uptime_kuma_settings - a ``steam_api_key``-only change is now written; the key was wrongly treated as unreadable.
- uptime_kuma_settings - disabling authentication without ``password`` now fails up front instead of at the server.
- uptime_kuma_status_page - ``description``, ``footer_text``, ``google_analytics_id``, ``show_certificate_expiry``, ``domain_name_list`` and ``public_group_list`` are now compared on an existing page instead of being silently ignored after creation.
- uptime_kuma_status_page - an ``api_timeout`` on the lookup is now reported as a timeout instead of being treated as "page does not exist" (which made ``state=present`` try to create a duplicate and ``state=absent`` silently skip).
- uptime_kuma_status_page - the check-mode create result now includes ``slug`` and ``title``.

v0.2.1
======

Release Summary
---------------

Idempotency fix for monitors managed by the role.

Bugfixes
--------

- uptime_kuma_monitor - ``dns_resolve_server``, ``dns_resolve_type`` and ``json_path_operator`` no longer carry module defaults; they were sent (and compared) for every monitor type, so any monitor created in the UI or by another tool reported a change on every run. Creation still falls back to Uptime Kuma's own defaults.

v0.2.0
======

Release Summary
---------------

Targets Uptime Kuma 2.x. The ``uptime-kuma-api`` wrapper is replaced by an in-repo client on ``python-socketio`` (ADR 0001); integration tests run against ``louislam/uptime-kuma:2`` in CI.

Minor Changes
-------------

- uptime_kuma role - passes the full monitor option set; new ``uptime_kuma_monitor_defaults``, ``uptime_kuma_monitor_tags`` and ``uptime_kuma_bootstrap_admin`` variables; logs in once and reuses the token (password logins are rate-limited to 20/min by Uptime Kuma).
- uptime_kuma_monitor - new options ``timeout``, ``resend_interval``, ``json_path``, ``json_path_operator``, ``expected_value``, ``invert_keyword``, ``parent`` (group by name) and ``notification_names``.
- uptime_kuma_monitor - notification linkage compares as a set, so ``notification_ids`` no longer reports a change on every run.

Breaking Changes / Porting Guide
--------------------------------

- Default ``api_timeout`` raised from 10 to 30 seconds.
- Requires ``python-socketio[client]`` instead of ``uptime-kuma-api`` on the control node.
- Uptime Kuma 1.x is no longer supported.

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
