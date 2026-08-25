# goodolclint.uptime_kuma.uptime_kuma

Declaratively manage an Uptime Kuma 2.x instance from variable lists: notifications, tags, monitors, monitor tags, status pages, maintenance windows, API keys and settings.

The role logs in once with `uptime_kuma_login` and passes the session token to every task, because Uptime Kuma limits password logins to 20 per minute. Set `uptime_kuma_api_token` to skip the login entirely.

## Requirements

- `python-socketio[client] >= 5.0` on the control node (the modules run where the play runs; use `delegate_to: localhost` if targeting a remote host).
- Uptime Kuma 2.x reachable at `uptime_kuma_api_url`.

## Variables

| Variable | Default | Purpose |
|---|---|---|
| `uptime_kuma_api_url` | `http://localhost:3001` | Instance URL |
| `uptime_kuma_api_username` / `uptime_kuma_api_password` | `""` | Admin credentials; used for the single login and for `uptime_kuma_bootstrap_admin` |
| `uptime_kuma_api_token` | `""` | Session token; when set, no password login is performed |
| `uptime_kuma_validate_certs` | `true` | TLS verification |
| `uptime_kuma_api_timeout` | `30` | Socket.IO request timeout in seconds |
| `uptime_kuma_bootstrap_admin` | `false` | Create the admin account on a fresh instance (`uptime_kuma_setup`) before anything else |
| `uptime_kuma_monitor_defaults` | `{}` | Dict merged under every entry of `uptime_kuma_monitors` |
| `uptime_kuma_notifications` | `[]` | `uptime_kuma_notification` items |
| `uptime_kuma_tags` | `[]` | `uptime_kuma_tag` items |
| `uptime_kuma_monitors` | `[]` | `uptime_kuma_monitor` items; every module option is passed through |
| `uptime_kuma_monitor_tags` | `[]` | `uptime_kuma_monitor_tag` items (`monitor_name`, `tag_name`, `value`) |
| `uptime_kuma_status_pages` | `[]` | `uptime_kuma_status_page` items |
| `uptime_kuma_maintenances` | `[]` | `uptime_kuma_maintenance` items |
| `uptime_kuma_api_keys` | `[]` | `uptime_kuma_api_key` items; a newly created key's value is only available on the run that created it, as `uptime_kuma_api_keys_result.results[*].key` (the task runs with `no_log`, so a failure in it reports only that output was hidden) |
| `uptime_kuma_settings` | `{}` | Keys for `uptime_kuma_settings`; skipped when empty |

Each list item accepts the corresponding module's options by the same name plus `state` (default `present`). Notifications are managed before monitors so monitors can reference them with `notification_names`.

## Example

```yaml
- hosts: localhost
  roles:
    - role: goodolclint.uptime_kuma.uptime_kuma
      vars:
        uptime_kuma_api_url: http://kuma.example.com:3001
        uptime_kuma_api_username: admin
        uptime_kuma_api_password: "{{ kuma_admin_password }}"
        uptime_kuma_bootstrap_admin: true
        uptime_kuma_notifications:
          - name: ntfy
            notification_type: ntfy
            is_default: true
            notification_config:
              ntfyserverurl: https://ntfy.sh
              ntfytopic: "{{ ntfy_topic }}"
        uptime_kuma_monitor_defaults:
          max_retries: 2
          timeout: 16
          notification_names: [ntfy]
        uptime_kuma_monitors:
          - name: Website
            monitor_type: http
            url: https://example.com
            accepted_statuscodes: ["200-299", "300-399"]
          - name: DNS
            monitor_type: dns
            hostname: example.com
            dns_resolve_server: 1.1.1.1
            port: 53
```

A second run with the same variables reports `changed: false`.

## License

GPL-3.0-or-later
