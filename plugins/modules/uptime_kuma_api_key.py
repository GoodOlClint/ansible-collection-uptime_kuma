#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Clint Branham <goodolclint@gmail.com>
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: uptime_kuma_api_key
short_description: Manage API keys in Uptime Kuma
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
  - Create and delete API keys in Uptime Kuma.
  - API keys are identified by O(name) for idempotency.
  - API keys cannot be edited after creation — only created, enabled, disabled, or deleted.
  - The API key value is only returned on creation and cannot be retrieved later.
options:
  name:
    description:
      - Name of the API key.
      - Used as the unique identifier for idempotency.
    type: str
    required: true
  expires:
    description:
      - Expiration date and time as a string (e.g. C(2025-12-31 23:59:00)).
      - Set to C(null) to create a key that does not expire; omitting it leaves an existing key's expiry alone.
      - Uptime Kuma cannot change an existing key's expiry; if it differs the module fails and the key
        must be removed (O(state=absent)) and recreated.
    type: str
  active:
    description:
      - Whether the API key should be active.
    type: bool
    default: true
  state:
    description:
      - Whether the API key should exist or not.
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
- name: Create an API key
  goodolclint.uptime_kuma.uptime_kuma_api_key:
    api_url: http://localhost:3001
    api_username: admin
    api_password: secret123
    name: ci-pipeline
    expires: "2025-12-31 23:59:00"
    active: true
    state: present
  register: api_key_result
  no_log: true

- name: Create an API key that never expires
  goodolclint.uptime_kuma.uptime_kuma_api_key:
    api_url: http://localhost:3001
    api_username: admin
    api_password: secret123
    name: permanent-key
    active: true
    state: present

- name: Delete an API key
  goodolclint.uptime_kuma.uptime_kuma_api_key:
    api_url: http://localhost:3001
    api_username: admin
    api_password: secret123
    name: ci-pipeline
    state: absent
"""

RETURN = r"""
api_key:
  description: The API key object after the operation.
  returned: success
  type: dict
  sample:
    id: 1
    name: ci-pipeline
    active: true
    expires: "2025-12-31 23:59:00"
key:
  description:
    - The API key value.
    - Only returned when a new key is created.
    - This value cannot be retrieved later — store it securely.
    - Returned in clear; set I(no_log) to V(true) on the task that registers it.
  returned: when a new key is created
  type: str
  sample: uk1_9XPRjV7ilGj9CvWRKYiBPq9GLtQs74UzTxKfCxWY
"""

from datetime import datetime, timezone

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.goodolclint.uptime_kuma.plugins.module_utils.uptime_kuma_api import (
    UptimeKumaClient,
    UptimeKumaError,
    compute_diff,
    normalize_result,
    uptime_kuma_argument_spec,
)


def _instant(value):
    """Expiry strings as the server stores them (verbatim) or as the UI sends them (ISO 8601), made comparable."""
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return value
    return parsed.astimezone(timezone.utc).replace(tzinfo=None) if parsed.tzinfo else parsed


def run_module(module):
    """Execute the api_key module logic."""
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
    active = module.params["active"]

    existing = client.get_api_key_by_name(name)

    if state == "absent":
        if existing is None:
            module.exit_json(changed=False, api_key={})
            return
        if module.check_mode:
            module.exit_json(
                changed=True,
                diff=compute_diff(existing, None),
                api_key=normalize_result(existing),
            )
            return
        client.delete_api_key(existing["id"])
        module.exit_json(changed=True, diff=compute_diff(existing, None), api_key={})
        return

    # state == present
    if existing is None:
        expires = module.params.get("expires")
        if module.check_mode:
            result = {"name": name, "active": active, "expires": expires}
            module.exit_json(changed=True, diff=compute_diff(None, result), api_key=result)
            return
        result = client.add_api_key(name=name, expires=expires, active=active)
        key_value = result.get("key", "")
        key_id = result.get("keyID")
        new_key = client.get_api_key(key_id) if key_id else {"name": name, "active": active}
        module.exit_json(
            changed=True,
            diff=compute_diff(None, new_key),
            api_key=normalize_result(new_key),
            key=key_value,
        )
        return

    expires = module.params.get("expires")
    if expires is not None and _instant(existing.get("expires")) != _instant(expires):
        module.fail_json(msg=f"API key '{name}' exists with expires={existing.get('expires')!r}; Uptime Kuma cannot "
                             "change a key's expiry. Remove it with state=absent and recreate it.")
        return

    changed = False
    is_active = existing.get("active", False)

    if active and not is_active:
        if not module.check_mode:
            client.enable_api_key(existing["id"])
        changed = True
    elif not active and is_active:
        if not module.check_mode:
            client.disable_api_key(existing["id"])
        changed = True

    if changed:
        updated = client.get_api_key(existing["id"]) if not module.check_mode else dict(existing, active=active)
        module.exit_json(
            changed=True,
            diff=compute_diff(existing, updated),
            api_key=normalize_result(updated),
        )
    else:
        module.exit_json(changed=False, api_key=normalize_result(existing))


def main():
    """Module entry point."""
    spec = uptime_kuma_argument_spec()
    spec.update(
        name=dict(type="str", required=True),
        expires=dict(type="str"),
        active=dict(type="bool", default=True),
        state=dict(type="str", choices=["present", "absent"], default="present"),
    )

    module = AnsibleModule(
        argument_spec=spec,
        supports_check_mode=True,
        required_one_of=[("api_password", "api_token")],
        mutually_exclusive=[("api_token", "api_password")],
    )

    run_module(module)


if __name__ == "__main__":
    main()
