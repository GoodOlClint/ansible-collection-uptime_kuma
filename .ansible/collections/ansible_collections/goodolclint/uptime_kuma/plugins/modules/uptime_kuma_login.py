#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Clint Branham <goodolclint@gmail.com>
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: uptime_kuma_login
short_description: Obtain a login token from Uptime Kuma
version_added: "0.2.0"
description:
  - Logs in with username and password and returns the session token.
  - Uptime Kuma rate-limits password logins to 20 per minute but not token logins, so
    playbooks that run many tasks should log in once and pass the token as O(api_token)
    to every other module.
  - Never reports changed.
options:
  api_url:
    description:
      - URL of the Uptime Kuma instance.
    type: str
    required: true
  api_username:
    description:
      - Username for authentication.
    type: str
    required: true
  api_password:
    description:
      - Password for authentication.
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
- name: Log in once
  goodolclint.uptime_kuma.uptime_kuma_login:
    api_url: http://localhost:3001
    api_username: admin
    api_password: secret123
  register: kuma

- name: Use the token for every other task
  goodolclint.uptime_kuma.uptime_kuma_tag:
    api_url: http://localhost:3001
    api_token: "{{ kuma.token }}"
    name: production
    color: "#ff0000"
"""

RETURN = r"""
token:
  description: Session token to pass as C(api_token).
  returned: success
  type: str
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.goodolclint.uptime_kuma.plugins.module_utils.uptime_kuma_api import (
    UptimeKumaClient,
)


def main():
    module = AnsibleModule(
        argument_spec=dict(
            api_url=dict(type="str", required=True),
            api_username=dict(type="str", required=True),
            api_password=dict(type="str", required=True, no_log=True),
            validate_certs=dict(type="bool", default=True),
            api_timeout=dict(type="int", default=30),
        ),
        supports_check_mode=True,
    )
    client = UptimeKumaClient(module)
    client.disconnect()
    module.exit_json(changed=False, token=client.token)


if __name__ == "__main__":
    main()
