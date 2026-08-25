#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Clint Branham <goodolclint@gmail.com>
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: uptime_kuma_status_page
short_description: Manage status pages in Uptime Kuma
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
  - Create, update, and delete public status pages in Uptime Kuma.
  - Status pages are identified by O(slug) (URL-safe identifier).
options:
  slug:
    description:
      - URL-safe identifier for the status page.
      - Used as the unique identifier — cannot be changed after creation.
    type: str
    required: true
  title:
    description:
      - Title of the status page.
      - Required when O(state=present).
    type: str
  description:
    description:
      - Description text for the status page.
    type: str
  theme:
    description:
      - Visual theme for the status page.
    type: str
    choices: [auto, light, dark]
    default: auto
  published:
    description:
      - Deprecated, has no effect and will be removed in version 1.0.0 of the collection. Uptime Kuma 2.x does not
        change this after creation, so it is neither sent nor compared; kept so existing playbooks keep validating.
    type: bool
    default: true
  show_tags:
    description:
      - Whether to show tags on the status page.
    type: bool
    default: false
  show_powered_by:
    description:
      - Whether to show the Powered By footer.
    type: bool
    default: true
  show_certificate_expiry:
    description:
      - Whether to show certificate expiry information.
    type: bool
    default: false
  custom_css:
    description:
      - Custom CSS for the status page.
    type: str
    default: ""
  footer_text:
    description:
      - Custom footer text.
    type: str
  google_analytics_id:
    description:
      - Stored as Uptime Kuma 2.x C(analyticsId) with C(analyticsType=google).
      - Google Analytics tracking ID.
    type: str
  domain_name_list:
    description:
      - List of custom domain names for the status page.
    type: list
    elements: str
  public_group_list:
    description:
      - List of monitor group definitions for the status page.
      - Each group is a dict with C(name), C(weight), and C(monitorList) keys.
    type: list
    elements: dict
  state:
    description:
      - Whether the status page should exist or not.
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
- name: Create a status page
  goodolclint.uptime_kuma.uptime_kuma_status_page:
    api_url: http://localhost:3001
    api_username: admin
    api_password: secret123
    slug: my-services
    title: My Services Status
    description: Current status of all services
    state: present

- name: Create a status page with monitor groups
  goodolclint.uptime_kuma.uptime_kuma_status_page:
    api_url: http://localhost:3001
    api_username: admin
    api_password: secret123
    slug: my-services
    title: My Services Status
    public_group_list:
      - name: Web Services
        weight: 1
        monitorList:
          - id: 1
          - id: 2
    state: present

- name: Delete a status page
  goodolclint.uptime_kuma.uptime_kuma_status_page:
    api_url: http://localhost:3001
    api_username: admin
    api_password: secret123
    slug: my-services
    state: absent
"""

RETURN = r"""
status_page:
  description: The status page object after the operation.
  returned: success
  type: dict
  sample:
    slug: my-services
    title: My Services Status
    theme: auto
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.goodolclint.uptime_kuma.plugins.module_utils.uptime_kuma_api import (
    UptimeKumaClient,
    UptimeKumaError,
    UptimeKumaServerError,
    compute_diff,
    needs_update,
    normalize_result,
    uptime_kuma_argument_spec,
)


def _get_existing_by_slug(client, slug, with_groups=False):
    """Return the page config for *slug* (plus public groups if *with_groups*), or None if no such page."""
    if not with_groups:
        return client.get_status_page_config(slug)
    try:
        return client.get_status_page(slug)
    except UptimeKumaServerError:
        return None


def _groups(groups):
    """Public groups reduced to what the module manages: names and monitor ids, both in display order."""
    return [(g.get("name"), [m.get("id") for m in g.get("monitorList") or []]) for g in groups or []]


_DIFF_EXCLUDE = {"incident", "maintenanceList"}


