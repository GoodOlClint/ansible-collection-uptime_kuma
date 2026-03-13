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
      - Whether the status page is publicly visible.
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
    type: str
  api_password:
    description:
      - Password for authentication.
    type: str
    no_log: true
  api_token:
    description:
      - Login token for authentication.
    type: str
    no_log: true
  validate_certs:
    description:
      - Whether to validate SSL certificates.
    type: bool
    default: true
  api_timeout:
    description:
      - Timeout in seconds for API requests.
    type: int
    default: 10
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
    published: true
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
    published: true
    theme: auto
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.goodolclint.uptime_kuma.plugins.module_utils.uptime_kuma_api import (
    UptimeKumaClient,
    compute_diff,
    needs_update,
    normalize_result,
    uptime_kuma_argument_spec,
)


def _get_existing_by_slug(client, slug):
    """Find a status page by slug, return None if not found."""
    for page in client.get_status_pages():
        if page.get("slug") == slug:
            return page
    return None


def run_module(module):
    """Execute the status_page module logic."""
    client = UptimeKumaClient(module)
    try:
        _run(module, client)
    finally:
        client.disconnect()


def _run(module, client):
    """Inner logic separated for clean disconnect handling."""
    state = module.params["state"]
    slug = module.params["slug"]

    existing = _get_existing_by_slug(client, slug)

    if state == "absent":
        if existing is None:
            module.exit_json(changed=False, status_page={})
            return
        if module.check_mode:
            module.exit_json(
                changed=True,
                diff=compute_diff(existing, None),
                status_page=normalize_result(existing),
            )
            return
        client.delete_status_page(slug)
        module.exit_json(changed=True, diff=compute_diff(existing, None), status_page={})
        return

    # state == present
    title = module.params["title"]
    if title is None:
        module.fail_json(msg="Parameter 'title' is required when state=present")

    save_kwargs = _build_save_kwargs(module)

    if existing is None:
        if module.check_mode:
            module.exit_json(changed=True, diff=compute_diff(None, save_kwargs), status_page=save_kwargs)
            return
        client.add_status_page(slug, title)
        # After creation, get the page to find its ID, then save full config
        created = _get_existing_by_slug(client, slug)
        if created and save_kwargs:
            save_kwargs["id"] = created["id"]
            save_kwargs["title"] = title
            client.save_status_page(slug, **save_kwargs)
        result = _get_existing_by_slug(client, slug) or created
        module.exit_json(
            changed=True,
            diff=compute_diff(None, result),
            status_page=normalize_result(result),
        )
        return

    # Update if needed - check basic fields
    desired_check = {"title": title}
    for key in ("theme", "published", "showTags", "showPoweredBy", "customCSS"):
        if key in save_kwargs:
            desired_check[key] = save_kwargs[key]

    exclude = {"id", "slug", "incident", "maintenanceList", "publicGroupList", "icon"}
    if not needs_update(existing, desired_check, exclude_keys=exclude):
        module.exit_json(changed=False, status_page=normalize_result(existing))
        return

    if module.check_mode:
        after = dict(existing)
        after.update(desired_check)
        module.exit_json(
            changed=True,
            diff=compute_diff(existing, after),
            status_page=normalize_result(after),
        )
        return

    save_kwargs["id"] = existing["id"]
    save_kwargs["title"] = title
    client.save_status_page(slug, **save_kwargs)
    updated = _get_existing_by_slug(client, slug)
    module.exit_json(
        changed=True,
        diff=compute_diff(existing, updated),
        status_page=normalize_result(updated),
    )


def _build_save_kwargs(module):
    """Build kwargs for save_status_page from module params."""
    params = module.params
    kwargs = {}

    mappings = {
        "description": "description",
        "theme": "theme",
        "published": "published",
        "show_tags": "showTags",
        "show_powered_by": "showPoweredBy",
        "show_certificate_expiry": "showCertificateExpiry",
        "custom_css": "customCSS",
        "footer_text": "footerText",
        "google_analytics_id": "googleAnalyticsId",
    }

    for param_name, api_name in mappings.items():
        value = params.get(param_name)
        if value is not None:
            kwargs[api_name] = value

    if params.get("domain_name_list") is not None:
        kwargs["domainNameList"] = params["domain_name_list"]
    if params.get("public_group_list") is not None:
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
        published=dict(type="bool", default=True),
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
        required_if=[
            ("state", "present", ("title",)),
        ],
    )

    run_module(module)


if __name__ == "__main__":
    main()
