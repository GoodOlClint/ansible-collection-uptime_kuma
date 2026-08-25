#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Clint Branham <goodolclint@gmail.com>
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: uptime_kuma_notification
short_description: Manage notification providers in Uptime Kuma
version_added: "0.1.0"
requirements:
  - python-socketio[client] >= 5.0 on the host the module runs on
attributes:
  check_mode:
    description: Can run in check_mode and return changed status prediction without modifying target.
    support: full
  diff_mode:
    description: Will return details on what has changed (or possibly needs changing in check_mode), when in diff mode.
    support: full
description:
  - Create, update, and delete notification providers in Uptime Kuma.
  - Supports all 56+ notification provider types (Slack, Discord, Telegram, etc.).
  - Notifications are identified by O(name) for idempotency.
  - Provider-specific options are passed via the O(notification_config) dictionary.
options:
  name:
    description:
      - Name of the notification provider.
      - Used as the unique identifier for idempotency.
    type: str
    required: true
  notification_type:
    description:
      - Type of notification provider.
      - Required when O(state=present).
    type: str
  is_default:
    description:
      - Whether this notification is enabled by default for new monitors.
    type: bool
    default: false
  apply_existing:
    description:
      - Apply this notification to all existing monitors.
    type: bool
    default: false
  notification_config:
    description:
      - Dictionary of provider-specific configuration options.
      - Keys and values depend on the chosen O(notification_type).
      - For example, for Discord provide C(discordWebhookUrl).
      - For Slack provide C(slackwebhookURL).
      - Keys are compared and written individually. A key removed from this dictionary is not removed on
        the server and its old value stays in effect; set it to an empty string explicitly, or remove and
        recreate the notification.
      - Treated as no_log. Values whose key looks like a credential (password, token, key, webhook, URL, ...)
        are masked wherever they appear; other values are shown so results stay readable.
      - Provider configuration is never part of RV(notification) or the diff, whether it was set by this task
        or read back from the server. It is compared, so a changed value (including a rotated credential)
        is applied.
    type: dict
    default: {}
  state:
    description:
      - Whether the notification provider should exist or not.
    type: str
    choices: [present, absent]
    default: present
  api_url:
    description:
      - URL of the Uptime Kuma instance.
    type: str
    required: true
  api_username:
    description:
      - Username for authentication.
      - Not required if O(api_token) is provided.
    type: str
  api_password:
    description:
      - Password for authentication.
      - Not required if O(api_token) is provided.
    type: str
  api_token:
    description:
      - Login token for authentication.
      - Mutually exclusive with O(api_password).
    type: str
  validate_certs:
    description:
      - Whether to validate SSL certificates.
    type: bool
    default: true
  api_timeout:
    description:
      - Timeout in seconds for API requests.
    type: int
    default: 30
author:
  - Clint Branham (@goodolclint)
"""

EXAMPLES = r"""
- name: Create a Slack notification
  goodolclint.uptime_kuma.uptime_kuma_notification:
    api_url: http://localhost:3001
    api_username: admin
    api_password: secret123
    name: Slack Alerts
    notification_type: slack
    notification_config:
      slackwebhookURL: https://hooks.slack.com/services/XXX/YYY/ZZZ
    state: present

- name: Create a Discord notification
  goodolclint.uptime_kuma.uptime_kuma_notification:
    api_url: http://localhost:3001
    api_username: admin
    api_password: secret123
    name: Discord Alerts
    notification_type: discord
    notification_config:
      discordWebhookUrl: https://discord.com/api/webhooks/XXX/YYY
    state: present

- name: Delete a notification
  goodolclint.uptime_kuma.uptime_kuma_notification:
    api_url: http://localhost:3001
    api_username: admin
    api_password: secret123
    name: Slack Alerts
    state: absent
"""

RETURN = r"""
notification:
  description:
    - The notification provider object after the operation.
    - Only C(id), C(name), C(type), C(isDefault) and C(active); provider configuration is never returned.
  returned: success
  type: dict
  sample:
    id: 1
    name: Slack Alerts
    type: slack
    isDefault: false