def run_module(module):
    """Execute the status_page module logic."""
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
    slug = module.params["slug"]

    existing = _get_existing_by_slug(client, slug, with_groups=module.params.get("public_group_list") is not None)

    if state == "absent":
        if existing is None:
            module.exit_json(changed=False, status_page={})
            return
        if module.check_mode:
            module.exit_json(
                changed=True,
                diff=compute_diff(existing, None, exclude_keys=_DIFF_EXCLUDE),
                status_page=normalize_result(existing),
            )
            return
        client.delete_status_page(slug)
        module.exit_json(changed=True, diff=compute_diff(existing, None, exclude_keys=_DIFF_EXCLUDE), status_page={})
        return

    # state == present
    title = module.params["title"]
    if title is None:
        module.fail_json(msg="Parameter 'title' is required when state=present")
        return

    save_kwargs = _build_save_kwargs(module)
    desired_groups = save_kwargs.get("publicGroupList")

    if existing is None:
        if module.check_mode:
            predicted = {"slug": slug, "title": title, **save_kwargs}
            module.exit_json(changed=True, diff=compute_diff(None, predicted), status_page=normalize_result(predicted))
            return
        client.add_status_page(slug, title)
        # After creation, get the page to find its ID, then save full config
        created = _get_existing_by_slug(client, slug)
        if created and save_kwargs:
            save_kwargs["id"] = created["id"]
            save_kwargs["title"] = title
            client.save_status_page(slug, **save_kwargs)
        result = _get_existing_by_slug(client, slug, with_groups=desired_groups is not None) or created
        module.exit_json(
            changed=True,
            diff=compute_diff(None, result, exclude_keys=_DIFF_EXCLUDE),
            status_page=normalize_result(result),
        )
        return

    desired_check = {"title": title, **save_kwargs}
    desired_check.pop("publicGroupList", None)
    groups_changed = desired_groups is not None and _groups(existing.get("publicGroupList")) != _groups(desired_groups)
    if not needs_update(existing, desired_check) and not groups_changed:
        module.exit_json(changed=False, status_page=normalize_result(existing))
        return

    if module.check_mode:
        after = dict(existing)
        after.update(desired_check)
        if desired_groups is not None:
            after["publicGroupList"] = desired_groups
        module.exit_json(
            changed=True,
            diff=compute_diff(existing, after, exclude_keys=_DIFF_EXCLUDE),
            status_page=normalize_result(after),
        )
        return

    save_kwargs["id"] = existing["id"]
    save_kwargs["title"] = title
    client.save_status_page(slug, **save_kwargs)
    updated = _get_existing_by_slug(client, slug, with_groups=desired_groups is not None)
    module.exit_json(
        changed=True,
        diff=compute_diff(existing, updated, exclude_keys=_DIFF_EXCLUDE),
        status_page=normalize_result(updated),
    )


def _build_save_kwargs(module):
    """Build kwargs for save_status_page from module params."""
    params = module.params
    kwargs = {}

    mappings = {
        "description": "description",
        "theme": "theme",
        "show_tags": "showTags",
        "show_powered_by": "showPoweredBy",
        "show_certificate_expiry": "showCertificateExpiry",
        "custom_css": "customCSS",
        "footer_text": "footerText",
        "google_analytics_id": "analyticsId",
    }

    for param_name, api_name in mappings.items():
        value = params.get(param_name)
        if value is not None:
            kwargs[api_name] = value

    if params.get("google_analytics_id") is not None:
        kwargs["analyticsType"] = "google"
    if params.get("domain_name_list") is not None:
        kwargs["domainNameList"] = params["domain_name_list"]
    if params.get("public_group_list") is not None:
        for group in params["public_group_list"]:
            if not all(isinstance(m, dict) and "id" in m for m in group.get("monitorList") or []):
                module.fail_json(msg="public_group_list monitorList entries must be dicts with an 'id' key")
        kwargs["publicGroupList"] = params["public_group_list"]

    return kwargs


def main():
    """Module entry point."""
    spec = uptime_kuma_argument_spec()
    spec.update(
        slug=dict(type="str", required=True),
        title=dict(type="str"),
        description=dict(type="str"),
        theme=dict(type="str", choices=["auto", "light", "dark"], default="auto"),
        published=dict(type="bool", default=True, removed_in_version="1.0.0",
                       removed_from_collection="goodolclint.uptime_kuma"),
        show_tags=dict(type="bool", default=False),
        show_powered_by=dict(type="bool", default=True),
        show_certificate_expiry=dict(type="bool", default=False),
        custom_css=dict(type="str", default=""),
        footer_text=dict(type="str"),
        google_analytics_id=dict(type="str"),
        domain_name_list=dict(type="list", elements="str"),
        public_group_list=dict(type="list", elements="dict"),
        state=dict(type="str", choices=["present", "absent"], default="present"),
    )

    module = AnsibleModule(
        argument_spec=spec,
        supports_check_mode=True,
        required_one_of=[("api_password", "api_token")],
        mutually_exclusive=[("api_token", "api_password")],
        required_if=[
            ("state", "present", ("title",)),
        ],
    )

    run_module(module)


if __name__ == "__main__":
    main()
