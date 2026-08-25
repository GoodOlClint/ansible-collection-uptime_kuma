# goodolclint.uptime_kuma

Ansible collection for managing Uptime Kuma 2.x — monitors, notifications, tags, status pages, maintenance windows, API keys and settings — over its Socket.IO interface.

## Requirements

- ansible-core >= 2.16
- Python >= 3.10
- `python-socketio[client] >= 5.0` on the host the modules run on (the control node unless you `delegate_to` elsewhere)
- Uptime Kuma **2.x** (tested against `louislam/uptime-kuma:2`; 1.x is not supported)

### Why a pip dependency?

Uptime Kuma does not expose a REST API — the only programmatic interface is Socket.IO 4.x over WebSocket. Implementing Engine.IO and WebSocket framing from the Python standard library would be disproportionately complex, so this collection talks to Uptime Kuma through the maintained `python-socketio` protocol library. The Uptime Kuma event protocol itself lives in this repo (`plugins/module_utils/uptime_kuma_api.py`) and is pinned by integration tests against a real 2.x container. See [ADR 0001](docs/decisions/0001-in-repo-python-socketio-client-replaces-the-uptime-kuma-api-wrapper-uptime-kuma-2-x-only.md).

```bash
pip install 'python-socketio[client]>=5.0'
```

### Local development instance

```bash
tests/dev/up.sh          # starts louislam/uptime-kuma:2 on :3001 and creates admin / Ansible-Dev-Pass-1
tests/dev/up.sh fresh    # recreates the volume and leaves setup to the suite; then run it once with -e uptime_kuma_fresh_instance=true
tests/dev/up.sh down     # tears it down
```

## Installation

```bash
ansible-galaxy collection install goodolclint.uptime_kuma
```

## Included Content

### Modules

| Module | Description |
|--------|-------------|
| `goodolclint.uptime_kuma.uptime_kuma_monitor` | Manage monitors (HTTP, TCP, DNS, ping, and more) |
| `goodolclint.uptime_kuma.uptime_kuma_monitor_tag` | Manage tags on monitors |
| `goodolclint.uptime_kuma.uptime_kuma_notification` | Manage notification providers |
| `goodolclint.uptime_kuma.uptime_kuma_status_page` | Manage public status pages |
| `goodolclint.uptime_kuma.uptime_kuma_tag` | Manage tags |
| `goodolclint.uptime_kuma.uptime_kuma_maintenance` | Manage maintenance windows |
| `goodolclint.uptime_kuma.uptime_kuma_api_key` | Manage API keys |
| `goodolclint.uptime_kuma.uptime_kuma_settings` | Query and update instance settings |
| `goodolclint.uptime_kuma.uptime_kuma_setup` | Create the initial admin account on a fresh instance |
| `goodolclint.uptime_kuma.uptime_kuma_login` | Obtain a session token; password logins are rate-limited to 20/min, token logins are not |

### Roles

| Role | Description |
|------|-------------|
| `goodolclint.uptime_kuma.uptime_kuma` | Declaratively manage all Uptime Kuma resources via variable lists |

## Usage

### Module Examples

```yaml
- name: Create an HTTP monitor
  goodolclint.uptime_kuma.uptime_kuma_monitor:
    api_url: "http://localhost:3001"
    api_username: admin
    api_password: secret
    name: Example Website
    monitor_type: http
    url: "https://example.com"
    interval: 60
    state: present

- name: Create a tag
  goodolclint.uptime_kuma.uptime_kuma_tag:
    api_url: "http://localhost:3001"
    api_username: admin
    api_password: secret
    name: production
    color: "#28a745"
    state: present

- name: Create a notification
  goodolclint.uptime_kuma.uptime_kuma_notification:
    api_url: "http://localhost:3001"
    api_username: admin
    api_password: secret
    name: Slack Alert
    notification_type: slack
    notification_config:
      slackwebhookURL: "https://hooks.slack.com/services/xxx"
    state: present

- name: Query instance settings
  goodolclint.uptime_kuma.uptime_kuma_settings:
    api_url: "http://localhost:3001"
    api_username: admin
    api_password: secret
    state: query
  register: current_settings
```

### Role Example

```yaml
- hosts: localhost
  roles:
    - role: goodolclint.uptime_kuma.uptime_kuma
      vars:
        uptime_kuma_api_url: "http://localhost:3001"
        uptime_kuma_api_username: admin
        uptime_kuma_api_password: secret
        uptime_kuma_bootstrap_admin: true        # create the admin on a fresh instance
        uptime_kuma_notifications:
          - name: ntfy
            notification_type: ntfy
            is_default: true
            notification_config:
              ntfyserverurl: https://ntfy.sh
              ntfytopic: "{{ ntfy_topic }}"
        uptime_kuma_monitor_defaults:            # merged under every monitor
          max_retries: 2
          timeout: 16
          notification_names: [ntfy]
        uptime_kuma_tags:
          - name: production
            color: "#28a745"
        uptime_kuma_monitors:
          - name: Example Website
            monitor_type: http
            url: "https://example.com"
            accepted_statuscodes: ["200-299", "300-399"]
          - name: Lobby
            monitor_type: json-query
            url: "http://host:8080/status.json"
            json_path: platform
            expected_value: playfab
        uptime_kuma_monitor_tags:
          - monitor_name: Example Website
            tag_name: production
```

The role logs in once and reuses the session token; Uptime Kuma limits password logins to 20 per minute, so playbooks that call modules directly should do the same with `uptime_kuma_login`.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

GPL-3.0-or-later
