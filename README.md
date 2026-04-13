# goodolclint.uptime_kuma

Ansible collection for managing Uptime Kuma monitors via its API.

## Requirements

- ansible-core >= 2.14
- Python >= 3.9
- `uptime-kuma-api >= 1.2.0` (pip install required on the control node)

### Why a pip dependency?

Uptime Kuma does not expose a REST API — the only programmatic interface is
Socket.IO 4.x over WebSocket. Implementing a Socket.IO client from scratch using
only the Python standard library would be disproportionately complex. This
collection uses the community `uptime-kuma-api` wrapper as a documented exception
to the stdlib-only rule. See [CONTRIBUTING.md](CONTRIBUTING.md) for the full
architecture decision record.

```bash
pip install 'uptime-kuma-api>=1.2.0'
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
        uptime_kuma_tags:
          - name: production
            color: "#28a745"
        uptime_kuma_monitors:
          - name: Example Website
            monitor_type: http
            url: "https://example.com"
            interval: 60
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

GPL-3.0-or-later
