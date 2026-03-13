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

## Usage

<!-- Module index and examples will be added during development -->

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

GPL-3.0-or-later
