#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Clint Branham <goodolclint@gmail.com>
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: uptime_kuma_monitor_tag
short_description: Manage tag assignments on monitors in Uptime Kuma
version_added: "0.1.0"
description:
  - Assign or remove tags from monitors in Uptime Kuma.
  - Uses the combination of O(tag_name), O(monitor_name), and O(value) as the
    unique identifier for idempotency.
options:
  tag_name:
    description:
      - Name of the tag to assign or remove.
    type: str
    required: true
  monitor_name:
    description:
      - Name of the monitor to assign the tag to.
    type: str
    required: true
  value:
    description:
      - Optional value for the tag assignment.
    type: str
    default: ""
  state:
    description:
      - Whether the tag assignment should exist or not.
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
    type: str
  api_password:
    description:
      - Password for authentication.
    type: str
  api_token:
    description:
      - Login token for authentication.
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
- name: Assign a tag to a monitor
  goodolclint.uptime_kuma.uptime_kuma_monitor_tag:
    api_url: http://localhost:3001
    api_username: admin
    api_password: secret123
    tag_name: production
    monitor_name: My Website
    value: web
    state: present

- name: Remove a tag from a monitor
  goodolclint.uptime_kuma.uptime_kuma_monitor_tag:
    api_url: http://localhost:3001
    api_username: admin
    api_password: secret123
    tag_name: production
    monitor_name: My Website
    state: absent
"""

RETURN = r"""
monitor_tag:
  description: Information about the tag assignment.
  returned: success
  type: dict
  sample:
    tag_id: 1
    monitor_id: 1
    value: web
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.goodolclint.uptime_kuma.plugins.module_utils.uptime_kuma_api import (
    UptimeKumaClient,
    UptimeKumaError,
    normalize_result,
    uptime_kuma_argument_spec,
)


def _find_monitor_tag(monitor, tag_id, value):
    """Check if a monitor has a specific tag assignment."""
    for tag in monitor.get("tags", []):
        if tag.get("tag_id") == tag_id and tag.get("value", "") == value:
            return tag
    return None


def run_module(module):
    """Execute the monitor_tag module logic."""
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
    tag_name = module.params["tag_name"]
    monitor_name = module.params["monitor_name"]
    value = module.params["value"]

    # Resolve tag by name
    tag = client.get_tag_by_name(tag_name)
    if tag is None:
        module.fail_json(msg=f"Tag '{tag_name}' not found")

    # Resolve monitor by name
    monitor = client.get_monitor_by_name(monitor_name)
    if monitor is None:
        module.fail_json(msg=f"Monitor '{monitor_name}' not found")

    tag_id = tag["id"]
    monitor_id = monitor["id"]
    existing = _find_monitor_tag(monitor, tag_id, value)

    result_data = {"tag_id": tag_id, "monitor_id": monitor_id, "value": value}

    if state == "absent":
        if existing is None:
            module.exit_json(changed=False, monitor_tag={})
            return
        if module.check_mode:
            module.exit_json(changed=True, monitor_tag=result_data)
            return
        client.delete_monitor_tag(tag_id, monitor_id, value)
        module.exit_json(changed=True, monitor_tag={})
        return

    # state == present
    if existing is not None:
        module.exit_json(changed=False, monitor_tag=normalize_result(result_data))
        return

    if module.check_mode:
        module.exit_json(changed=True, monitor_tag=result_data)
        return

    client.add_monitor_tag(tag_id, monitor_id, value)
    module.exit_json(changed=True, monitor_tag=result_data)


def main():
    """Module entry point."""
    spec = uptime_kuma_argument_spec()
    spec.update(
        tag_name=dict(type="str", required=True),
        monitor_name=dict(type="str", required=True),
        value=dict(type="str", default=""),
        state=dict(type="str", choices=["present", "absent"], default="present"),
    )

    module = AnsibleModule(
        argument_spec=spec,
        supports_check_mode=True,
    )

    run_module(module)


if __name__ == "__main__":
    main()