"""

import re

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.goodolclint.uptime_kuma.plugins.module_utils.uptime_kuma_api import (
    UptimeKumaClient,
    UptimeKumaError,
    needs_update,
    normalize_result,
    uptime_kuma_argument_spec,
)

# Provider config keys that look like credentials stay masked; the rest are unmasked
# after argument parsing so short values (ports, hosts) do not shred the result.
_SECRET_KEY = re.compile(r"pass|secret|token|key|webhook|url|auth|nsec|sender|credential|sid", re.IGNORECASE)
_RETURNED_KEYS = {"id", "name", "type", "isDefault", "active"}


def _out(notification):
    return normalize_result({k: v for k, v in (notification or {}).items() if k in _RETURNED_KEYS})


def _diff(before, after):
    return {"before": _out(before), "after": _out(after)}


def _unmask_benign_config(module, config):
    secret = {str(v) for k, v in config.items() if _SECRET_KEY.search(k)}
    module.no_log_values.difference_update(
        str(v) for k, v in config.items()
        if not _SECRET_KEY.search(k) and not isinstance(v, (bool, dict, list)) and str(v) not in secret
    )


def run_module(module):
    """Execute the notification module logic."""
    client = UptimeKumaClient(module)
    try:
        _run(module, client)
    except UptimeKumaError as exc:
        module.fail_json(msg=f"Uptime Kuma API error: {exc}")
    finally:
        client.disconnect()


def _run(module, client):
    """Inner logic separated for clean disconnect handling."""
    state = module.params["state"]
    name = module.params["name"]
    _unmask_benign_config(module, module.params.get("notification_config") or {})

    existing = client.get_notification_by_name(name)

    if state == "absent":
        if existing is None:
            module.exit_json(changed=False, notification={})
            return
        if module.check_mode:
            module.exit_json(
                changed=True,
                diff=_diff(existing, None),
                notification=_out(existing),
            )
            return
        client.delete_notification(existing["id"])
        module.exit_json(changed=True, diff=_diff(existing, None), notification={})
        return

    # state == present
    notification_type = module.params["notification_type"]
    if notification_type is None:
        module.fail_json(msg="Parameter 'notification_type' is required when state=present")

    config = module.params.get("notification_config") or {}
    kwargs = {
        "name": name,
        "type": notification_type,
        "isDefault": module.params["is_default"],
        "applyExisting": module.params["apply_existing"],
    }
    kwargs.update(config)

    if existing is None:
        if module.check_mode:
            module.exit_json(changed=True, diff=_diff(None, kwargs), notification=_out(kwargs))
            return
        result = client.add_notification(**kwargs)
        notification_id = result.get("id")
        new_notif = client.get_notification(notification_id) if notification_id else result
        module.exit_json(
            changed=True,
            diff=_diff(None, new_notif),
            notification=_out(new_notif),
        )
        return

    # Check for updates
    desired_check = {k: v for k, v in kwargs.items() if k != "applyExisting"}
    if not needs_update(existing, desired_check):
        module.exit_json(changed=False, notification=_out(existing))
        return

    if module.check_mode:
        after = dict(existing)
        after.update(desired_check)
        module.exit_json(
            changed=True,
            diff=_diff(existing, after),
            notification=_out(after),
        )
        return

    client.edit_notification(existing["id"], **kwargs)
    updated = client.get_notification(existing["id"])
    module.exit_json(
        changed=True,
        diff=_diff(existing, updated),
        notification=_out(updated),
    )


def main():
    """Module entry point."""
    spec = uptime_kuma_argument_spec()
    spec.update(
        name=dict(type="str", required=True),
        notification_type=dict(type="str"),
        is_default=dict(type="bool", default=False),
        apply_existing=dict(type="bool", default=False),
        notification_config=dict(type="dict", default={}, no_log=True),
        state=dict(type="str", choices=["present", "absent"], default="present"),
    )

    module = AnsibleModule(
        argument_spec=spec,
        supports_check_mode=True,
        required_one_of=[("api_password", "api_token")],
        mutually_exclusive=[("api_token", "api_password")],
        required_if=[
            ("state", "present", ("notification_type",)),
        ],
    )

    run_module(module)


if __name__ == "__main__":
    main()
