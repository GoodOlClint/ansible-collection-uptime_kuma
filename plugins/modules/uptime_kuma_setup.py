#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Clint Branham <goodolclint@gmail.com>
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: uptime_kuma_setup
short_description: Create the initial admin account on a fresh Uptime Kuma
version_added: "0.2.0"
requirements:
  - python-socketio[client] >= 5.0 on the host the module runs on
attributes:
  check_mode:
    description: Can run in check_mode and return changed status prediction without modifying target.
    support: full
  diff_mode:
    description: Will return details on what has changed (or possibly needs changing in check_mode), when in diff mode.
    support: none
description:
  - Performs the first-run setup of an Uptime Kuma instance by creating the admin user.
  - Does nothing when the instance has already been set up.
  - The instance must have its database selected already; with the official container
    set C(UPTIME_KUMA_DB_TYPE=sqlite) (or the MariaDB variables) so the database page is skipped.
options:
  username:
    description:
      - Username of the admin account to create.
    type: str
    required: true
  password:
    description:
      - Password of the admin account. Uptime Kuma rejects weak passwords.
    type: str
    required: true
  api_url:
    description:
      - URL of the Uptime Kuma instance.
    type: str
    required: true
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
- name: Create the admin account on first boot
  goodolclint.uptime_kuma.uptime_kuma_setup:
    api_url: http://localhost:3001
    username: admin
    password: "{{ uptime_kuma_admin_password }}"
"""

RETURN = r"""
setup_performed:
  description: Whether the admin account was created by this run.
  returned: success
  type: bool
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.goodolclint.uptime_kuma.plugins.module_utils.uptime_kuma_api import (
    UptimeKumaClient,
    UptimeKumaError,
)


def run_module(module):
    client = UptimeKumaClient(module, login=False)
    try:
        if not client.need_setup():
            module.exit_json(changed=False, setup_performed=False)
        if not module.check_mode:
            client.setup(module.params["username"], module.params["password"])
        module.exit_json(changed=True, setup_performed=not module.check_mode)
    except UptimeKumaError as exc:
        module.fail_json(msg=f"Uptime Kuma API error: {exc}")
    finally:
        client.disconnect()


def main():
    module = AnsibleModule(
        argument_spec=dict(
            api_url=dict(type="str", required=True),
            validate_certs=dict(type="bool", default=True),
            api_timeout=dict(type="int", default=30),
            username=dict(type="str", required=True),
            password=dict(type="str", required=True, no_log=True),
        ),
        supports_check_mode=True,
    )
    run_module(module)


if __name__ == "__main__":
    main()
