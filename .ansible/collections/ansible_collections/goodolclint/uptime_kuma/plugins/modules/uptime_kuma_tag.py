#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Clint Branham <goodolclint@gmail.com>
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: uptime_kuma_tag
short_description: Manage tags in Uptime Kuma
version_added: "0.1.0"
description:
  - Create, update, and delete tags in Uptime Kuma.
  - Tags can be assigned to monitors to categorise and group them.
options:
  name:
    description:
      - Name of the tag.
      - Used as the unique identifier for idempotency.
    type: str
    required: true
  color:
    description:
      - Hex colour code for the tag (e.g. C(#ff0000)).
      - Required when O(state=present).
    type: str
  state:
    description:
      - Whether the tag should exist or not.
    type: str
    choices: [present, absent]
    default: present
  api_url:
    description:
      - URL of the Uptime Kuma instance (e.g. C(http://localhost:3001)).
    type: str
    required: true
  api_username:
    description:
      - Username for authentication.
      - Not required if O(api_token) is provided or authentication is disabled.
    type: str
  api_password:
    description:
      - Password for authentication.
      - Not required if O(api_token) is provided or authentication is disabled.
    type: str
  api_token:
    description:
      - Login token for authentication.
      - Mutually exclusive with O(api_username)/O(api_password).
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
- name: Create a tag
  goodolclint.uptime_kuma.uptime_kuma_tag:
    api_url: http://localhost:3001
    api_username: admin
    api_password: secret123
    name: production
    color: "#ff0000"
    state: present

- name: Update a tag colour
  goodolclint.uptime_kuma.uptime_kuma_tag:
    api_url: http://localhost:3001
    api_username: admin
    api_password: secret123
    name: production
    color: "#00ff00"
    state: present

- name: Delete a tag
  goodolclint.uptime_kuma.uptime_kuma_tag:
    api_url: http://localhost:3001
    api_username: admin
    api_password: secret123
    name: production
    state: absent
"""

RETURN = r"""
tag:
  description: The tag object after the operation.
  returned: success
  type: dict
  sample:
    id: 1
    name: production
    color: "#ff0000"
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.goodolclint.uptime_kuma.plugins.module_utils.uptime_kuma_api import (
    UptimeKumaClient,
    UptimeKumaError,
    compute_diff,
    needs_update,
    normalize_result,
    uptime_kuma_argument_spec,
)


def run_module(module):
    """Execute the tag module logic."""
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
    color = module.params["color"]

    existing = client.get_tag_by_name(name)

    if state == "absent":
        if existing is None:
            module.exit_json(changed=False, tag={})
            return
        if module.check_mode:
            module.exit_json(
                changed=True,
                diff=compute_diff(existing, None),
                tag=normalize_result(existing),
            )
            return
        client.delete_tag(existing["id"])
        module.exit_json(
            changed=True,
            diff=compute_diff(existing, None),
            tag={},
        )
        return

    # state == present
    if module.params["color"] is None:
        module.fail_json(msg="Parameter 'color' is required when state=present")

    desired = {"name": name, "color": color}

    if existing is None:
        # Create
        if module.check_mode:
            module.exit_json(
                changed=True,
                diff=compute_diff(None, desired),
                tag=desired,
            )
            return
        result = client.add_tag(name=name, color=color)
        module.exit_json(
            changed=True,
            diff=compute_diff(None, result),
            tag=normalize_result(result),
        )
        return

    # Update if needed
    exclude = {"id"}
    if not needs_update(existing, desired, exclude_keys=exclude):
        module.exit_json(
            changed=False,
            tag=normalize_result(existing),
        )
        return

    if module.check_mode:
        after = dict(existing)
        after.update(desired)
        module.exit_json(
            changed=True,
            diff=compute_diff(existing, after),
            tag=normalize_result(after),
        )
        return

    result = client.edit_tag(existing["id"], name=name, color=color)
    tag_data = result.get("tag", result)
    module.exit_json(
        changed=True,
        diff=compute_diff(existing, tag_data),
        tag=normalize_result(tag_data),
    )


def main():
    """Module entry point."""
    spec = uptime_kuma_argument_spec()
    spec.update(
        name=dict(type="str", required=True),
        color=dict(type="str"),
        state=dict(type="str", choices=["present", "absent"], default="present"),
    )

    module = AnsibleModule(
        argument_spec=spec,
        supports_check_mode=True,
        required_if=[
            ("state", "present", ("color",)),
        ],
    )

    run_module(module)


if __name__ == "__main__":
    main()
