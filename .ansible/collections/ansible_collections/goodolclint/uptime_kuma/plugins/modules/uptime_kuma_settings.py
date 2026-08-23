#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Clint Branham <goodolclint@gmail.com>
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: uptime_kuma_settings
short_description: Manage instance settings in Uptime Kuma
version_added: "0.1.0"
description:
  - Query or update Uptime Kuma instance-level settings.
  - When O(state=query), returns the current settings without making changes.
  - When O(state=present), updates settings to match the specified values.
options:
  check_update:
    description:
      - Show update notification if a new version is available.
    type: bool
  check_beta:
    description:
      - Also check for beta releases.
    type: bool
  keep_data_period_days:
    description:
      - Number of days to keep monitor history data. Set to 0 for infinite retention.
    type: int
  server_timezone:
    description:
      - Server timezone (e.g. C(America/New_York)).
    type: str
  entry_page:
    description:
      - Entry page for the Uptime Kuma dashboard.
    type: str
    choices: [dashboard, statusPage]
  search_engine_index:
    description:
      - Whether to allow search engine indexing.
    type: bool
  primary_base_url:
    description:
      - Primary base URL for the instance.
    type: str
  steam_api_key:
    description:
      - Steam Web API key for monitoring Steam game servers.
    type: str
  dns_cache:
    description:
      - Enable DNS caching.
    type: bool
  tls_expiry_notify_days:
    description:
      - List of day thresholds for TLS certificate expiry notifications.
    type: list
    elements: int
  disable_auth:
    description:
      - Disable authentication for the instance.
      - When enabling this, O(password) is required to confirm the action.
    type: bool
  trust_proxy:
    description:
      - Trust X-Forwarded headers from reverse proxies.
    type: bool
  password:
    description:
      - Current password, required when changing O(disable_auth).
    type: str
  state:
    description:
      - C(present) updates settings to match specified values.
      - C(query) returns current settings without making changes.
    type: str
    choices: [present, query]
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
- name: Query current settings
  goodolclint.uptime_kuma.uptime_kuma_settings:
    api_url: http://localhost:3001
    api_username: admin
    api_password: secret123
    state: query
  register: current_settings

- name: Update settings
  goodolclint.uptime_kuma.uptime_kuma_settings:
    api_url: http://localhost:3001
    api_username: admin
    api_password: secret123
    check_update: false
    keep_data_period_days: 90
    server_timezone: America/New_York
    dns_cache: true
    tls_expiry_notify_days: [7, 14, 21]
    state: present

- name: Disable authentication
  goodolclint.uptime_kuma.uptime_kuma_settings:
    api_url: http://localhost:3001
    api_username: admin
    api_password: secret123
    disable_auth: true
    password: secret123
    state: present
"""

RETURN = r"""
settings:
  description: The instance settings after the operation.
  returned: success
  type: dict
  sample:
    checkUpdate: false
    checkBeta: false
    keepDataPeriodDays: 180
    serverTimezone: America/New_York
    entryPage: dashboard
    searchEngineIndex: false
    dnsCache: true
    disableAuth: false
    trustProxy: false
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

# steamAPIKey and password are write-only
WRITE_ONLY_FIELDS = {"steamAPIKey", "password"}


def run_module(module):
    """Execute the settings module logic."""
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
    current = client.get_settings()

    if state == "query":
        module.exit_json(changed=False, settings=normalize_result(current))
        return

    # state == present — build desired settings
    desired = {}
    mappings = {
        "check_update": "checkUpdate",
        "check_beta": "checkBeta",
        "keep_data_period_days": "keepDataPeriodDays",
        "server_timezone": "serverTimezone",
        "entry_page": "entryPage",
        "search_engine_index": "searchEngineIndex",
        "primary_base_url": "primaryBaseURL",
        "steam_api_key": "steamAPIKey",
        "dns_cache": "dnsCache",
        "tls_expiry_notify_days": "tlsExpiryNotifyDays",
        "disable_auth": "disableAuth",
        "trust_proxy": "trustProxy",
    }

    for param_name, api_name in mappings.items():
        value = module.params.get(param_name)
        if value is not None:
            desired[api_name] = value

    if not desired:
        module.exit_json(changed=False, settings=normalize_result(current))
        return

    if not needs_update(current, desired, exclude_keys=WRITE_ONLY_FIELDS):
        module.exit_json(changed=False, settings=normalize_result(current))
        return

    if module.check_mode:
        after = dict(current)
        after.update(desired)
        module.exit_json(
            changed=True,
            diff=compute_diff(current, after),
            settings=normalize_result(after),
        )
        return

    # Add password if provided (needed for disableAuth changes)
    set_kwargs = dict(desired)
    if module.params.get("password"):
        set_kwargs["password"] = module.params["password"]

    client.set_settings(**set_kwargs)
    updated = client.get_settings()
    module.exit_json(
        changed=True,
        diff=compute_diff(current, updated),
        settings=normalize_result(updated),
    )


def main():
    """Module entry point."""
    spec = uptime_kuma_argument_spec()
    spec.update(
        check_update=dict(type="bool"),
        check_beta=dict(type="bool"),
        keep_data_period_days=dict(type="int"),
        server_timezone=dict(type="str"),
        entry_page=dict(type="str", choices=["dashboard", "statusPage"]),
        search_engine_index=dict(type="bool"),
        primary_base_url=dict(type="str"),
        steam_api_key=dict(type="str", no_log=True),
        dns_cache=dict(type="bool"),
        tls_expiry_notify_days=dict(type="list", elements="int"),
        disable_auth=dict(type="bool"),
        trust_proxy=dict(type="bool"),
        password=dict(type="str", no_log=True),
        state=dict(type="str", choices=["present", "query"], default="present"),
    )

    module = AnsibleModule(
        argument_spec=spec,
        supports_check_mode=True,
    )

    run_module(module)


if __name__ == "__main__":
    main()
