#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Clint Branham <goodolclint@gmail.com>
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: uptime_kuma_maintenance
short_description: Manage maintenance windows in Uptime Kuma
version_added: "0.1.0"
description:
  - Create, update, and delete maintenance windows in Uptime Kuma.
  - Maintenance windows are identified by O(title) for idempotency.
options:
  title:
    description:
      - Title of the maintenance window.
      - Used as the unique identifier for idempotency.
    type: str
    required: true
  strategy:
    description:
      - Maintenance scheduling strategy.
      - Required when O(state=present).
    type: str
    choices: [manual, single, recurring-interval, recurring-weekday, recurring-day-of-month, cron]
  active:
    description:
      - Whether the maintenance window is active.
    type: bool
    default: true
  description:
    description:
      - Description of the maintenance window.
    type: str
    default: ""
  date_range:
    description:
      - List of date strings for the maintenance window.
    type: list
    elements: str
  interval_day:
    description:
      - Interval in days for recurring-interval strategy.
    type: int
    default: 1
  weekdays:
    description:
      - List of weekday numbers (0-6) for recurring-weekday strategy.
    type: list
    elements: int
  days_of_month:
    description:
      - List of day numbers (1-31) for recurring-day-of-month strategy.
    type: list
    elements: int
  time_range:
    description:
      - List of time range dicts with C(hours) and C(minutes) keys.
    type: list
    elements: dict
  cron:
    description:
      - Cron expression for cron strategy.
    type: str
    default: "30 3 * * *"
  duration_minutes:
    description:
      - Duration in minutes for the maintenance window.
    type: int
    default: 60
  timezone:
    description:
      - Timezone for the maintenance schedule.
    type: str
  state:
    description:
      - Whether the maintenance window should exist or not.
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
- name: Create a manual maintenance window
  goodolclint.uptime_kuma.uptime_kuma_maintenance:
    api_url: http://localhost:3001
    api_username: admin
    api_password: secret123
    title: Server Upgrade
    strategy: manual
    description: Upgrading server hardware
    state: present

- name: Create a recurring weekly maintenance window
  goodolclint.uptime_kuma.uptime_kuma_maintenance:
    api_url: http://localhost:3001
    api_username: admin
    api_password: secret123
    title: Weekly Backup
    strategy: recurring-weekday
    weekdays: [0, 6]
    time_range:
      - hours: 2
        minutes: 0
      - hours: 4
        minutes: 0
    duration_minutes: 120
    state: present

- name: Create a cron-based maintenance window
  goodolclint.uptime_kuma.uptime_kuma_maintenance:
    api_url: http://localhost:3001
    api_username: admin
    api_password: secret123
    title: Nightly Cleanup
    strategy: cron
    cron: "0 3 * * *"
    duration_minutes: 30
    state: present

- name: Delete a maintenance window
  goodolclint.uptime_kuma.uptime_kuma_maintenance:
    api_url: http://localhost:3001
    api_username: admin
    api_password: secret123
    title: Server Upgrade
    state: absent
"""

RETURN = r"""
maintenance:
  description: The maintenance window object after the operation.
  returned: success
  type: dict
  sample:
    id: 1
    title: Server Upgrade
    strategy: manual
    active: true
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


def _build_maintenance_kwargs(module):
    """Build kwargs for add_maintenance / edit_maintenance."""
    params = module.params
    kwargs = {
        "title": params["title"],
        "strategy": params["strategy"],
        "active": params["active"],
        "description": params["description"],
        "intervalDay": params["interval_day"],
    }
    if params["strategy"] == "cron":
        kwargs["cron"] = params["cron"]
        kwargs["durationMinutes"] = params["duration_minutes"]

    if params.get("date_range") is not None:
        kwargs["dateRange"] = params["date_range"]
    if params.get("weekdays") is not None:
        kwargs["weekdays"] = params["weekdays"]
    if params.get("days_of_month") is not None:
        kwargs["daysOfMonth"] = params["days_of_month"]
    if params.get("time_range") is not None:
        kwargs["timeRange"] = params["time_range"]
    if params.get("timezone") is not None:
        kwargs["timezoneOption"] = params["timezone"]

    return kwargs


def run_module(module):
    """Execute the maintenance module logic."""
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
    title = module.params["title"]

    existing = client.get_maintenance_by_title(title)

    if state == "absent":
        if existing is None:
            module.exit_json(changed=False, maintenance={})
            return
        if module.check_mode:
            module.exit_json(
                changed=True,
                diff=compute_diff(existing, None),
                maintenance=normalize_result(existing),
            )
            return
        client.delete_maintenance(existing["id"])
        module.exit_json(changed=True, diff=compute_diff(existing, None), maintenance={})
        return

    # state == present
    kwargs = _build_maintenance_kwargs(module)

    if existing is None:
        if module.check_mode:
            module.exit_json(changed=True, diff=compute_diff(None, kwargs), maintenance=kwargs)
            return
        result = client.add_maintenance(**kwargs)
        maint_id = result.get("maintenanceID")
        new_maint = client.get_maintenance(maint_id) if maint_id else result
        module.exit_json(
            changed=True,
            diff=compute_diff(None, new_maint),
            maintenance=normalize_result(new_maint),
        )
        return

    # Update if needed
    exclude = {"id", "timezoneOption"}
    if not needs_update(existing, kwargs, exclude_keys=exclude):
        module.exit_json(changed=False, maintenance=normalize_result(existing))
        return

    if module.check_mode:
        after = dict(existing)
        after.update(kwargs)
        module.exit_json(
            changed=True,
            diff=compute_diff(existing, after),
            maintenance=normalize_result(after),
        )
        return

    client.edit_maintenance(existing["id"], **kwargs)
    updated = client.get_maintenance(existing["id"])
    module.exit_json(
        changed=True,
        diff=compute_diff(existing, updated),
        maintenance=normalize_result(updated),
    )


def main():
    """Module entry point."""
    spec = uptime_kuma_argument_spec()
    spec.update(
        title=dict(type="str", required=True),
        strategy=dict(
            type="str",
            choices=["manual", "single", "recurring-interval", "recurring-weekday",
                     "recurring-day-of-month", "cron"],
        ),
        active=dict(type="bool", default=True),
        description=dict(type="str", default=""),
        date_range=dict(type="list", elements="str"),
        interval_day=dict(type="int", default=1),
        weekdays=dict(type="list", elements="int"),
        days_of_month=dict(type="list", elements="int"),
        time_range=dict(type="list", elements="dict"),
        cron=dict(type="str", default="30 3 * * *"),
        duration_minutes=dict(type="int", default=60),
        timezone=dict(type="str"),
        state=dict(type="str", choices=["present", "absent"], default="present"),
    )

    module = AnsibleModule(
        argument_spec=spec,
        supports_check_mode=True,
        required_if=[
            ("state", "present", ("strategy",)),
        ],
    )

    run_module(module)


if __name__ == "__main__":
    main()
